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
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from dotenv import load_dotenv
from openai import BadRequestError, OpenAI
from PIL import Image, ImageChops, ImageFilter

from google_custom_search_image_downloader import (
    google_search_api_call,
    google_search_response_parser,
)


# Which service draws the bear: "openai" (default) or "gemini". Gemini 3.1 Flash
# Image costs about a third of OpenAI's high-quality edit. Text calls (search,
# verification, blurb, GIF motion) always use OpenAI.
IMAGE_PROVIDER = os.getenv("ICEBEAR_IMAGE_PROVIDER", "openai").strip().lower()
if IMAGE_PROVIDER not in {"openai", "gemini"}:
    raise SystemExit(f"ICEBEAR_IMAGE_PROVIDER must be 'openai' or 'gemini', got {IMAGE_PROVIDER!r}")
if IMAGE_PROVIDER == "gemini":
    DEFAULT_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image")
else:
    DEFAULT_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "chatgpt-image-latest")
GEMINI_ASPECT_RATIO = os.getenv("GEMINI_ASPECT_RATIO", "1:1")
# The text model only verifies images, writes a short blurb and scripts the GIF
# motion, so a mini model at low reasoning effort is plenty and far cheaper.
DEFAULT_TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-5.4-mini")
TEXT_REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "low")
DEFAULT_OUTPUT_SIZE = os.getenv("OPENAI_IMAGE_SIZE", "1024x1024")
# Keep the daily image at high quality and high input fidelity: medium quality
# loses the bear's fine details (nose, mouth), which matter most.
DEFAULT_OUTPUT_QUALITY = os.getenv("OPENAI_IMAGE_QUALITY", "high")
DEFAULT_OUTPUT_FORMAT = os.getenv("OPENAI_IMAGE_FORMAT", "jpeg")
DEFAULT_OUTPUT_COMPRESSION = int(os.getenv("OPENAI_IMAGE_COMPRESSION", "90"))
DEFAULT_INPUT_FIDELITY = os.getenv("OPENAI_INPUT_FIDELITY", "high")
DEFAULT_MAX_ATTEMPTS = int(os.getenv("OPENAI_IMAGE_MAX_ATTEMPTS", "4"))
DEFAULT_GIF_SECONDS = float(os.getenv("ICEBEAR_GIF_SECONDS", "3"))
DEFAULT_GIF_WIDTH = int(os.getenv("ICEBEAR_GIF_WIDTH", "1024"))
GIF_KEYFRAMES = int(os.getenv("ICEBEAR_GIF_KEYFRAMES", "4"))
GIF_FRAME_QUALITY = os.getenv("ICEBEAR_GIF_QUALITY", "high")
GIF_INPUT_FIDELITY = os.getenv("ICEBEAR_GIF_INPUT_FIDELITY", "high")
# How much a pixel (0-255, after a slight blur) must change between the still and a
# keyframe to count as the bear moving rather than redraw noise.
GIF_MOTION_THRESHOLD = int(os.getenv("ICEBEAR_GIF_MOTION_THRESHOLD", "60"))

