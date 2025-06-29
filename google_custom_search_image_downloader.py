import json
import requests
import os
import PIL
from io import BytesIO
from dotenv import load_dotenv
import subprocess
import time
from datetime import datetime

load_dotenv()


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
    query = query.strip().strip("/")

    with open(
        f"media/google_search_responses/{datetime.now().strftime('%Y-%m-%d')}-{query.replace(' ', '_').strip('/')}.json",
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
    search_query = str(data["queries"]["request"][0]["searchTerms"]).replace(" ", "_")

    return [link_and_format_pairs, search_query]


def download_images(links_and_format_pairs: list[dict], search_terms: str):
    os.makedirs("media", exist_ok=True)
    os.makedirs(f"media/search_images/{search_terms}", exist_ok=True)

    for index, link_and_format_pair in enumerate(links_and_format_pairs):

        file_format = "unknown"

        if (
            link_and_format_pair["format"] == "image/jpeg"
            or link_and_format_pair["format"] == "image/jpg"
        ):
            file_format = "jpg"
        elif link_and_format_pair["format"] == "image/png":
            file_format = "png"
        elif link_and_format_pair["format"] == "image/gif":
            file_format = "gif"
        elif link_and_format_pair["format"] == "image/webp":
            file_format = "webp"
        else:
            print(f"Skipping {link_and_format_pair['link']} because it is not an image")
            continue

        subprocess.run(
            f"curl -fL '{link_and_format_pair['link']}' -o 'media/search_images/{search_terms}/{index}.{file_format}' ",
            shell=True,
        )

        time.sleep(1)
