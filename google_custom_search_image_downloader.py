import json
import requests
import os
import re
import PIL
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from dotenv import load_dotenv
import subprocess
import time
from datetime import datetime

DOWNLOAD_MAX_WORKERS = int(os.getenv("GOOGLE_IMAGE_DOWNLOAD_WORKERS", "8"))

load_dotenv()


def _sanitize_for_filename(value: str) -> str:
    """Make a string safe to use as a filesystem path component.

    Replaces any character that isn't alphanumeric, dash, underscore, or dot
    with an underscore. This prevents apostrophes (e.g. "Christina's") and
    other shell/filesystem-unfriendly characters from breaking downstream
    path handling.
    """
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_") or "query"


def google_search_api_call(query):
    os.makedirs("media", exist_ok=True)
    os.makedirs("media/google_search_responses", exist_ok=True)
    
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": query,
        "key": os.getenv("GOOGLE_SEARCH_API_KEY"),
        "cx": os.getenv("GOOGLE_SEARCH_ENGINE_ID"),
        "searchType": "image",
        "imgSize": "large",
        "num": 10,
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        raise Exception(f"Error: {response.status_code} {response.text}")

    data = json.loads(response.text)

    data["queries"]["request"][0]["searchTerms"] = query
    safe_query = _sanitize_for_filename(query)

    with open(
        f"media/google_search_responses/{datetime.now().strftime('%Y-%m-%d')}-{safe_query}.json",
        "w",
    ) as file:
        json.dump(data, file, indent=4)

    return file.name


def google_search_response_parser(file_name):
    with open(file_name, "r") as file:
        data = json.load(file)
    items = data["items"]
    link_and_format_pairs = [
        {"link": item["link"], "format": item["fileFormat"]} for item in items
    ]
    search_query = _sanitize_for_filename(
        str(data["queries"]["request"][0]["searchTerms"])
    )

    return [link_and_format_pairs, search_query]


_FORMAT_TO_EXT = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}


def _download_one(link: str, output_path: str) -> tuple[str, bool, str | None]:
    """Download a single URL to output_path. Returns (link, ok, error)."""
    try:
        result = subprocess.run(
            ["curl", "-fL", "--max-time", "60", link, "-o", output_path],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return (link, False, (result.stderr or "").strip() or f"curl exit {result.returncode}")
        return (link, True, None)
    except Exception as e:
        return (link, False, str(e))


def download_images(links_and_format_pairs: list[dict], search_terms: str):
    os.makedirs("media", exist_ok=True)
    os.makedirs(f"media/search_images/{search_terms}", exist_ok=True)

    jobs: list[tuple[str, str]] = []
    for index, link_and_format_pair in enumerate(links_and_format_pairs):
        file_format = _FORMAT_TO_EXT.get(link_and_format_pair["format"])
        if not file_format:
            print(f"Skipping {link_and_format_pair['link']} because it is not an image")
            continue

        output_path = f"media/search_images/{search_terms}/{index}.{file_format}"
        jobs.append((link_and_format_pair["link"], output_path))

    if not jobs:
        return

    workers = max(1, min(DOWNLOAD_MAX_WORKERS, len(jobs)))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_download_one, link, path) for link, path in jobs]
        for future in as_completed(futures):
            link, ok, err = future.result()
            if ok:
                print(f"Downloaded {link}")
            else:
                print(f"Failed to download {link}: {err}")
