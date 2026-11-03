#!/usr/bin/env python3
"""Turn a single image into a stereo pair using estimated depth.

Depth comes from Depth Anything V2 (relative inverse depth, i.e. bigger = nearer),
which is mapped to a per-pixel horizontal disparity. Each eye's view is made by
shifting pixels by half that disparity, nearer pixels winning where two land on
the same spot, and filling the uncovered gaps from the background side.

Needs: pip install torch transformers numpy pillow
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image


DEFAULT_DEPTH_MODEL = "depth-anything/Depth-Anything-V2-Small-hf"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Make a stereo pair from one image")
    parser.add_argument("image", type=str, help="Input image path")
    parser.add_argument(
        "--out-dir",
        type=str,
        help="Output directory (default: next to the input image)",
    )
    parser.add_argument(
        "--max-disparity",
        type=float,
        default=0.03,
        help="Disparity between nearest and farthest points, as a fraction of "
             "image width (default: 0.03)",
    )
    parser.add_argument(
        "--convergence",
        type=float,
        default=0.5,
        help="Depth (0 = farthest, 1 = nearest) that sits on the screen plane: "
             "nearer things pop out, farther things recede (default: 0.5)",
    )
    parser.add_argument(
        "--depth-model",
        type=str,
        default=DEFAULT_DEPTH_MODEL,
        help=f"Hugging Face depth-estimation model (default: {DEFAULT_DEPTH_MODEL})",
    )
    return parser.parse_args()


def _gaussian_blur(values: np.ndarray, sigma: float) -> np.ndarray:
    """Separable Gaussian blur for float arrays, which PIL's filters do not accept."""
    radius = int(3 * sigma)
    offsets = np.arange(-radius, radius + 1)
    kernel = np.exp(-(offsets ** 2) / (2 * sigma ** 2))
    kernel /= kernel.sum()
    padded = np.pad(values, radius, mode="edge")
    rows = np.apply_along_axis(np.convolve, 1, padded, kernel, mode="valid")
    return np.apply_along_axis(np.convolve, 0, rows, kernel, mode="valid").astype(np.float32)


def estimate_depth(image: Image.Image, model_name: str) -> np.ndarray:
    """Return relative inverse depth normalized to 0 (far) .. 1 (near), at image size."""
    import torch
    from transformers import pipeline

    device = "mps" if torch.backends.mps.is_available() else (0 if torch.cuda.is_available() else -1)
    estimator = pipeline("depth-estimation", model=model_name, device=device)
    raw = estimator(image)["predicted_depth"].squeeze().float().cpu().numpy()

    depth = np.asarray(Image.fromarray(raw).resize(image.size, Image.BICUBIC), dtype=np.float32)
    # A light blur keeps tiny depth noise from tearing textures apart.
    depth = _gaussian_blur(depth, sigma=1.5)

    low, high = np.percentile(depth, [2, 98])
    return np.clip((depth - low) / max(high - low, 1e-6), 0.0, 1.0)


def _fill_holes(view: np.ndarray, view_depth: np.ndarray, filled: np.ndarray) -> np.ndarray:
    """Fill each uncovered pixel from its nearest covered neighbor on the farther side."""
    height, width = filled.shape
    columns = np.arange(width)

    left_index = np.where(filled, columns, -1)
    left_index = np.maximum.accumulate(left_index, axis=1)
    right_index = np.where(filled, columns, width)
    right_index = np.minimum.accumulate(right_index[:, ::-1], axis=1)[:, ::-1]

    rows = np.arange(height)[:, None]
    has_left = left_index >= 0
    has_right = right_index < width
    left_depth = np.where(has_left, view_depth[rows, np.clip(left_index, 0, width - 1)], np.inf)
    right_depth = np.where(has_right, view_depth[rows, np.clip(right_index, 0, width - 1)], np.inf)

    # Gaps open up behind foreground edges, so take whichever neighbor is farther away.
    use_left = has_left & (~has_right | (left_depth <= right_depth))
    source = np.where(use_left, left_index, right_index).clip(0, width - 1)

    result = view.copy()
    holes = ~filled
    result[holes] = view[rows, source][holes]
    return result


def render_view(pixels: np.ndarray, depth: np.ndarray, shift: np.ndarray) -> np.ndarray:
    """Forward-warp pixels horizontally by `shift`, nearest pixel winning, holes filled."""
    height, width = depth.shape
    rows, columns = np.indices((height, width))
    target = np.rint(columns + shift).astype(np.int64)
    inside = (target >= 0) & (target < width)

    flat_target = (rows * width + target)[inside]
    source_depth = depth[inside]

    # z-buffer: keep the nearest (largest) depth landing on each output pixel.
    zbuffer = np.full(height * width, -np.inf, dtype=np.float32)
    np.maximum.at(zbuffer, flat_target, source_depth)
    winners = source_depth >= zbuffer[flat_target]

    view = np.zeros_like(pixels)
    view_depth = np.full((height, width), np.inf, dtype=np.float32)
    filled = np.zeros((height, width), dtype=bool)
    winner_target = flat_target[winners]
    view.reshape(-1, pixels.shape[2])[winner_target] = pixels[inside][winners]
    view_depth.reshape(-1)[winner_target] = source_depth[winners]
    filled.reshape(-1)[winner_target] = True

    return _fill_holes(view, view_depth, filled)


def make_stereo_pair(
    image: Image.Image,
    depth: np.ndarray,
    max_disparity: float,
    convergence: float,
) -> tuple[Image.Image, Image.Image]:
    pixels = np.asarray(image.convert("RGB"))
    disparity = max_disparity * image.width * (depth - convergence)
    # Near points move right in the left eye and left in the right eye.
    left = render_view(pixels, depth, disparity / 2)
    right = render_view(pixels, depth, -disparity / 2)
    return Image.fromarray(left), Image.fromarray(right)


def side_by_side(first: Image.Image, second: Image.Image) -> Image.Image:
    combined = Image.new("RGB", (first.width * 2, first.height))
    combined.paste(first, (0, 0))
    combined.paste(second, (first.width, 0))
    return combined


def anaglyph(left: Image.Image, right: Image.Image) -> Image.Image:
    """Red-cyan anaglyph: red from the left eye, green and blue from the right."""
    red, _, _ = left.split()
    _, green, blue = right.split()
    return Image.merge("RGB", (red, green, blue))


def main() -> int:
    args = parse_args()
    image_path = Path(args.image)
    out_dir = Path(args.out_dir) if args.out_dir else image_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = image_path.stem

    with Image.open(image_path) as source:
        image = source.convert("RGB")

    print(f"Estimating depth with {args.depth_model}...")
    depth = estimate_depth(image, args.depth_model)
    left, right = make_stereo_pair(image, depth, args.max_disparity, args.convergence)

    outputs = {
        "depth": Image.fromarray((depth * 255).astype(np.uint8)),
        "left": left,
        "right": right,
        "parallel": side_by_side(left, right),
        "crosseye": side_by_side(right, left),
        "anaglyph": anaglyph(left, right),
    }
    for name, output in outputs.items():
        path = out_dir / f"{stem}-{name}.{'png' if name == 'depth' else 'jpg'}"
        output.save(path, quality=95)
        print(f"Saved {name}: {path}")

    wiggle_path = out_dir / f"{stem}-wiggle.gif"
    left.save(wiggle_path, save_all=True, append_images=[right], duration=140, loop=0)
    print(f"Saved wiggle: {wiggle_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
