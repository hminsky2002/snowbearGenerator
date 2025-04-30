from openai import OpenAI
import os
import base64
import random
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

artworks = [
    {"title": "I ❤️ NY", "artist": "Milton Glaser", "year": "1977"},
    {"title": "Vertigo", "artist": "Saul Bass", "year": "1958"},
    {"title": "Books!", "artist": "Alexander Rodchenko", "year": "1924"},
    {
        "title": "Moulin Rouge: La Goulue",
        "artist": "Henri de Toulouse-Lautrec",
        "year": "1891",
    },
    {"title": "Bob Dylan", "artist": "Milton Glaser", "year": "1966"},
    {"title": "The Arnolfini Portrait", "artist": "Jan van Eyck", "year": "1434"},
    {"title": "Jaws", "artist": "Bill Gold", "year": "1975"},
    {
        "title": "Liberty Leading the People",
        "artist": "Eugène Delacroix",
        "year": "1830",
    },
    {
        "title": "The Lady of Shalott",
        "artist": "John William Waterhouse",
        "year": "1888",
    },
    {"title": "Mona Lisa", "artist": "Leonardo da Vinci", "year": "c. 1503–1506"},
    {"title": "Dubonnet", "artist": "A. M. Cassandre", "year": "1932"},
    {"title": "The Garden of Love", "artist": "Peter Paul Rubens", "year": "1633"},
    {"title": "The Fighting Temeraire", "artist": "J.M.W. Turner", "year": "1839"},
    {"title": "The Persistence of Memory", "artist": "Salvador Dalí", "year": "1931"},
    {"title": "Ophelia", "artist": "John Everett Millais", "year": "1851–1852"},
    {"title": "The Man with the Golden Arm", "artist": "Saul Bass", "year": "1955"},
    {"title": "La Loïe Fuller", "artist": "Jules Chéret", "year": "1893"},
    {"title": "Starry Night", "artist": "Vincent van Gogh", "year": "1889"},
    {"title": "24 Heures du Mans", "artist": "A. M. Cassandre", "year": "1931"},
    {"title": "Hope", "artist": "Shepard Fairey", "year": "2008"},
    {"title": "The Son of Man", "artist": "René Magritte", "year": "1964"},
    {"title": "E.T. the Extra-Terrestrial", "artist": "John Alvin", "year": "1982"},
    {
        "title": "The Velvet Underground & Nico",
        "artist": "Andy Warhol",
        "year": "1967",
    },
    {
        "title": "The Garden of Earthly Delights",
        "artist": "Hieronymus Bosch",
        "year": "c. 1500",
    },
    {
        "title": "Never Mind the Bollocks, Here's the Sex Pistols",
        "artist": "Jamie Reid",
        "year": "1977",
    },
    {"title": "Gismonda", "artist": "Alphonse Mucha", "year": "1894"},
    {
        "title": "Self-Portrait with Thorn Necklace and Hummingbird",
        "artist": "Frida Kahlo",
        "year": "1940",
    },
    {
        "title": "Portrait of Adele Bloch-Bauer I",
        "artist": "Gustav Klimt",
        "year": "1907",
    },
    {"title": "The Avengers", "artist": "Tom Chantrell", "year": "1961"},
    {"title": "Whistler's Mother", "artist": "James McNeill Whistler", "year": "1871"},
    {"title": "Les Demoiselles d'Avignon", "artist": "Pablo Picasso", "year": "1907"},
    {
        "title": "Italian Futurist Exhibition",
        "artist": "F.T. Marinetti",
        "year": "1919",
    },
    {"title": "Visit California", "artist": "David Klein", "year": "1950"},
    {"title": "Star Wars", "artist": "Drew Struzan", "year": "1977"},
    {"title": "Goldfinger", "artist": "Robert McGinnis", "year": "1964"},
    {"title": "The Gulf Stream", "artist": "Winslow Homer", "year": "1899"},
    {"title": "Visit London", "artist": "Abram Games", "year": "1948"},
    {
        "title": "Saturn Devouring His Son",
        "artist": "Francisco Goya",
        "year": "1819–1823",
    },
    {"title": "Priester Matches", "artist": "Lucian Bernhard", "year": "1905"},
    {"title": "Drink Coca-Cola", "artist": "Haddon Sundblom", "year": "1940s"},
    {"title": "Composition VIII", "artist": "Wassily Kandinsky", "year": "1923"},
    {
        "title": "Woman with a Parasol – Madame Monet and Her Son",
        "artist": "Claude Monet",
        "year": "1875",
    },
    {"title": "Bauhaus Exhibition", "artist": "Herbert Bayer", "year": "1923"},
    {"title": "Salon des Cent", "artist": "Eugène Grasset", "year": "1896"},
    {"title": "Impression, Sunrise", "artist": "Claude Monet", "year": "1872"},
    {"title": "Fillmore Poster", "artist": "Wes Wilson", "year": "1966"},
    {"title": "Maurin Quina", "artist": "Leonetto Cappiello", "year": "1906"},
    {"title": "My Fair Lady", "artist": "Bob Peak", "year": "1964"},
    {"title": "Guernica", "artist": "Pablo Picasso", "year": "1937"},
    {"title": "TWA – Visit America", "artist": "David Klein", "year": "1957"},
    {"title": "Job", "artist": "Alphonse Mucha", "year": "1896"},
    {"title": "We Can Do It!", "artist": "J. Howard Miller", "year": "1943"},
    {
        "title": "A Sunday Afternoon on the Island of La Grande Jatte",
        "artist": "Georges Seurat",
        "year": "1886",
    },
    {"title": "Pink Floyd – The Wall", "artist": "Gerald Scarfe", "year": "1982"},
    {"title": "Woodstock", "artist": "Bob Masse", "year": "1969"},
    {"title": "Olympia", "artist": "Édouard Manet", "year": "1863"},
    {"title": "The Blue Boy", "artist": "Thomas Gainsborough", "year": "1770"},
    {
        "title": "London Transport – The Country Poster",
        "artist": "E. McKnight Kauffer",
        "year": "1939",
    },
    {"title": "Manoli Cigarettes", "artist": "Lucian Bernhard", "year": "1910"},
    {"title": "Depero Futurista", "artist": "Fortunato Depero", "year": "1927"},
    {"title": "The Scream", "artist": "Edvard Munch", "year": "1893"},
    {"title": "Buveurs de Quinas", "artist": "Leonetto Cappiello", "year": "1900"},
    {
        "title": "The Birth of Venus",
        "artist": "Sandro Botticelli",
        "year": "c. 1484–1486",
    },
    {"title": "The Last Supper", "artist": "Leonardo da Vinci", "year": "c. 1495–1498"},
    {"title": "West Side Story", "artist": "Saul Bass", "year": "1961"},
    {
        "title": "The Raft of the Medusa",
        "artist": "Théodore Géricault",
        "year": "1818–1819",
    },
    {"title": "BMW", "artist": "Ludwig Hohlwein", "year": "1929"},
    {"title": "Portrait of Dr. Gachet", "artist": "Vincent van Gogh", "year": "1890"},
    {"title": "The Kiss", "artist": "Gustav Klimt", "year": "1907–1908"},
    {
        "title": "Nude Descending a Staircase, No. 2",
        "artist": "Marcel Duchamp",
        "year": "1912",
    },
    {"title": "The Two Fridas", "artist": "Frida Kahlo", "year": "1939"},
    {
        "title": "Wanderer above the Sea of Fog",
        "artist": "Caspar David Friedrich",
        "year": "1818",
    },
    {
        "title": "I Want YOU for U.S. Army",
        "artist": "James Montgomery Flagg",
        "year": "1917",
    },
    {"title": "Girl with Balloon", "artist": "Banksy", "year": "2002"},
    {"title": "Normandie", "artist": "A. M. Cassandre", "year": "1935"},
    {"title": "Three Musicians", "artist": "Pablo Picasso", "year": "1921"},
    {"title": "The Potato Eaters", "artist": "Vincent van Gogh", "year": "1885"},
    {"title": "The Creation of Adam", "artist": "Michelangelo", "year": "c. 1508–1512"},
    {"title": "Luncheon on the Grass", "artist": "Édouard Manet", "year": "1863"},
    {"title": "Stop the Famine!", "artist": "Abram Games", "year": "1949"},
    {"title": "The Dance", "artist": "Henri Matisse", "year": "1909–1910"},
    {
        "title": "Bal du Moulin de la Galette",
        "artist": "Pierre-Auguste Renoir",
        "year": "1876",
    },
    {"title": "Broadway Boogie Woogie", "artist": "Piet Mondrian", "year": "1942–1943"},
    {"title": "Christina's World", "artist": "Andrew Wyeth", "year": "1948"},
    {
        "title": "Beat the Whites with the Red Wedge",
        "artist": "Gustav Klutsis",
        "year": "1919",
    },
    {
        "title": "Hurrah, die Butter ist Alle!",
        "artist": "John Heartfield",
        "year": "1935",
    },
    {
        "title": "Grateful Dead – Skull & Roses",
        "artist": "Stanley Mouse & Alton Kelley",
        "year": "1966",
    },
    {"title": "The Gleaners", "artist": "Jean-François Millet", "year": "1857"},
    {"title": "American Gothic", "artist": "Grant Wood", "year": "1930"},
    {"title": "Nighthawks", "artist": "Edward Hopper", "year": "1942"},
    {"title": "The Old Guitarist", "artist": "Pablo Picasso", "year": "1903–1904"},
    {"title": "Persil", "artist": "Ludwig Hohlwein", "year": "1908"},
    {"title": "Blade Runner", "artist": "John Alvin", "year": "1982"},
    {"title": "The Gross Clinic", "artist": "Thomas Eakins", "year": "1875"},
    {"title": "Campbell's Soup Cans", "artist": "Andy Warhol", "year": "1962"},
    {"title": "Swissair – Switzerland", "artist": "Herbert Matter", "year": "1937"},
    {"title": "Folies Bergère", "artist": "Jules Chéret", "year": "1893"},
    {"title": "The Hay Wain", "artist": "John Constable", "year": "1821"},
    {"title": "No. 5, 1948", "artist": "Jackson Pollock", "year": "1948"},
    {"title": "The School of Athens", "artist": "Raphael", "year": "1511"},
]

