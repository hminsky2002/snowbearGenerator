import os
import math
import subprocess
from pathlib import Path
from PIL import Image

def composite_scaled_images(input_dir, output_path="composite.png", canvas_size=2048):
    input_dir = Path(input_dir)
    png_files = sorted([p for p in input_dir.glob("*.png")])

    if not png_files:
        print("No PNG files found in the directory.")
        return

    num_images = len(png_files)
    grid_size = math.ceil(math.sqrt(num_images))
    cell_size = canvas_size // grid_size

    print(f"Preparing to tile {num_images} images into {grid_size}x{grid_size} grid.")
    print(f"Each cell size: {cell_size}x{cell_size} (max per image)")

    # Temp dir for resized images
    resized_dir = input_dir / "resized_temp"
    resized_dir.mkdir(exist_ok=True)

    resized_files = []

    for i, file in enumerate(png_files):
        resized_path = resized_dir / f"img_{i:03}.png"

        # Open image to get its original size
        with Image.open(file) as im:
            im.thumbnail((cell_size, cell_size), Image.Resampling.LANCZOS)
            # Create square canvas with transparency
            new_im = Image.new("RGBA", (cell_size, cell_size), (0, 0, 0, 0))
            offset = (
                (cell_size - im.width) // 2,
                (cell_size - im.height) // 2
            )
            new_im.paste(im, offset)
            new_im.save(resized_path)
            resized_files.append(resized_path)

    # Call montage
    subprocess.run([
        "montage", *map(str, resized_files),
        "-tile", f"{grid_size}x{grid_size}",
        "-geometry", f"{cell_size}x{cell_size}+0+0",
        "-background", "none",
        str(output_path)
    ], check=True)

    print(f"Composite saved to: {output_path}")

    # Clean up
    for f in resized_files:
        f.unlink()
    resized_dir.rmdir()

if __name__ == "__main__":
    composite_scaled_images("media")  # <- replace this path
