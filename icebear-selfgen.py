from openai import OpenAI, BadRequestError
import os
import base64
import random
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

load_dotenv()

def create_prompt():
    return f"""
Make a list of info about 100 iconic artworks, each entry having artist and title and year of creation,  at random picking artworks that are somewhat known but not so common that they have become cliche. Take another look at your list and remove overly publicized or overly well known art works.  Then pick a random entry from that list using a random number between 0 and 100 as an index ,   Then Pick an artwork at random from the remaining ones in your list. Remember the title, artist's name, and year that the artwork was created. You will need this later when 
titling an image you generate. 

Now, generate an image using the original artwork as inspiration  with a cartoon polar bear, loosely inspired by Ice Bear from We Bare Bears, thoughtfully integrated into the scene, either as main subject or an observer.
The image should feature a cartoon polar bear inspired by Ice Bear from "We Bare Bears".
The polar bear should be well integrated into the style and spirit of the original artwork.
If the original artwork contains people, consider substituting the polar bear for one or more of them, or adding it alongside them.
If there are no people, incorporate the polar bear creatively into the scene.
If the artwork is abstract, the polar bear's depiction should also be abstract, matching the original style.
The goal is for the polar bear to appear as if it were part of the original artist's composition.
If multiple people are in the original, you might include other "We Bare Bears" characters, such as Griz or Panda,but ensure Ice Bear is prominent.
Sometimes, include human figures alongside the bears to maintain the original's essence.
Again, The polar bear should be well integrated into the style and spirit of the original artwork, in terms of drawing, paint,
colors, texture, and in relation to the objects and activities in the scene.
The artwork must be constructed so that in no way would cause violation of openAI image generation guidelines.
Make every effort to make Ice Bear or bears blend in with the style and background, e.g., wear the same type of clothing,
use same kind of lighting, shadows, coloring,  and brush strokes, be properly occluded by objects in the scene. The intent of the
artwork must guide how the bear or bears are integrated into it. Also MAKE SURE to render into the image a text title which has the title of the original artwork, the artist, and what year the artwork was made, which you were careful to remember. We must give credit to the original artist by putting in this title caption. Make sure there is room in the image for the title, and artist info, so it is not cut off at the edge.

"""

today = datetime.today()


# Define the reference start time: January 1, 2025 at midnight UTC
start = datetime(2025, 1, 1, tzinfo=timezone.utc)

# Get the current time in UTC
now = datetime.now(timezone.utc)

# Compute the time difference in minutes
minutes_since_jan_2025 = int((now - start).total_seconds() // 60)

#print("Minutes since Jan 1, 2025:", minutes_since_jan_2025)



media_dir = "./media"
if not os.path.exists(media_dir):
    os.makedirs(media_dir)

image_filename = (
    f"bear-artwork-{minutes_since_jan_2025}{today.strftime('%Y-%m-%d')}.png"
)
image_filepath = os.path.join(media_dir, image_filename)

if not os.path.exists(image_filepath):
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"), organization=os.getenv("OPENAI_ORG_ID")
    )
    
    current_prompt = create_prompt()
    for i in range(0,5):
        if i >= 5: # Max 3 retries (initial + 2 alternates)
            print("Maximum retries reached. Could not generate image.")
            break
        try:
            print(f"Attempt {i+1} with prompt: {current_prompt}")
            result = client.images.generate(model="gpt-image-1", prompt=current_prompt)
            image_base64 = result.data[0].b64_json
            if image_base64 is None:
                raise ValueError("No image data returned from API")
            image_bytes = base64.b64decode(image_base64)

            with open(image_filepath, "wb") as f:
                f.write(image_bytes)
            print(
                f"Image generated"
            )
            image_generated = True
            break 
        except BadRequestError as e:
            print(f"Attempt {i+1} failed with BadRequestError: {e}")
            if i < len(prompts_to_try) -1:
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


data = {
    "from": f"Icebear Courier <{os.getenv('MAILGUN_FROM_EMAIL')}>",
    "to": f"{os.getenv('MAILGUN_TO_NAME')} <{os.getenv('MAILGUN_TO_EMAIL')}>",
    "subject": f"Icebear Artwork for today {today.strftime('%Y-%m-%d')}",
    "text": f"Here is today's iconic artwork. Have a great bear day!",
}


if os.getenv("MAILGUN_CC_EMAILS"):
    cc_emails = os.getenv("MAILGUN_CC_EMAILS").split(",")
    data["cc"] = ", ".join(f"<{email.strip()}>" for email in cc_emails)


if os.path.exists(image_filepath): # Only send email if image was generated
    requests.post(
        f"{os.getenv('MAILGUN_DOMAIN')}",
        auth=("api", os.environ["MAILGUN_API_KEY"]),
        files=[("inline", open(image_filepath, "rb"))],
        data=data,
    )
    print(f"Email sent to {os.getenv('MAILGUN_TO_EMAIL')} with image {image_filename}")
else:
    print(f"Email not sent as image {image_filename} was not generated.")