MEDIA_ROOT = Path("./media")
MEDIA_DIR = MEDIA_ROOT / f"pid-{os.getpid()}"
SEARCH_IMAGES_DIR = MEDIA_DIR / "search_images"
ARTWORKS_JSON = Path("./artworks.json")
DIRECT_INPUT_DIR = MEDIA_DIR / "direct_inputs"
MAX_REFERENCE_DOWNLOADS = 3
MAX_ARTWORK_TRIES = 10
MAX_IMAGE_VERIFY_TRIES = int(os.getenv("OPENAI_IMAGE_VERIFY_TRIES", "3"))
# Artworks for which no reference image could be found; later runs skip them
# instead of paying to search for them again.
FAILED_ARTWORKS_JSON = Path("./failed_artworks.json")
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
        help=f"Image model for ICEBEAR_IMAGE_PROVIDER={IMAGE_PROVIDER} (default: {DEFAULT_IMAGE_MODEL})",
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
    parser.add_argument(
        "--gif",
        action="store_true",
        help="Also generate a short animated GIF of Ice Bear doing his activity in the artwork",
    )
    parser.add_argument(
        "--gif-seconds",
        type=float,
        default=DEFAULT_GIF_SECONDS,
        help=f"GIF length in seconds (default: {DEFAULT_GIF_SECONDS:g})",
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


def _read_failed_entries() -> list[dict[str, Any]]:
    try:
        with FAILED_ARTWORKS_JSON.open("r", encoding="utf-8") as f:
            entries = json.load(f)
    except FileNotFoundError:
        return []
    except (OSError, json.JSONDecodeError) as e:
        print(f"Ignoring unreadable {FAILED_ARTWORKS_JSON}: {e}")
        return []
    return [e for e in entries if isinstance(e, dict) and "title" in e and "artist" in e]


def load_failed_artworks() -> set[tuple[str, str]]:
    return {(e["title"], e["artist"]) for e in _read_failed_entries()}


def record_failed_artwork(artwork: Artwork, reason: str) -> None:
    """Remember an artwork with no findable reference image, so it is not searched again.

    Delete its entry from the file to make it eligible again.
    """
    entries = _read_failed_entries()
    if any(e["title"] == artwork.title and e["artist"] == artwork.artist for e in entries):
        return
    entries.append(
        {
            "title": artwork.title,
            "artist": artwork.artist,
            "reason": reason,
            "date": datetime.today().strftime("%Y-%m-%d"),
        }
    )
    with FAILED_ARTWORKS_JSON.open("w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


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
                reasoning={"effort": TEXT_REASONING_EFFORT},
                input=prompt,
                **extra,
            )
        except BadRequestError as e:
            last_error = e
            print(f"Retrying ChatGPT image search with a simpler request: {e}")

    raise RuntimeError(f"ChatGPT image search failed: {last_error}")


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "yes", "y", "match", "matches"}:
            return True
        if text in {"false", "no", "n", "mismatch"}:
            return False
    return None


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
- really look at the image itself to determine if it is likely correct, does it make sense with respect to the title and background you know about the artwork?
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


def _google_image_search_query(artwork: Artwork) -> str:
    query = f"High quality image of {artwork.title} by {artwork.artist}"
    if artwork.year:
        query += f" {artwork.year}"
    return query


def find_artwork_image_urls_via_google(artwork: Artwork) -> list[str]:
    query = _google_image_search_query(artwork)
    print(f"Searching Google Images for: {query}")

    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
    if not api_key or not engine_id:
        raise RuntimeError(
            "Google image search fallback requires GOOGLE_SEARCH_API_KEY and "
            "GOOGLE_SEARCH_ENGINE_ID"
        )

    response_file = google_search_api_call(query)
    links_and_format_pairs, _search_terms = google_search_response_parser(response_file)
    urls = [item["link"] for item in links_and_format_pairs if item.get("link")]
    if not urls:
        raise FileNotFoundError(
            f"Google image search returned no results for {artwork.title} by {artwork.artist}"
        )

    print(f"Google search selected {len(urls)} candidate image URL(s)")
    for index, url in enumerate(urls, start=1):
        print(f"  {index}. {url}")
    return urls


