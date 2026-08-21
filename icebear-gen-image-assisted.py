#!/usr/bin/env python3

from __future__ import annotations

import argparse
import base64
import html
import io
import json
import os
import random
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from dotenv import load_dotenv
from openai import BadRequestError, OpenAI
from PIL import Image


DEFAULT_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "chatgpt-image-latest")
#DEFAULT_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
DEFAULT_TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-5.4")
DEFAULT_OUTPUT_SIZE = os.getenv("OPENAI_IMAGE_SIZE", "1024x1024")
DEFAULT_OUTPUT_QUALITY = os.getenv("OPENAI_IMAGE_QUALITY", "high")
DEFAULT_OUTPUT_FORMAT = os.getenv("OPENAI_IMAGE_FORMAT", "jpeg")
DEFAULT_OUTPUT_COMPRESSION = int(os.getenv("OPENAI_IMAGE_COMPRESSION", "90"))
DEFAULT_INPUT_FIDELITY = os.getenv("OPENAI_INPUT_FIDELITY", "high")
DEFAULT_MAX_ATTEMPTS = int(os.getenv("OPENAI_IMAGE_MAX_ATTEMPTS", "4"))

MEDIA_ROOT = Path("./media")
MEDIA_DIR = MEDIA_ROOT / f"pid-{os.getpid()}"
SEARCH_IMAGES_DIR = MEDIA_DIR / "search_images"
ARTWORKS_JSON = Path("./artworks.json")
DIRECT_INPUT_DIR = MEDIA_DIR / "direct_inputs"
MAX_REFERENCE_DOWNLOADS = 3
MAX_ARTWORK_TRIES = 10
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8,text/html;q=0.4",
}
_USELESS_CITATION = re.compile(
    r"^(:contentReference|not specified|unspecified|n/?a)\b",
    re.IGNORECASE,
)
_OG_IMAGE_PATTERNS = [
    re.compile(
        r'<meta[^>]+property=["\']og:image:secure_url["\'][^>]+content=["\']([^"\']+)',
        re.IGNORECASE,
    ),
    re.compile(
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image:secure_url["\']',
        re.IGNORECASE,
    ),
    re.compile(
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
        re.IGNORECASE,
    ),
    re.compile(
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        re.IGNORECASE,
    ),
    re.compile(
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)',
        re.IGNORECASE,
    ),
    re.compile(
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
        re.IGNORECASE,
    ),
]


@dataclass
class Artwork:
    title: str
    artist: str
    year: str | None = None
    citation: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Artwork":
        year = data.get("year")
        citation = data.get("citation")
        return cls(
            title=str(data["title"]).strip(),
            artist=str(data["artist"]).strip(),
            year=_clean_citation(year),
            citation=_clean_citation(citation),
        )

    def output_stem(self, today: datetime) -> str:
        safe_title = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in self.title)
        return f"{safe_title}-{today.strftime('%Y-%m-%d')}"

    def search_description(self) -> str:
        lines = [
            f"Title: {self.title}",
            f"Artist: {self.artist}",
        ]
        if self.year:
            lines.append(f"Year: {self.year}")
        if self.citation:
            lines.append(f"Citation / known source: {self.citation}")
        return "\n".join(lines)


class LowConfidenceImageMatch(Exception):
    def __init__(self, artwork: Artwork, reason: str) -> None:
        self.artwork = artwork
        self.reason = reason
        super().__init__(
            f"Low-confidence image match for {artwork.title} by {artwork.artist}: {reason}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate IceBear artwork images")
    parser.add_argument("--env", type=str, help="Path to .env file")
    parser.add_argument(
        "--sourcedir",
        type=str,
        help="Directory containing source image(s) to edit",
    )
    parser.add_argument(
        "--image-source",
        type=str,
        help="Direct image source: either a local file path or an image URL. "
             "If omitted, ChatGPT web search picks the best matching reference image.",
    )
    parser.add_argument(
        "--artwork",
        type=str,
        help='JSON blob, e.g. \'{"title": "Starry Night", "artist": "Vincent van Gogh"}\'',
    )
    parser.add_argument(
        "--image-model",
        type=str,
        default=DEFAULT_IMAGE_MODEL,
        help=f"OpenAI image model (default: {DEFAULT_IMAGE_MODEL})",
    )
    parser.add_argument(
        "--text-model",
        type=str,
        default=DEFAULT_TEXT_MODEL,
        help=f"OpenAI text model (default: {DEFAULT_TEXT_MODEL})",
    )
    parser.add_argument(
        "--attempts",
        type=int,
        default=DEFAULT_MAX_ATTEMPTS,
        help=f"Max image edit attempts (default: {DEFAULT_MAX_ATTEMPTS})",
    )
    return parser.parse_args()


