from openai import OpenAI, BadRequestError
import os
import json
import base64
import random
from datetime import datetime
import requests
import argparse
from dotenv import load_dotenv
from PIL import Image
import io
import glob
from google_custom_search_image_downloader import (
    google_search_api_call,
    google_search_response_parser,
    download_images,
)

# Parse command line arguments
parser = argparse.ArgumentParser(description="Generate IceBear artwork images")
parser.add_argument("--env", type=str, help="Path to .env file (optional)")
parser.add_argument("--sourcedir", type=str, help="Path to image file (optional)")
args = parser.parse_args()

args.sourcedir = args.sourcedir or None

# Load environment variables
load_dotenv(dotenv_path=args.env, override=True)

with open("artworks.json", "r", encoding="utf-8") as f:
    artworks = json.load(f)

target_date = datetime(2025, 4, 29)

today = datetime.today()

difference = (target_date - today).days


def create_prompt(bear_modifier=""):
    return f""" {bear_modifier}. Edit this image to feature a cartoon polar bear 
  inspired by Ice Bear from
 "We Bare Bears". The polar bear should be well integrated into the
 style and spirit of the original artwork. If the original artwork
 contains people, consider substituting the polar bear for one or more
 of them, or adding it alongside them. If there are no people,
 incorporate the polar bear creatively into the scene. If the artwork
 is abstract, the polar bear's depiction should also be abstract,
 matching the original style. The goal is for the polar bear to appear
 as if it were part of the original artist's composition. If multiple
 people are in the original, you might include other "We Bare Bears"
 characters, such as Griz or Panda,but ensure Ice Bear is prominent.
 Sometimes, include human figures alongside the bears to maintain the
 original's essence. Again, The polar bear should be well integrated
 into the style and spirit of the original artwork, in terms of
 drawing, paint, colors, texture, and in relation to the objects and
 activities in the scene. If there is some principal or background
 activity, the bear should be engaged in it. Even the facial
 expression and gaze on the bear should match the feel and intent of
 the scene. The artwork must be constructed so that in no way would
 cause violation of openAI image generation guidelines. Make every
 effort to make Ice Bear or bears blend in with the style and
 background, e.g., wear the same type of clothing, use same kind of
 lighting, shadows, coloring, and brush strokes, be properly occluded
 by objects in the scene. If the original is a sculpture, make a rendering
 of a scuplture with the bear modifications. The intent of the artwork must guide how the
 bear or bears are integrated into it. Artworks are unique because of
 the particular style they have, so use the original as a very literal
 guide, to preserve that unique style and colors, textures, technqiue,
 really the appearance must match up as much as possible. If there is text in the
artwork image, put in just a subtle references to bears or to Ice Bear, either
altering a single name to have some bear-like reference or a altering single word to be more  bear-like. Don't overdo it, be
subtle.  """


alternate_prompts = [
    "Generate an image which takes inspiration from the artwork",
    "Generate an image  with a cartoon polar bear, loosely inspired by Ice Bear from We Bare Bears, thoughtfully integrated into the scene, either as main subject or an observer,  which takes inspiration from the artwork ",
    "Generate an image which one might imagine had resemblance to an artwork where a cartoon polar bear, one could say resembling Ice Bear, is subtly hidden within the composition, which takes inspiration from the artwork ",
    "Generate an image  which, featuring a solitary cartoon polar bear akin to Ice Bear, as the central figure, does reinterpretation of the original artwork's theme, but in no way would cause violation of your guidelines using as a theme the artwork ",
]


artwork_choice = random.choice(artworks)

media_dir = "./media"
if not os.path.exists(media_dir):
    os.makedirs(media_dir)

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"), organization=os.getenv("OPENAI_ORG_ID")
)


image_generated = False
N_PROMPTS = 8
if not args.sourcedir:
    file_name = google_search_api_call(
        f"High quality image of {artwork_choice['title']} by {artwork_choice['artist']}"
    )
    links_and_format_pairs, search_terms = google_search_response_parser(file_name)
    download_images(links_and_format_pairs, search_terms)

    image_files = glob.glob(f"{media_dir}/search_images/{search_terms}/*")
    image_files.sort()