def _image_data_url(image_path: Path, max_dimension: int = 1024) -> str:
    """Return a downscaled JPEG data URL so verification stays cheap."""
    with Image.open(image_path) as image:
        image = normalize_for_jpeg(image)
        if max(image.size) > max_dimension:
            image.thumbnail((max_dimension, max_dimension))
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=85)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def verify_image_matches_artwork(
    client: OpenAI,
    text_model: str,
    artwork: Artwork,
    image_path: Path,
) -> tuple[bool, str]:
    """Ask ChatGPT to look at the downloaded image and confirm it is this artwork."""
    try:
        data_url = _image_data_url(image_path)
    except Exception as e:
        return False, f"could not read the downloaded image: {e}"

    prompt = f"""You are verifying whether an image really depicts one specific artwork.

{artwork.search_description()}

Look at the attached image and decide whether it is a reproduction of THIS exact artwork.

Answer with matches=false if the image is any of:
- a different work, including another work by the same artist or a similarly titled work
- a tribute, parody, meme, AI remix, fan art, or merchandise/product photo
- a photo or portrait of the artist, a book cover, a gallery interior, or a museum wall label
- a heavily cropped detail, a watermarked or illegible thumbnail, or an error/placeholder image

A straight reproduction of the work counts as a match even if it includes the frame or is
photographed at a slight angle.

Return JSON only, with no markdown:
{{"matches": true, "reason": "one short sentence"}}
"""

    try:
        response = client.responses.create(
            model=text_model,
            reasoning={"effort": TEXT_REASONING_EFFORT},
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": data_url, "detail": "low"},
                    ],
                }
            ],
        )
    except Exception as e:
        return False, f"verification request failed: {e}"

    text = (response.output_text or "").strip()
    if not text:
        return False, "verification returned no text"

    try:
        payload = _extract_json_object(text)
    except (json.JSONDecodeError, ValueError) as e:
        return False, f"could not parse verification JSON: {e}"

    matches = _as_bool(payload.get("matches"))
    reason = str(payload.get("reason") or "").strip() or "no reason given"
    if matches is None:
        return False, f"verification did not report a verdict: {reason}"
    return matches, reason


def download_reference_images(
    artwork: Artwork,
    urls: list[str],
    source_label: str,
    client: OpenAI,
    text_model: str,
    verify_budget: int,
) -> tuple[list[Path], int]:
    """Download candidates and keep only those ChatGPT confirms are this artwork.

    Returns the verified images plus the number of candidates rejected by
    verification. Stops once `verify_budget` candidates have been rejected;
    a budget of 0 or less skips verification entirely.
    """
    download_dir = SEARCH_IMAGES_DIR / _sanitize_filename(f"{artwork.title}_{artwork.artist}")
    download_dir.mkdir(parents=True, exist_ok=True)

    verified: list[Path] = []
    rejected = 0
    for index, url in enumerate(urls):
        if len(verified) >= MAX_REFERENCE_DOWNLOADS:
            break
        if verify_budget > 0 and rejected >= verify_budget:
            print(f"Giving up on {source_label} candidates after {rejected} rejected image(s)")
            break

        destination = download_dir / _filename_for_url(url, artwork, index)
        try:
            path = download_image_from_url(url, destination)
        except Exception as e:
            print(f"Failed to download {url}: {e}")
            continue
        print(f"Downloaded {source_label} image: {url} -> {path}")

        if verify_budget <= 0:
            verified.append(path)
            continue

        matches, reason = verify_image_matches_artwork(client, text_model, artwork, path)
        if not matches:
            rejected += 1
            print(
                f"Rejected candidate {rejected}/{verify_budget} ({url}): {reason}"
            )
            path.unlink(missing_ok=True)
            continue

        print(f"Verified candidate image {path}: {reason}")
        verified.append(path)

    return verified, rejected


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

    # Google image search first: it is nearly free, while an OpenAI web search is
    # billed per call plus the search results as input tokens. Each source gets
    # its own verification budget.
    google_rejected = 0
    try:
        urls = find_artwork_image_urls_via_google(artwork)
    except Exception as e:
        print(f"Google image search failed ({e}); falling back to ChatGPT web search")
    else:
        images, google_rejected = download_reference_images(
            artwork, urls, "Google-selected", client, text_model, MAX_IMAGE_VERIFY_TRIES
        )
        if images:
            return images
        print(
            "No Google-selected candidate passed image verification; "
            "falling back to ChatGPT web search"
        )

    try:
        urls = find_artwork_image_urls(client, text_model, artwork)
    except LowConfidenceImageMatch as e:
        raise LowConfidenceImageMatch(
            artwork,
            f"Google found no verified image and ChatGPT could not confidently find one "
            f"({e.reason})",
        ) from e

    images, chatgpt_rejected = download_reference_images(
        artwork, urls, "ChatGPT-selected", client, text_model, MAX_IMAGE_VERIFY_TRIES
    )
    if images:
        return images

    raise LowConfidenceImageMatch(
        artwork,
        f"no candidate image passed image verification "
        f"({google_rejected + chatgpt_rejected} rejected across Google and ChatGPT results)",
    )




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