def load_environment(env_path: str | None) -> None:
    load_dotenv(dotenv_path=env_path, override=True)


def ensure_dirs() -> None:
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    SEARCH_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    DIRECT_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Using process-local media dir: {MEDIA_DIR.resolve()}")


def load_artworks() -> list[Artwork]:
    if not ARTWORKS_JSON.exists():
        raise FileNotFoundError(f"Missing artworks file: {ARTWORKS_JSON}")
    with ARTWORKS_JSON.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return [Artwork.from_dict(item) for item in raw]


def pick_artwork(
    args: argparse.Namespace,
    artworks: list[Artwork],
    exclude: set[tuple[str, str]] | None = None,
) -> Artwork:
    if args.artwork:
        try:
            payload = json.loads(args.artwork)
            artwork = Artwork.from_dict(payload)
            print(f"Using provided artwork: {artwork}")
            return artwork
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid --artwork JSON: {e}") from e

    skipped = exclude or set()
    candidates = [item for item in artworks if (item.title, item.artist) not in skipped]
    if not candidates:
        raise RuntimeError("No remaining artworks to try")
    artwork = random.choice(candidates)
    print(f"Randomly selected artwork: {artwork}")
    return artwork


def resolve_openai_base_url() -> str:
    """Return a usable OpenAI base URL.

    The OpenAI SDK reads OPENAI_BASE_URL when set. An empty value or a host
    without an http(s) scheme produces:
      httpx.UnsupportedProtocol: Request URL is missing an 'http://' or 'https://' protocol
    which the SDK wraps as APIConnectionError("Connection error.").
    """
    default = "https://api.openai.com/v1"
    raw = (os.getenv("OPENAI_BASE_URL") or "").strip()
    if not raw:
        return default

    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError(
            f"OPENAI_BASE_URL must be an absolute http(s) URL, got {raw!r}. "
            f"Example: {default}"
        )
    return raw.rstrip("/")


def create_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    base_url = resolve_openai_base_url()
    org_id = os.getenv("OPENAI_ORG_ID") or None
    print(f"OpenAI base_url: {base_url}")

    kwargs: dict[str, Any] = {"api_key": api_key, "base_url": base_url}
    if org_id:
        kwargs["organization"] = org_id
    return OpenAI(**kwargs)


def _clean_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clean_citation(value: Any) -> str | None:
    text = _clean_optional_text(value)
    if not text or _USELESS_CITATION.match(text):
        return None
    return text