target_date = datetime(2025, 4, 29)

today = datetime.today()


difference = (target_date - today).days
index = difference % len(artworks)

prompt = f"""
Generate an image inspired by the artwork {artworks[index]["title"]} by {artworks[index]['artist']} with a cartoon polar substituted for the people, or if there are no people
in the original artwork, add that cartoon polar bear somewhere in the image. The polar bear cartoon character should be inspired by ice bear from the we bare bears cartoon. Make sure the polar bear blends in to the spirit and technique of the image, substituting it for persons, and if there are no persons, perhaps adding in an ice bear, making sure it is in the style of the original image. Even if the image is abstract art, make ice bear blend in.

"""

media_dir = "./media"
if not os.path.exists(media_dir):
    os.makedirs(media_dir)

image_filename = (
    f"{artworks[index]['title'].replace(' ', '_')}-{today.strftime('%Y-%m-%d')}.png"
)
image_filepath = os.path.join(media_dir, image_filename)

if not os.path.exists(image_filepath):
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"), organization=os.getenv("OPENAI_ORG_ID")
    )
    result = client.images.generate(model="gpt-image-1", prompt=prompt)
    image_base64 = result.data[0].b64_json
    image_bytes = base64.b64decode(image_base64)

    with open(image_filepath, "wb") as f:
        f.write(image_bytes)

    print(
        f"Image generated for {artworks[index]['title']} by {artworks[index]['artist']}"
    )

data = {
    "from": f"Icebear Courier <{os.getenv('MAILGUN_FROM_EMAIL')}>",
    "to": f"{os.getenv('MAILGUN_TO_NAME')} <{os.getenv('MAILGUN_TO_EMAIL')}>",
    "subject": f"Icebear Artwork for today {today.strftime('%Y-%m-%d')}",
    "text": f"Todays artwork is {artworks[index]['title']} by {artworks[index]['artist']}. Have a great bear day!",
}

if os.getenv("MAILGUN_CC_EMAILS"):
    cc_emails = os.getenv("MAILGUN_CC_EMAILS").split(",")
    data["cc"] = ", ".join(f"<{email.strip()}>" for email in cc_emails)

requests.post(
    f"{os.getenv('MAILGUN_DOMAIN')}",
    auth=("api", os.environ["MAILGUN_API_KEY"]),
    files=[("inline", open(image_filepath, "rb"))],
    data=data,
)
print(f"Email sent to {os.getenv('MAILGUN_TO_EMAIL')} with image {image_filename}")