class GeminiError(RuntimeError):
    pass


def _mime_type_for(path: Path) -> str:
    return {
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(path.suffix.lower(), "image/jpeg")


def edit_image(
    client: OpenAI,
    image_model: str,
    image_bytes: bytes,
    mime_type: str,
    prompt: str,
    quality: str,
    input_fidelity: str,
    output_format: str,
) -> Image.Image:
    """Edit one image with the configured provider and return the result.

    `quality`, `input_fidelity` and `output_format` only apply to OpenAI; Gemini
    has no equivalent settings.
    """
    if IMAGE_PROVIDER == "gemini":
        return gemini_edit_image(image_model, image_bytes, mime_type, prompt)

    result = client.images.edit(
        model=image_model,
        image=(f"source{_extension_for_mime(mime_type)}", image_bytes, mime_type),
        prompt=prompt,
        size=DEFAULT_OUTPUT_SIZE,
        quality=quality,
        output_format=output_format,
        **({"output_compression": DEFAULT_OUTPUT_COMPRESSION} if output_format != "png" else {}),
        input_fidelity=input_fidelity,
    )
    if not result.data or not result.data[0].b64_json:
        raise RuntimeError("No image data returned from OpenAI")
    return decode_b64_image_to_pil(result.data[0].b64_json)


def _extension_for_mime(mime_type: str) -> str:
    return {"image/png": ".png", "image/webp": ".webp"}.get(mime_type, ".jpg")


def _gemini_request_target(model: str) -> tuple[str, dict[str, str]]:
    """Return the URL and auth headers for a Gemini generateContent call.

    With GEMINI_VERTEX_PROJECT set, calls go through Vertex AI using Application
    Default Credentials and are billed to that Google Cloud project. Otherwise
    they go to the Gemini API with GEMINI_API_KEY (AI Studio billing).
    """
    project = os.getenv("GEMINI_VERTEX_PROJECT")
    if project:
        location = os.getenv("GEMINI_VERTEX_LOCATION", "global")
        host = "aiplatform.googleapis.com" if location == "global" else f"{location}-aiplatform.googleapis.com"
        url = (
            f"https://{host}/v1/projects/{project}/locations/{location}"
            f"/publishers/google/models/{model}:generateContent"
        )
        return url, {
            "Authorization": f"Bearer {_gcloud_access_token()}",
            "x-goog-user-project": project,
        }

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ICEBEAR_IMAGE_PROVIDER=gemini needs GEMINI_API_KEY, or GEMINI_VERTEX_PROJECT "
            "to use Vertex AI with Application Default Credentials"
        )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    return url, {"x-goog-api-key": api_key}