else:
    image_files = glob.glob(f"{args.sourcedir}/*")
    image_files.sort()

image_generated = False
N_PROMPTS = 8

for i in range(0, N_PROMPTS):
    try:
        prompt = create_prompt(random.choice(alternate_prompts))
        print(f"Attempt {i+1} with prompt: {prompt}")

        image_filename = f"{artwork_choice['title'].replace(' ', '_')}-{today.strftime('%Y-%m-%d')}.jpg"
        image_filepath = os.path.join(media_dir, image_filename)
        with open(image_files[0], "rb") as image_file:
            result = client.images.edit(
                image=image_file, prompt=prompt, model="gpt-image-1"
            )
        image_base64 = result.data[0].b64_json
        if image_base64 is None:
            raise ValueError("No image data returned from API")
        image_bytes = base64.b64decode(image_base64)

        # Convert PNG to JPG using PIL
        png_image = Image.open(io.BytesIO(image_bytes))
        # Convert to RGB if necessary (PNG might have transparency)
        if png_image.mode in ("RGBA", "LA", "P"):
            rgb_image = Image.new("RGB", png_image.size, (255, 255, 255))
            if png_image.mode == "P":
                png_image = png_image.convert("RGBA")
            rgb_image.paste(
                png_image,
                mask=(
                    png_image.split()[-1] if png_image.mode in ("RGBA", "LA") else None
                ),
            )
            png_image = rgb_image

        # Save as JPG
        png_image.save(image_filepath, "JPEG", quality=95)
        print(
            f"Image generated for {artwork_choice['title']} by {artwork_choice['artist']}"
        )
        image_generated = True
        break
    except BadRequestError as e:
        print(f"Attempt {i+1} failed with BadRequestError: {e}")
        if i < N_PROMPTS:
            print("Retrying with an alternate prompt...")
        else:
            print("All prompts failed.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        break

if not image_generated:
    print("Failed to generate image after multiple attempts.")
    # Optionally, handle the failure e.g., by exiting or sending a different email
    exit()

# Generate a simple blurb about the days artwork
blurb_prompt = f"""Please write an extremely brief and concise, non-judgmental analytical blurb about the artwork titled {artwork_choice['title']} by {artwork_choice['artist']}. Include only its historical context and any specific, verifiable details 
related to its creation (date, place, patronage, historical events influencing it, etc.). 
Do not offer opinions, interpretations, or evaluations. If any of those historical details are unknown or disputed, 
simply omit them. If possible, make this blurb read as if written by museum curator Dana Friis-Hansen.
"""

blurb_completion = client.chat.completions.create(
    model="gpt-5",
    messages=[
        {
            "role": "user",
            "content": blurb_prompt,
        }
    ],
)


blurb = blurb_completion.choices[0].message.content


data = {
    "from": f"Icebear Courier <{os.getenv('MAILGUN_FROM_EMAIL')}>",
    "to": f"{os.getenv('MAILGUN_TO_NAME')} <{os.getenv('MAILGUN_TO_EMAIL')}>",
    "subject": f"Icebear Artwork for today {today.strftime('%Y-%m-%d')}",
    "text": f"Todays artwork is {artwork_choice['title']} by {artwork_choice['artist']}. Have a great bear day! \n \nTODAYS DESCRIPTION: \n{blurb}",
}


if os.getenv("MAILGUN_CC_EMAILS"):
    cc_emails = os.getenv("MAILGUN_CC_EMAILS").split(",")
    data["cc"] = ", ".join(f"<{email.strip()}>" for email in cc_emails)

if os.path.exists(image_filepath):  # Only send email if image was generated
    print(
        requests.post(
            f"{os.getenv('MAILGUN_DOMAIN')}",
            auth=("api", os.environ["MAILGUN_API_KEY"]),
            files=[
                ("inline", open(image_filepath, "rb")),
                ("inline", open(image_files[0], "rb")),
            ],
            data=data,
        )
    )
    print(f"Email sent to {os.getenv('MAILGUN_TO_EMAIL')} with image {image_filename}")
else:
    print(f"Email not sent as image {image_filename} was not generated.")