def _sanitize_filename(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return sanitized or "artwork"


def is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _looks_like_image(content: bytes, content_type: str) -> bool:
    if content_type.startswith("image/"):
        return True
    return content.startswith((b"\x89PNG", b"\xff\xd8\xff", b"GIF87a", b"GIF89a", b"RIFF"))


def _extract_og_image(page_html: str, page_url: str) -> str | None:
    for pattern in _OG_IMAGE_PATTERNS:
        match = pattern.search(page_html)
        if not match:
            continue
        raw = html.unescape(match.group(1).strip())
        if raw.startswith("//"):
            raw = f"{urlparse(page_url).scheme}:{raw}"
        resolved = urljoin(page_url, raw)
        if is_url(resolved):
            return resolved
    return None


def _filename_for_url(image_url: str, artwork: Artwork, index: int) -> str:
    parsed = urlparse(image_url)
    suffix = Path(parsed.path).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        suffix = ".jpg"
    stem = _sanitize_filename(f"{artwork.artist}_{artwork.title}")
    return f"{index}_{stem}{suffix}"


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in model output: {text[:400]}")
    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("Model JSON was not an object")
    return parsed


def _collect_urls(*groups: Any) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for group in groups:
        if group is None:
            continue
        values = group if isinstance(group, list) else [group]
        for value in values:
            if not isinstance(value, str):
                continue
            candidate = value.strip().rstrip(").,]}'\"")
            if not is_url(candidate) or candidate in seen:
                continue
            seen.add(candidate)
            urls.append(candidate)
    return urls


def _image_urls_from_web_search(response: Any) -> list[str]:
    urls: list[str] = []
    for item in getattr(response, "output", None) or []:
        item_type = getattr(item, "type", None)
        dumped = item.model_dump() if hasattr(item, "model_dump") else None
        if item_type != "web_search_call" and not (
            isinstance(dumped, dict) and dumped.get("type") == "web_search_call"
        ):
            continue

        results = getattr(item, "results", None)
        if results is None and isinstance(dumped, dict):
            results = dumped.get("results")
        if not results:
            continue

        for result in results:
            if isinstance(result, dict):
                urls.extend(
                    _collect_urls(
                        result.get("image_url"),
                        result.get("url"),
                    )
                )
            else:
                urls.extend(
                    _collect_urls(
                        getattr(result, "image_url", None),
                        getattr(result, "url", None),
                    )
                )
    return urls


def _create_artwork_image_search(
    client: OpenAI,
    text_model: str,
    prompt: str,
) -> Any:
    attempts: list[dict[str, Any]] = [
        {
            "tools": [
                {
                    "type": "web_search",
                    "search_content_types": ["image", "text"],
                    "image_settings": {"max_results": 8, "caption": True},
                }
            ],
            "tool_choice": {"type": "web_search"},
            "include": ["web_search_call.results"],
        },
        {
            "tools": [{"type": "web_search"}],
            "tool_choice": {"type": "web_search"},
        },
        {
            "tools": [{"type": "web_search"}],
        },
    ]

    last_error: Exception | None = None
    for extra in attempts:
        try:
            return client.responses.create(
                model=text_model,
                input=prompt,
                **extra,
            )
        except BadRequestError as e:
            last_error = e
            print(f"Retrying ChatGPT image search with a simpler request: {e}")

    raise RuntimeError(f"ChatGPT image search failed: {last_error}")


def _is_high_confidence(payload: dict[str, Any]) -> bool:
    high_confidence = payload.get("high_confidence")
    if isinstance(high_confidence, bool):
        return high_confidence
    if isinstance(high_confidence, str):
        return high_confidence.strip().lower() in {"true", "yes", "high"}

    confidence = str(payload.get("confidence") or "").strip().lower()
    return confidence == "high"


def find_artwork_image_urls(
    client: OpenAI,
    text_model: str,
    artwork: Artwork,
) -> list[str]:
    prompt = f"""Search the web for the most appropriate high-quality reference image of this exact artwork:

{artwork.search_description()}

Requirements:
- Identify THIS specific work, not a similarly titled piece, tribute, parody, meme, merchandise photo, or a crop of a different painting.
- Prefer museum, Wikimedia Commons, official artist, or publisher pages. If the citation is a product listing URL, start there.
- Prefer a complete, well-lit view of the original work over details, frames on a wall, or screenshots.
- Prefer a direct image file URL (jpg/jpeg/png/webp) that can be downloaded.
- Set high_confidence to true only if you are highly confident the chosen URL is this exact artwork.
- If you cannot find this exact work with high confidence, set high_confidence to false and url to null.

Return JSON only, with no markdown:
{{
  "url": "https://..." or null,
  "alternate_urls": ["https://...", "https://..."],
  "high_confidence": true,
  "reason": "one sentence explaining why this is or is not a confident match"
}}
"""

    print(f"Asking ChatGPT to find a reference image for: {artwork.title} by {artwork.artist}")
    response = _create_artwork_image_search(client, text_model, prompt)
    search_urls = _image_urls_from_web_search(response)

    model_urls: list[str] = []
    reason = ""
    high_confidence = False
    text = (response.output_text or "").strip()
    if text:
        try:
            payload = _extract_json_object(text)
            reason = str(payload.get("reason") or "").strip()
            if reason:
                print(f"ChatGPT image choice: {reason}")
            high_confidence = _is_high_confidence(payload)
            model_urls = _collect_urls(payload.get("url"), payload.get("alternate_urls"))
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Could not parse ChatGPT image-URL JSON: {e}")
            reason = str(e)
            high_confidence = False

    if not high_confidence:
        raise LowConfidenceImageMatch(
            artwork,
            reason or "ChatGPT did not report high confidence for this artwork",
        )

    urls = _collect_urls(model_urls, search_urls)
    if not urls:
        raise LowConfidenceImageMatch(
            artwork,
            reason or "ChatGPT reported high confidence but returned no image URL",
        )

    print(f"ChatGPT selected {len(urls)} candidate image URL(s)")
    for index, url in enumerate(urls, start=1):
        print(f"  {index}. {url}")
    return urls


def download_image_from_url(image_url: str, destination: Path, depth: int = 0) -> Path:
    if depth > 2:
        raise ValueError(f"Could not resolve an image from: {image_url}")

    headers = dict(BROWSER_HEADERS)
    host = urlparse(image_url).netloc.lower()
    if "wikimedia.org" in host or "wikipedia.org" in host:
        headers["Referer"] = "https://commons.wikimedia.org/"

    response = requests.get(image_url, headers=headers, timeout=60, allow_redirects=True)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
    content = response.content
    looks_like_html = content_type.startswith("text/html") or (
        not _looks_like_image(content, content_type) and b"<html" in content[:4000].lower()
    )
    if looks_like_html:
        og_url = _extract_og_image(response.text, response.url or image_url)
        if not og_url:
            raise ValueError(f"URL is a web page, not an image: {image_url}")
        print(f"Resolved page to og:image: {og_url}")
        return download_image_from_url(og_url, destination, depth=depth + 1)

    if not _looks_like_image(content, content_type):
        raise ValueError(f"URL does not appear to be an image: content-type={content_type}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return destination


def download_direct_image(image_url: str) -> Path:
    parsed = urlparse(image_url)
    filename = Path(parsed.path).name or "downloaded_image"
    suffix = Path(filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        filename = f"{filename}.jpg"

    destination = DIRECT_INPUT_DIR / filename
    download_image_from_url(image_url, destination)
    print(f"Downloaded direct image URL to: {destination}")
    return destination


def get_source_images(
    artwork: Artwork,
    sourcedir: str | None,
    image_source: str | None,
    client: OpenAI,
    text_model: str,
) -> list[Path]:
    # Highest priority: explicit direct file path or URL
    if image_source:
        if is_url(image_source):
            return [download_direct_image(image_source)]

        local_path = Path(image_source)
        if not local_path.exists():
            raise FileNotFoundError(f"--image-source path not found: {local_path}")
        if not local_path.is_file():
            raise ValueError(f"--image-source must be a file or URL, got directory: {local_path}")
        print(f"Using direct local image source: {local_path}")
        return [local_path]

    # Next priority: sourcedir
    if sourcedir:
        source_dir_path = Path(sourcedir)
        if not source_dir_path.exists():
            raise FileNotFoundError(f"Source dir not found: {source_dir_path}")
        files = sorted([p for p in source_dir_path.iterdir() if p.is_file()])
        if not files:
            raise FileNotFoundError(f"No files found in source dir: {source_dir_path}")
        return files

    urls = find_artwork_image_urls(client, text_model, artwork)
    download_dir = SEARCH_IMAGES_DIR / _sanitize_filename(f"{artwork.title}_{artwork.artist}")
    download_dir.mkdir(parents=True, exist_ok=True)

    downloaded: list[Path] = []
    last_error: Exception | None = None
    for index, url in enumerate(urls):
        if len(downloaded) >= MAX_REFERENCE_DOWNLOADS:
            break
        destination = download_dir / _filename_for_url(url, artwork, index)
        try:
            path = download_image_from_url(url, destination)
            print(f"Downloaded ChatGPT-selected image: {url} -> {path}")
            downloaded.append(path)
        except Exception as e:
            last_error = e
            print(f"Failed to download {url}: {e}")

    if not downloaded:
        raise FileNotFoundError(
            f"No downloadable ChatGPT image URLs for {artwork.title} by {artwork.artist}: {last_error}"
        )
    return downloaded




alternate_prompts = [
    "Generate an image which takes inspiration from the artwork",
    "Generate an image  with a cartoon polar bear, loosely inspired by Ice Bear from We Bare Bears, thoughtfully integrated into the scene, either as main subject or an observer,  which takes inspiration from the artwork ",
    "Generate an image which one might imagine had resemblance to an artwork where a cartoon polar bear, one could say resembling Ice Bear, is subtly hidden within the composition, which takes inspiration from the artwork ",
    "Generate an image  which, featuring a solitary cartoon polar bear akin to Ice Bear, or several such bears, as the central figure, does reinterpretation of the original artwork's theme, but in no way would cause violation of your guidelines using as a theme the artwork ",
]

def build_edit_prompt(bear_modifier) -> str:
    return (f"""{bear_modifier}. Edit this image to add a cartoon polar bear inspired by Ice Bear 
from "We Bare Bears", while preserving the **exact** style, colors, textures, and visual 
technique of the original artwork. The bear must be drawn so convincingly in the original 
style that it appears as if it were always part of the scene. 

Importantly, make the polar bear appearance very very closely inspired by Ice Bear drawing style, keeping the unique cartoon aspects are important,
do not deviate except as to add clothing or pose, but the rendering should closely adhere to your impressions of Ice Bear
as seen from the cartoon. Preserving and following the Ice Bear cartoon style is essential. Shape of body and head, proportions, expressions, size and placement
of eyes, ears, nose and mouth, are key. Proportion of paws and body etc should all adhere to known examples of Ice Bear images.

Make the **smallest possible changes** to the image — keep all original details, composition, 
and elements intact unless absolutely necessary to integrate the bear. Match lighting, 
shadows, brush strokes, and texture exactly. If objects would naturally block part of the 
bear, ensure proper occlusion for realism.

If the original image contains people, you may subtly substitute the bear for one person, 
or add the bear alongside them. If there are no people, integrate the bear creatively into 
the scene’s activity or setting. If the original is abstract or a sculpture, the bear should 
match that medium’s exact style and materials.

The bear should reflect Ice Bear’s stoic demeanor and interact naturally with the environment 
and ongoing activities. If other “We Bare Bears” characters are included, ensure Ice Bear 
remains the focus.

If the artwork contains visible text, make at most one **subtle** bear-related word change 
(e.g., modifying a name or single word) without disrupting the text’s original tone or meaning.

If the artwork contains sillhouettes of people, make them into silhouettes of ice bears. 

Some people in the background can be replaced by bears also, if they are not too prominent, i.e., in a crowd or
far away. 

Above all: preserve the **unique identity** of the original artwork, making the bear feel like 
a natural and seamless part of the artist’s original vision, adapting to the drawing style, and
feel of what the artist is doing that is unique to them.

Make the bear be doing an activity that matches doing what a person would do in the context of the image.
for example, if it is construction, the bear would be doing construction. If its a boat, the bear might be 
piloting or rowing the boat. If it is a dinner, the bear could be cooking, serving, or eating dinner
at a table. If people are out walking in a park, so is the bear. The bear's clothing should match that
of the primary characters in the scene, or be appropriate for the task being performed.. If they are playing a sport, the bear would be 
doing that.  Pay attention to the scene and what activity person in the scene would naturally be performing
and make the bear do that. If there are people in the background, replace some of them with bears as well.

Remember, make the polar bear's appearance very very closely inspired by Ice Bear, the cartoon aspects are important,
do not deviate except as to add clothing or pose, but the rendering should closely adhere to your impressions of Ice Bear
as seen from the cartoon. Preserving and following the Ice Bear cartoon style is essential.

    """)



def decode_b64_image_to_pil(b64_json: str) -> Image.Image:
    image_bytes = base64.b64decode(b64_json)
    return Image.open(io.BytesIO(image_bytes))


def normalize_for_jpeg(image: Image.Image) -> Image.Image:
    if image.mode in ("RGBA", "LA", "P"):
        return image.convert("RGB")
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def save_image(image: Image.Image, output_path: Path, output_format: str) -> None:
    output_format = output_format.lower()
    if output_format == "jpeg":
        image = normalize_for_jpeg(image)
        image.save(output_path, "JPEG", quality=95)
    elif output_format == "png":
        image.save(output_path, "PNG")
    elif output_format == "webp":
        image.save(output_path, "WEBP", quality=95)
    else:
        raise ValueError(f"Unsupported output format: {output_format}")


def try_edit_image(
    client: OpenAI,
    image_model: str,
    source_images: list[Path],
    output_path: Path,
    attempts: int,
) -> Path:
    prompt = build_edit_prompt(random.choice(alternate_prompts))
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        source_path = source_images[(attempt - 1) % len(source_images)]
        print(f"Attempt {attempt}/{attempts} using source: {source_path}")

        try:
            with source_path.open("rb") as image_file:
                # result = client.images.edit(
                #     model=image_model,
                #     image=image_file,
                #     prompt=prompt,
                #     size=DEFAULT_OUTPUT_SIZE,
                # )

                result = client.images.edit(
                    model=image_model,
                    image=image_file,
                    prompt=prompt,
                    size=DEFAULT_OUTPUT_SIZE,
                    quality=DEFAULT_OUTPUT_QUALITY,
                    output_format=DEFAULT_OUTPUT_FORMAT,
                    output_compression=DEFAULT_OUTPUT_COMPRESSION,
                    input_fidelity=DEFAULT_INPUT_FIDELITY,
                )

            if not result.data or not result.data[0].b64_json:
                raise RuntimeError("No image data returned from OpenAI")

            pil_image = decode_b64_image_to_pil(result.data[0].b64_json)
            save_image(pil_image, output_path, DEFAULT_OUTPUT_FORMAT)
            print(f"Saved edited image to: {output_path}")
            return output_path

        except BadRequestError as e:
            last_error = e
            print(f"OpenAI rejected attempt {attempt}: {e}")
            continue
        except Exception as e:
            last_error = e
            print(f"Unexpected error on attempt {attempt}: {e}")
            continue

    raise RuntimeError(f"Failed to generate edited image after {attempts} attempts: {last_error}")


def generate_blurb(client: OpenAI, text_model: str, artwork: Artwork) -> str:
    prompt = (
        f"Write an extremely brief, factual museum-style blurb about the artwork titled "
        f"'{artwork.title}' by {artwork.artist}. "
        "Include only concise historical context and verifiable creation details such as date, place, "
        "patronage, or relevant historical background if known. "
        "Do not include praise, interpretation, or opinion. "
        "If details are uncertain or disputed, omit them."
    )

    response = client.responses.create(
        model=text_model,
        input=prompt,
    )

    text = (response.output_text or "").strip()
    if not text:
        raise RuntimeError("No text returned for artwork blurb")
    return text


def send_mailgun_email(
    artwork: Artwork,
    today: datetime,
    image_path: Path,
    original_reference_path: Path | None,
    blurb: str,
) -> None:
    mailgun_domain = os.getenv("MAILGUN_DOMAIN")
    mailgun_api_key = os.getenv("MAILGUN_API_KEY")
    from_email = os.getenv("MAILGUN_FROM_EMAIL")
    to_name = os.getenv("MAILGUN_TO_NAME")
    to_email = os.getenv("MAILGUN_TO_EMAIL")

    required = {
        "MAILGUN_DOMAIN": mailgun_domain,
        "MAILGUN_API_KEY": mailgun_api_key,
        "MAILGUN_FROM_EMAIL": from_email,
        "MAILGUN_TO_NAME": to_name,
        "MAILGUN_TO_EMAIL": to_email,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise RuntimeError(f"Missing Mailgun config: {', '.join(missing)}")

    data: dict[str, str] = {
        "from": f"Icebear Courier <{from_email}>",
        "to": f"{to_name} <{to_email}>",
        "subject": f"Icebear Artwork for today {today.strftime('%Y-%m-%d')}",
        "text": (
            f"Today's artwork is {artwork.title} by {artwork.artist}. Have a great bear day!\n\n"
            f"TODAY'S DESCRIPTION:\n{blurb}"
        ),
    }

    cc_emails = os.getenv("MAILGUN_CC_EMAILS")
    if cc_emails:
        email_list = [email.strip() for email in cc_emails.split(",") if email.strip()]
        if email_list:
            data["bcc"] = ", ".join(f"<{email}>" for email in email_list)

    files = [("inline", (image_path.name, image_path.open("rb")))]

    if original_reference_path and original_reference_path.exists():
        files.append(("inline", (original_reference_path.name, original_reference_path.open("rb"))))

    try:
        response = requests.post(
            mailgun_domain,
            auth=("api", mailgun_api_key),
            files=files,
            data=data,
            timeout=60,
        )
        print(f"Mailgun response: {response.status_code} {response.text}")
        response.raise_for_status()
        print(f"Email sent to {to_email} with image {image_path.name}")
    finally:
        for _, (_, fh) in files:
            fh.close()


def main() -> int:
    args = parse_args()
    load_environment(args.env)
    ensure_dirs()

    today = datetime.today()

    artworks = load_artworks()
    client = create_openai_client()

    artwork: Artwork | None = None
    source_images: list[Path] | None = None
    last_error: Exception | None = None
    tried: set[tuple[str, str]] = set()
    max_tries = 1 if args.artwork or args.image_source or args.sourcedir else MAX_ARTWORK_TRIES

    for attempt in range(1, max_tries + 1):
        try:
            artwork = pick_artwork(args, artworks, exclude=tried)
        except RuntimeError as e:
            last_error = e
            print(f"No more unused artworks to try: {e}")
            break
        tried.add((artwork.title, artwork.artist))
        if max_tries > 1:
            print(
                f"Artwork search attempt {attempt}/{max_tries}: "
                f"{artwork.title} by {artwork.artist}"
            )
        try:
            source_images = get_source_images(
                artwork=artwork,
                sourcedir=args.sourcedir,
                image_source=args.image_source,
                client=client,
                text_model=args.text_model,
            )
            break
        except LowConfidenceImageMatch as e:
            last_error = e
            print(f"Skipping artwork (low confidence): {e}")

    if artwork is None or source_images is None:
        raise RuntimeError(
            f"Gave up after {len(tried)} artwork "
            f"{'try' if len(tried) == 1 else 'tries'}: {last_error}"
        )
    source_image = source_images[0]

    extension = {
        "jpeg": ".jpg",
        "png": ".png",
        "webp": ".webp",
    }.get(DEFAULT_OUTPUT_FORMAT.lower(), ".jpg")

    if args.image_source:
        output_path = MEDIA_DIR / f"icebear-{source_image.stem}{extension}"
    else:
        output_path = MEDIA_DIR / f"{artwork.output_stem(today)}{extension}"

    edited_image_path = try_edit_image(
        client=client,
        image_model=args.image_model,
        source_images=source_images,
        output_path=output_path,
        attempts=args.attempts,
    )

    blurb = generate_blurb(
        client=client,
        text_model=args.text_model,
        artwork=artwork,
    )

    send_mailgun_email(
        artwork=artwork,
        today=today,
        image_path=edited_image_path,
        original_reference_path=source_image,
        blurb=blurb,
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        raise SystemExit(1)