def _gcloud_access_token() -> str:
    # cron runs with a short PATH, so also look in the usual install locations
    # (macOS SDK, Homebrew, Debian/Ubuntu packages, snap). GCLOUD_PATH overrides.
    candidates = [
        os.getenv("GCLOUD_PATH"),
        shutil.which("gcloud"),
        str(Path.home() / "google-cloud-sdk/bin/gcloud"),
        "/opt/homebrew/bin/gcloud",
        "/usr/local/bin/gcloud",
        "/usr/bin/gcloud",
        "/snap/bin/gcloud",
        "/usr/lib/google-cloud-sdk/bin/gcloud",
    ]
    gcloud = next((c for c in candidates if c and Path(c).exists()), None)
    if not gcloud:
        raise RuntimeError("GEMINI_VERTEX_PROJECT is set but the gcloud command was not found")
    result = subprocess.run(
        [gcloud, "auth", "application-default", "print-access-token"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    token = result.stdout.strip()
    if result.returncode != 0 or not token:
        raise RuntimeError(
            "Could not get an Application Default Credentials token; run "
            f"'gcloud auth application-default login'. {result.stderr.strip()[:300]}"
        )
    return token


def gemini_edit_image(model: str, image_bytes: bytes, mime_type: str, prompt: str) -> Image.Image:
    url, headers = _gemini_request_target(model)
    body = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64.b64encode(image_bytes).decode("ascii"),
                        }
                    },
                ],
            }
        ],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {"aspectRatio": GEMINI_ASPECT_RATIO},
        },
    }
    # Vertex AI's shared capacity answers 429 when busy; wait and retry those and
    # temporary server errors before giving up.
    for wait in (15, 45, 90, None):
        response = requests.post(url, headers=headers, json=body, timeout=300)
        if response.status_code not in (429, 500, 503) or wait is None:
            break
        print(f"Gemini returned HTTP {response.status_code}; retrying in {wait}s")
        time.sleep(wait)
    try:
        payload = response.json()
    except ValueError:
        raise GeminiError(f"HTTP {response.status_code}: {response.text[:300]}")
    if "error" in payload:
        raise GeminiError(f"HTTP {response.status_code}: {payload['error'].get('message')}")

    candidates = payload.get("candidates") or []
    for candidate in candidates:
        for part in (candidate.get("content") or {}).get("parts") or []:
            data = part.get("inlineData") or part.get("inline_data")
            if data and data.get("data"):
                return Image.open(io.BytesIO(base64.b64decode(data["data"]))).copy()

    reason = candidates[0].get("finishReason") if candidates else None
    feedback = payload.get("promptFeedback")
    raise GeminiError(f"no image returned (finishReason={reason}, promptFeedback={feedback})")


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
            pil_image = edit_image(
                client,
                image_model,
                source_path.read_bytes(),
                _mime_type_for(source_path),
                prompt,
                quality=DEFAULT_OUTPUT_QUALITY,
                input_fidelity=DEFAULT_INPUT_FIDELITY,
                output_format=DEFAULT_OUTPUT_FORMAT,
            )
            save_image(pil_image, output_path, DEFAULT_OUTPUT_FORMAT)
            print(f"Saved edited image to: {output_path}")
            return output_path

        except BadRequestError as e:
            last_error = e
            print(f"OpenAI rejected attempt {attempt}: {e}")
            continue
        except GeminiError as e:
            last_error = e
            print(f"Gemini rejected attempt {attempt}: {e}")
            continue
        except Exception as e:
            last_error = e
            print(f"Unexpected error on attempt {attempt}: {e}")
            continue

    raise RuntimeError(f"Failed to generate edited image after {attempts} attempts: {last_error}")


def describe_bear_motion(
    client: OpenAI,
    text_model: str,
    artwork: Artwork,
    image_path: Path,
    seconds: float,
) -> str:
    """Ask ChatGPT to look at the edited still and script a short loop of Ice Bear's activity."""
    fallback = (
        "The polar bear continues the activity he is doing in the scene with small, "
        "deliberate, stoic movements."
    )
    prompt = f"""This image is a reinterpretation of "{artwork.title}" by {artwork.artist},
with a cartoon polar bear (in the style of Ice Bear from "We Bare Bears") added to the scene.

Describe, in 2-3 sentences, a {seconds:g}-second animation of this exact image in which the
bear performs the activity he is already doing (e.g. rowing, painting, eating, walking),
with a natural, simple motion that could loop. Other figures and elements may move subtly
(water ripples, wind, flickering light) where it suits the scene. The camera stays still.

Return only the description, no preamble."""

    try:
        response = client.responses.create(
            model=text_model,
            reasoning={"effort": TEXT_REASONING_EFFORT},
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": _image_data_url(image_path)},
                    ],
                }
            ],
        )
    except Exception as e:
        print(f"Could not describe bear motion, using a generic one: {e}")
        return fallback

    text = (response.output_text or "").strip()
    return text or fallback


