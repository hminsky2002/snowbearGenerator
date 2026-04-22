#!/usr/bin/env python3

from __future__ import annotations

import argparse
import base64
import glob
import io
import json
import os
import random
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from openai import BadRequestError, OpenAI
from PIL import Image

from google_custom_search_image_downloader import (
    download_images,
    google_search_api_call,
    google_search_response_parser,
)


DEFAULT_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "chatgpt-image-latest")
#DEFAULT_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
DEFAULT_TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-5.4")
DEFAULT_OUTPUT_SIZE = os.getenv("OPENAI_IMAGE_SIZE", "1024x1024")
DEFAULT_OUTPUT_QUALITY = os.getenv("OPENAI_IMAGE_QUALITY", "high")
DEFAULT_OUTPUT_FORMAT = os.getenv("OPENAI_IMAGE_FORMAT", "jpeg")
DEFAULT_OUTPUT_COMPRESSION = int(os.getenv("OPENAI_IMAGE_COMPRESSION", "90"))
DEFAULT_INPUT_FIDELITY = os.getenv("OPENAI_INPUT_FIDELITY", "high")
DEFAULT_MAX_ATTEMPTS = int(os.getenv("OPENAI_IMAGE_MAX_ATTEMPTS", "4"))

MEDIA_DIR = Path("./media")
SEARCH_IMAGES_DIR = MEDIA_DIR / "search_images"
ARTWORKS_JSON = Path("./artworks.json")
DIRECT_INPUT_DIR = MEDIA_DIR / "direct_inputs"


@dataclass
class Artwork:
    title: str
    artist: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Artwork":
        return cls(
            title=str(data["title"]).strip(),
            artist=str(data["artist"]).strip(),
        )

    def output_stem(self, today: datetime) -> str:
        safe_title = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in self.title)
        return f"{safe_title}-{today.strftime('%Y-%m-%d')}"


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
             "If omitted, the script falls back to Google search.",
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
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    SEARCH_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    DIRECT_INPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_artworks() -> list[Artwork]:
    if not ARTWORKS_JSON.exists():
        raise FileNotFoundError(f"Missing artworks file: {ARTWORKS_JSON}")
    with ARTWORKS_JSON.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return [Artwork.from_dict(item) for item in raw]


def pick_artwork(args: argparse.Namespace, artworks: list[Artwork]) -> Artwork:
    if args.artwork:
        try:
            payload = json.loads(args.artwork)
            artwork = Artwork.from_dict(payload)
            print(f"Using provided artwork: {artwork}")
            return artwork
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid --artwork JSON: {e}") from e
    artwork = random.choice(artworks)
    print(f"Randomly selected artwork: {artwork}")
    return artwork


def create_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    org_id = os.getenv("OPENAI_ORG_ID")
    if org_id:
        return OpenAI(api_key=api_key, organization=org_id)
    return OpenAI(api_key=api_key)


def is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def download_direct_image(image_url: str) -> Path:
    parsed = urlparse(image_url)
    filename = Path(parsed.path).name or "downloaded_image"
    suffix = Path(filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        filename = f"{filename}.jpg"

    destination = DIRECT_INPUT_DIR / filename

    response = requests.get(image_url, timeout=60)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "").lower()
    if not content_type.startswith("image/"):
        raise ValueError(f"URL does not appear to be an image: content-type={content_type}")

    destination.write_bytes(response.content)
    print(f"Downloaded direct image URL to: {destination}")
    return destination


def get_source_images(
    artwork: Artwork,
    sourcedir: str | None,
    image_source: str | None,
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

    # Default: Google search
    query = f"High quality image of {artwork.title} by {artwork.artist}"
    print(f"Searching reference images for: {query}")

    file_name = google_search_api_call(query)
    links_and_format_pairs, search_terms = google_search_response_parser(file_name)
    download_images(links_and_format_pairs, search_terms)

    download_dir = SEARCH_IMAGES_DIR / search_terms
    files = sorted([Path(p) for p in glob.glob(str(download_dir / "*"))])
    if not files:
        raise FileNotFoundError(f"No downloaded source images found in: {download_dir}")
    return files




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

Remember, make the polar bear appearance very very closely inspired by Ice Bear, the cartoon aspects are important,
do not deviate except as to add clothing or pose, but the rendering should closely adhere to your impressions of Ice Bear
as seen from the cartoon.

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
    artwork = pick_artwork(args, artworks)

    client = create_openai_client()

    source_images = get_source_images(
        artwork=artwork,
        sourcedir=args.sourcedir,
        image_source=args.image_source,
    )
    source_image = source_images[0]

    extension = {
        "jpeg": ".jpg",
        "png": ".png",
        "webp": ".webp",
    }.get(DEFAULT_OUTPUT_FORMAT.lower(), ".jpg")

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