def generate_gif_from_frames(
    client: OpenAI,
    image_model: str,
    still_path: Path,
    gif_path: Path,
    motion: str,
    seconds: float,
) -> Path:
    """Edit the still into a few poses of the activity and loop them back and forth."""
    with Image.open(still_path) as still:
        frames = [normalize_for_jpeg(still).copy()]

    # Every keyframe is edited from the sharp still, not from the previous keyframe:
    # chaining edits redraws the bear again for each frame and he degrades a little
    # more every time.
    source = io.BytesIO()
    frames[0].save(source, "PNG")
    for index in range(1, GIF_KEYFRAMES):
        progress = round(100 * index / (GIF_KEYFRAMES - 1))
        prompt = f"""This image shows a cartoon polar bear (Ice Bear) in an artwork. {motion}

Show the bear {progress}% of the way through that motion, as one keyframe of a short
animation that starts from exactly this image. Change ONLY the bear's pose (and anything he
is directly holding or moving), keeping the motion small and his face, proportions, line
work and colors exactly as drawn. Everything else in the image must stay pixel-for-pixel
identical: composition, framing, colors, style, other figures, background."""
        # The model sometimes hands the still back unchanged; try once more before
        # settling for a frame without motion.
        for attempt in range(2):
            print(f"Generating GIF keyframe {index + 1}/{GIF_KEYFRAMES}...")
            frame = edit_image(
                client,
                image_model,
                source.getvalue(),
                "image/png",
                prompt,
                quality=GIF_FRAME_QUALITY,
                input_fidelity=GIF_INPUT_FIDELITY,
                output_format="png",
            )
            frame = normalize_for_jpeg(frame)
            frame = frame.resize(frames[0].size, Image.LANCZOS)
            locked = lock_background(frames[0], frame)
            if locked is not frames[0]:
                break
        frames.append(locked)

    if DEFAULT_GIF_WIDTH < frames[0].width:
        height = round(frames[0].height * DEFAULT_GIF_WIDTH / frames[0].width)
        frames = [frame.resize((DEFAULT_GIF_WIDTH, height), Image.LANCZOS) for frame in frames]
    keyframes = quantize_with_shared_palette(frames)

    # Ping-pong so the loop has no jump back to the first pose.
    sequence = keyframes + keyframes[-2:0:-1]
    duration_ms = max(80, int(seconds * 1000 / len(sequence)))
    sequence[0].save(
        gif_path,
        "GIF",
        save_all=True,
        append_images=sequence[1:],
        duration=duration_ms,
        loop=0,
        optimize=False,  # keep the shared palette as built
    )
    return gif_path


def lock_background(still: Image.Image, frame: Image.Image) -> Image.Image:
    """Keep the generated frame only where the bear moved; elsewhere use the still.

    The image model redraws the whole picture for every keyframe, so the background
    drifts and softens from frame to frame. Pasting the new pose onto the original
    still keeps everything else sharp and steady.
    """
    # Mark pixels that changed strongly (after a slight blur, so redraw grain doesn't
    # count), then mark each 16px block where at least 5% of pixels did. Counting
    # strong pixels instead of averaging the difference keeps thin moved objects,
    # such as a stick the bear picked up, whose old position must also be covered.
    # Upscaling the mask afterwards feathers its edge.
    small = (still.width // 16, still.height // 16)
    diff = ImageChops.difference(
        still.filter(ImageFilter.GaussianBlur(1)), frame.filter(ImageFilter.GaussianBlur(1))
    ).convert("L")
    strong = diff.point(lambda v: 255 if v > GIF_MOTION_THRESHOLD else 0)
    moved = strong.resize(small, Image.BOX).point(lambda v: 255 if v > 13 else 0)
    # Drop isolated blocks: keep a block only if another block next to it also changed.
    # (Eroding instead would also drop thin objects, leaving e.g. the old stick behind.)
    neighbours = moved.filter(ImageFilter.Kernel((3, 3), [1] * 9, scale=9))
    moved = ImageChops.multiply(moved, neighbours.point(lambda v: 255 if v > 50 else 0))
    bbox = moved.getbbox()
    if bbox is None:
        print("Keyframe: no visible motion")
        return still

    # Paste one whole padded box around everything that moved. A mask shaped to the
    # changed pixels misses parts of a moving head and leaves a ghost of the old one.
    pad = max(2, max(small) // 12)
    left, top, right, bottom = bbox
    box = (
        max(0, left - pad),
        max(0, top - pad),
        min(small[0], right + pad),
        min(small[1], bottom + pad),
    )
    coverage = (box[2] - box[0]) * (box[3] - box[1]) / (small[0] * small[1])
    if coverage > 0.6:
        # The model moved the whole scene; a patch would show a seam, so keep it all.
        print(f"Keyframe differs over {coverage:.0%} of the image; using it whole")
        return frame
    print(f"Keyframe: keeping the new pose over {coverage:.0%} of the image")

    mask = Image.new("L", small, 0)
    mask.paste(255, box)
    mask = mask.filter(ImageFilter.GaussianBlur(pad / 3)).resize(still.size, Image.BILINEAR)
    return Image.composite(frame, still, mask)


def quantize_with_shared_palette(frames: list[Image.Image]) -> list[Image.Image]:
    """Reduce every frame to one 256-colour palette built from all of them.

    A palette per frame makes colours flicker between frames; a shared one keeps the
    still parts of the scene identical.
    """
    width, height = frames[0].size
    strip = Image.new("RGB", (width, height * len(frames)))
    for index, frame in enumerate(frames):
        strip.paste(frame, (0, height * index))
    palette = strip.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    return [
        frame.quantize(palette=palette, dither=Image.Dither.FLOYDSTEINBERG)
        for frame in frames
    ]


def generate_gif(
    client: OpenAI,
    args: argparse.Namespace,
    artwork: Artwork,
    still_path: Path,
) -> Path:
    gif_path = still_path.with_suffix(".gif")
    motion = describe_bear_motion(client, args.text_model, artwork, still_path, args.gif_seconds)
    print(f"Bear motion: {motion}")

    generate_gif_from_frames(
        client, args.image_model, still_path, gif_path, motion, args.gif_seconds
    )
    print(f"Saved animated GIF to: {gif_path}")
    return gif_path


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
        reasoning={"effort": TEXT_REASONING_EFFORT},
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
    gif_path: Path | None = None,
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

    if gif_path and gif_path.exists():
        files.append(("inline", (gif_path.name, gif_path.open("rb"))))

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
    failed = load_failed_artworks()
    if failed:
        print(f"Skipping {len(failed)} artwork(s) with no findable image ({FAILED_ARTWORKS_JSON})")

    for attempt in range(1, max_tries + 1):
        try:
            artwork = pick_artwork(args, artworks, exclude=tried | failed)
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
            if not args.artwork:
                record_failed_artwork(artwork, e.reason)

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

    gif_path: Path | None = None
    if args.gif:
        # The still is the main event; a failed animation should not cost us the email.
        try:
            gif_path = generate_gif(client, args, artwork, edited_image_path)
        except Exception as e:
            print(f"Could not generate animated GIF, sending the still only: {e}")

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
        gif_path=gif_path,
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
