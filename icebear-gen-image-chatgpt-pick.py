#!/usr/bin/env python3
"""IceBear generator where ChatGPT chooses the artwork instead of artworks.json.

Everything after the pick (reference-image search, the bear edit, GIF, blurb,
email) is the code in icebear-gen-image-assisted.py; this script only replaces
how the artwork is chosen:

  * ChatGPT is asked for a real, well-documented artwork of its choice. Most of
    the time it is nudged toward one of ART_CATEGORIES (distilled from the
    kinds of things in artworks.json); some of the time it is told to surprise
    us with something outside those.
  * Every artwork that gets an image is appended to GENERATED_LOG. If ChatGPT
    suggests something already in the log (or in failed_artworks.json, or
    already tried this run), it is told so and asked for another choice.

Extra flags (all other flags are passed through to the original script):
  --pick-only            ask ChatGPT for one pick, print it and exit (no log, no image)
  --category TEXT        force the suggested area, e.g. --category "album covers"
  --surprise             skip the category list and ask for a surprise
"""

from __future__ import annotations

import argparse
import difflib
import importlib.util
import json
import os
import random
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
BASE_SCRIPT = HERE / "icebear-gen-image-assisted.py"

GENERATED_LOG = Path(os.getenv("ICEBEAR_GENERATED_LOG", "./generated_artworks.jsonl"))
PICKER_MODEL = os.getenv("ICEBEAR_PICKER_MODEL")  # default: the script's --text-model
PICKER_REASONING_EFFORT = os.getenv("ICEBEAR_PICKER_REASONING_EFFORT", "low")
# Share of picks where ChatGPT ignores the category list and surprises us.
SURPRISE_RATE = float(os.getenv("ICEBEAR_SURPRISE_RATE", "0.25"))
# How many times to ask again when ChatGPT keeps suggesting something already done.
MAX_PICK_ROUNDS = int(os.getenv("ICEBEAR_MAX_PICK_ROUNDS", "8"))
# How many recent picks to show ChatGPT so it can steer away from them up front.
RECENT_IN_PROMPT = int(os.getenv("ICEBEAR_RECENT_IN_PROMPT", "150"))


# Distilled from artworks.json. These are suggestions for ChatGPT, not a closed
# list: the examples show the flavour, and ChatGPT is asked to go beyond them.
ART_CATEGORIES: list[tuple[str, str]] = [
    ("Vintage travel posters",
     "railway, airline, ocean-liner and tourism posters: A.M. Cassandre, Roger Broders, "
     "LNER and Southern Railway, Pan Am clippers, Canadian Pacific, WPA national parks, Swiss ski posters"),
    ("Wartime propaganda and home-front posters",
     "WWI and WWII recruiting, rationing, 'careless talk' and war-bond posters from the US, UK, "
     "USSR, France and elsewhere; Fougasse, Abram Games, Office of War Information, Soviet constructivists"),
    ("Art Nouveau and Belle Époque posters",
     "Mucha, Toulouse-Lautrec, Jules Chéret, Cappiello, Steinlen, Grasset, cabaret, absinthe and bicycle posters"),
    ("Children's book illustration",
     "Tenniel, Arthur Rackham, Maurice Sendak, Quentin Blake, Beatrix Potter, Tomi Ungerer, "
     "Shel Silverstein, Shaun Tan, Golden Books"),
    ("Classic literary illustration",
     "Gustave Doré, Cruikshank and Phiz for Dickens, Sidney Paget's Sherlock Holmes, N.C. Wyeth, "
     "Grandville, Riou's Jules Verne plates, Harry Clarke"),
    ("Album covers",
     "iconic LP sleeves in rock, jazz, blues and pop: Blue Note, Hipgnosis, Sgt. Pepper, punk and new wave"),
    ("Movie posters and title design",
     "Saul Bass, classic Hollywood one-sheets, Italian westerns, Polish film posters, sci-fi and B-movie posters"),
    ("Old-master prints, etchings and engravings",
     "Dürer, Rembrandt, Piranesi's Carceri, Goya's Caprichos, Hogarth, Callot, Meryon, Whistler's Thames set"),
    ("M.C. Escher and mathematical or impossible art",
     "Escher's tessellations, impossible staircases and early Italian landscapes; op art and optical puzzles"),
    ("Patents, inventions and technical drawings",
     "patent drawings (Tesla, Edison, Benz, Wright brothers), Leonardo's machines, Rees's Cyclopaedia plates"),
    ("Cutaways, manuals and how-to diagrams",
     "ocean-liner and bus cutaways, the VW 'Idiot Manual', Popular Mechanics DIY diagrams, assembly guides"),
    ("Impressionism and Post-Impressionism",
     "Monet, Renoir, Degas, Caillebotte, Cassatt, Van Gogh, Cézanne, Seurat, Gauguin"),
    ("Landscape and marine painting",
     "Hudson River School, Bierstadt, Moran, Turner, Constable, Dutch Golden Age canals and harbours, "
     "Canaletto, Caspar David Friedrich, even Bob Ross"),
    ("Renaissance and Baroque masterpieces",
     "Leonardo, Botticelli, Bruegel, Bosch, Van Eyck, Holbein, Vermeer, Caravaggio, Artemisia Gentileschi"),
    ("Japanese woodblock prints and East Asian art",
     "Hokusai, Hiroshige, Kuniyoshi, shin-hanga such as Hasui, Sesshū ink landscapes, Chinese scroll painting"),
    ("Pop art",
     "Warhol, Lichtenstein, Richard Hamilton, Paolozzi, Rosenquist, Peter Blake, Wayne Thiebaud"),
    ("Surrealism and Dada",
     "Dalí, Magritte, Max Ernst, de Chirico, Leonora Carrington, Hannah Höch, Duchamp"),
    ("Modernism and abstraction",
     "Mondrian, Malevich, Kandinsky, Klee, Léger, Cubist Picasso, Italian Futurists, Bauhaus"),
    ("American scene and realism",
     "Hopper, Norman Rockwell, Grant Wood, Andrew Wyeth, Sheeler and the Precisionists, George Bellows"),
    ("Cartoons, caricature and New Yorker art",
     "Saul Steinberg, Edward Gorey, Ralph Steadman, Ronald Searle, Charles Addams, Gillray, Gerald Scarfe, "
     "New Yorker covers"),
    ("Comics and manga original art",
     "Little Nemo, Krazy Kat, Calvin and Hobbes, Steve Ditko, Hergé, Maus, Moebius, Junji Ito, Osamu Tezuka"),
    ("Magazine covers and vintage advertising",
     "Saturday Evening Post, TIME and Life covers, Leyendecker's Arrow Collar Man, Sundblom's Coca-Cola, "
     "Doyle Dane Bernbach's Think Small, mid-century print ads"),
    ("Mid-century graphic design",
     "Paul Rand, Milton Glaser, Herbert Matter, Josef Müller-Brockmann, Swiss style, corporate identity posters"),
    ("Psychedelic and rock concert posters",
     "Fillmore and Avalon Ballroom posters, Peter Max, Wes Wilson, Victor Moscoso, Yellow Submarine"),
    ("Retro-futurism and pulp sci-fi",
     "Frank R. Paul, Chesley Bonestell, Arthur Radebaugh, Hugh Ferriss, pulp magazine covers, World's Fair visions"),
    ("Architecture and design icons",
     "Eiffel Tower, Crystal Palace, Bauhaus, Mies, Le Corbusier, Brooklyn Bridge, Eames and Dieter Rams objects"),
    ("Sculpture and installation",
     "Rodin, Michelangelo, Giacometti, Louise Bourgeois, Calder, Kusama, classical and ancient sculpture"),
    ("Iconic photography",
     "Earthrise, Muybridge's horse, Capa, Cartier-Bresson, Kertész, Ansel Adams, Dorothea Lange, Lee Miller"),
    ("Industry, labour and the machine age",
     "Coalbrookdale by Night, Rivera's Detroit Industry murals, Menzel's railway, Victorian factory engravings"),
    ("Ancient, medieval and manuscript art",
     "Egyptian tomb painting, the Bayeux Tapestry, illuminated manuscripts, the Voynich Manuscript, bestiaries"),
    ("Art from around the world",
     "Frida Kahlo, Amrita Sher-Gil, Raja Ravi Varma, Ben Enwonwu, Indigenous artists such as Norval Morrisseau, "
     "Mughal miniatures, Persian painting, African and Latin American modernists"),
    ("Contemporary and conceptual art",
     "Hockney, Barbara Kruger, Banksy, Kehinde Wiley, Yayoi Kusama, Kara Walker, Ai Weiwei"),
    ("Folk art and commercial ephemera",
     "orange-crate labels, Lotería cards, matchbox and cigar labels, tin signs, seed packets, playing cards"),
    ("Scientific and natural-history illustration",
     "Dürer's Rhinoceros, Audubon, Ernst Haeckel, Maria Sibylla Merian, anatomical plates, Hubble images, "
     "old maps and celestial charts"),
]

# Extra random angles, so repeated picks in one category don't all land on the
# single most famous example.
NUDGES = [
    "Prefer a work from before 1700.",
    "Prefer a work from 1700-1900.",
    "Prefer a work from 1900-1945.",
    "Prefer a work from 1945-1980.",
    "Prefer a work from after 1980.",
    "Prefer a work from outside Western Europe and the United States.",
    "Prefer a lesser-known work by a well-known artist.",
    "Prefer a well-known work by a lesser-known artist.",
    "Prefer something with a busy, detailed scene full of people or animals.",
    "Prefer something with a strong, simple graphic composition.",
    "Prefer something funny, odd or whimsical.",
    "Prefer something set outdoors in winter, at sea, or in the mountains.",
    "Prefer something with machines, vehicles or architecture in it.",
    "",  # no nudge
    "",
]

# Shown three at a time in "surprise me" requests, so the examples themselves
# don't become the answer every time.
SURPRISE_HINTS = [
    "tapestries", "stained glass", "antique maps", "tarot cards", "board games",
    "textile and wallpaper design", "puppetry", "shop signs and lettering", "postage stamps",
    "video game box art", "Soviet space-age posters", "Byzantine mosaics", "Mughal miniatures",
    "Aboriginal Australian painting", "Mexican muralism", "Inuit prints", "Persian carpets",
    "Ethiopian icons", "Haitian painting", "Polish circus posters", "Czech animation stills",
    "seed catalogue covers", "World's Fair pavilions", "medieval misericords",
    "Victorian trade cards", "theatre set designs", "fashion plates", "naive painting",
    "embroidery samplers", "Chinese New Year prints", "Indian truck art", "Tibetan thangkas",
    "Art Deco radio and car design", "early animation cels", "zoetrope strips",
    "lantern slides", "Edo-period kite and fan painting", "Mayan murals", "cave paintings",
]


# ---------------------------------------------------------------------------
# Load the original script as a module so we can reuse it unchanged.

def _load_base_module():
    spec = importlib.util.spec_from_file_location("icebear_base", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load {BASE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["icebear_base"] = module
    spec.loader.exec_module(module)
    return module


base = _load_base_module()
Artwork = base.Artwork


# ---------------------------------------------------------------------------
# Duplicate detection.

_LEADING_ARTICLE = re.compile(r"^(the|a|an|le|la|les|il|el|der|die|das)\s+")


def _norm(text: str | None) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    text = re.sub(r"\(.*?\)", " ", text)  # drop "(engraved reproduction)" etc.
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return _LEADING_ARTICLE.sub("", text)


def _artist_key(artist: str | None) -> str:
    """Surname-ish key: 'M. C. Escher' and 'M.C. Escher' -> 'escher'."""
    words = _norm(artist).split()
    return words[-1] if words else ""


def _same_artwork(a_title: str, a_artist: str, b_title: str, b_artist: str) -> bool:
    ta, tb = _norm(a_title), _norm(b_title)
    if not ta or not tb:
        return False
    aa, ab = _artist_key(a_artist), _artist_key(b_artist)
    if aa and ab and aa != ab:
        # Different artists can share a title ("The Kiss"); allow unless the
        # artist names overlap at all ("Hokusai" vs "Katsushika Hokusai").
        if aa not in _norm(b_artist).split() and ab not in _norm(a_artist).split():
            return False
    return ta == tb or difflib.SequenceMatcher(None, ta, tb).ratio() >= 0.88


def read_generated_log() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    try:
        lines = GENERATED_LOG.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return entries
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            print(f"Ignoring bad line in {GENERATED_LOG}: {line[:80]}")
            continue
        if isinstance(item, dict) and item.get("title"):
            entries.append(item)
    return entries


def append_generated_log(artwork: Any, category: str | None, image_path: Path | None) -> None:
    entry = {
        "title": artwork.title,
        "artist": artwork.artist,
        "year": artwork.year,
        "citation": artwork.citation,
        "category": category,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "image": str(image_path) if image_path else None,
    }
    with GENERATED_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"Logged to {GENERATED_LOG}: {artwork.title} by {artwork.artist}")


def find_duplicate(
    title: str, artist: str, done: list[tuple[str, str]]
) -> tuple[str, str] | None:
    for d_title, d_artist in done:
        if _same_artwork(title, artist, d_title, d_artist):
            return d_title, d_artist
    return None


# ---------------------------------------------------------------------------
# Asking ChatGPT.

def _category_menu() -> str:
    return "\n".join(f"- {name}: {examples}" for name, examples in ART_CATEGORIES)


def choose_direction(forced_category: str | None, force_surprise: bool) -> tuple[str | None, str]:
    """Return (category name or None for surprise, instruction text)."""
    if forced_category:
        return forced_category, (
            f"Pick something in this area: {forced_category}. "
            "Interpret it loosely if a neighbouring idea makes a better picture."
        )
    if force_surprise or random.random() < SURPRISE_RATE:
        hints = ", ".join(random.sample(SURPRISE_HINTS, 3))
        return None, (
            "Surprise me. Pick something that does NOT fit neatly into any of the areas listed "
            "below: another tradition, medium, era or corner of visual culture entirely. "
            f"Just to show the range (don't feel bound to these): {hints}. "
            "It still has to be a real, documented work."
        )
    name, examples = random.choice(ART_CATEGORIES)
    nudge = random.choice(NUDGES)
    return name, (
        f"This time, pick from this area: {name} (for flavour: {examples}). "
        "Don't just take the examples, and don't take the single most obvious piece in the area "
        f"unless you have a reason. {nudge}"
    ).strip()


PICK_INSTRUCTIONS = """\
You choose the artwork for a daily image series. Each day a well-known polar \
bear character (Ice Bear) is painted into a famous or interesting existing \
artwork, in that artwork's own style. The picture works best when the artwork \
has a scene or composition a bear can be placed into.

Rules:
- It must be a real, existing, well-documented work (painting, print, poster, \
illustration, cover, photograph, design, sculpture, ...). Never invent one.
- A good reference image of it must be easy to find online, so prefer works in \
museum collections, Wikipedia/Wikimedia, or well-known archives.
- Name one specific work, not a series or a whole book ("The Wild Rumpus \
spread from Where the Wild Things Are", not "Sendak's illustrations").
- Use the commonly known title and the artist's full commonly used name. For \
anonymous works use the studio, agency or "Unknown".
- Do not pick anything in the "already done" list. Vary artists from the \
recent picks.

The areas this series usually draws from (suggestions, not limits):
{categories}

Reply with ONLY a JSON object:
{{"title": "...", "artist": "...", "year": "...", \
"citation": "short search hint for finding the image: museum/collection or a descriptive phrase", \
"category": "the area it belongs to, in a few words"}}"""


def ask_chatgpt_for_artwork(
    client: Any,
    model: str,
    direction: str,
    recent: list[tuple[str, str]],
    rejected: list[tuple[str, str]],
) -> dict[str, Any]:
    lines = [direction, ""]
    if recent:
        lines.append("Already done (do not pick these):")
        lines.extend(f"- {t} — {a}" for t, a in recent)
        lines.append("")
    if rejected:
        lines.append("You already suggested these in this conversation and they were rejected "
                     "as duplicates or unusable; pick something different:")
        lines.extend(f"- {t} — {a}" for t, a in rejected)
        lines.append("")
    lines.append("Today's date: " + datetime.now().strftime("%Y-%m-%d")
                 + f". Random seed for variety: {random.randint(1, 10**6)}.")

    response = client.responses.create(
        model=model,
        reasoning={"effort": PICKER_REASONING_EFFORT},
        instructions=PICK_INSTRUCTIONS.format(categories=_category_menu()),
        input="\n".join(lines),
    )
    payload = base._extract_json_object(response.output_text or "")
    if not payload.get("title") or not payload.get("artist"):
        raise ValueError(f"Picker reply missing title/artist: {payload}")
    return payload


# ---------------------------------------------------------------------------
# Hooks into the original script.

_opts: argparse.Namespace
_client = None
_current_pick: dict[str, Any] = {}


def _get_client():
    global _client
    if _client is None:
        _client = base.create_openai_client()
    return _client


def chatgpt_pick_artwork(args: argparse.Namespace, artworks: list, exclude=None):
    """Drop-in replacement for base.pick_artwork."""
    if args.artwork:
        artwork = base.pick_artwork(args, artworks, exclude)
        _current_pick.update(artwork=artwork, category=None)
        return artwork

    log_entries = read_generated_log()
    done = [(e["title"], e.get("artist") or "") for e in log_entries]
    done += list(exclude or set())  # failed_artworks.json + already tried this run
    recent = [(e["title"], e.get("artist") or "") for e in log_entries[-RECENT_IN_PROMPT:]]

    model = PICKER_MODEL or args.text_model
    category, direction = choose_direction(_opts.category, _opts.surprise)
    print(f"Asking {model} for an artwork ({category or 'surprise'})")

    rejected: list[tuple[str, str]] = []
    for round_no in range(1, MAX_PICK_ROUNDS + 1):
        try:
            payload = ask_chatgpt_for_artwork(_get_client(), model, direction, recent, rejected)
        except Exception as e:  # bad JSON, transient API error: just ask again
            print(f"Pick round {round_no}: picker error: {e}")
            continue
        artwork = Artwork.from_dict(payload)
        dup = find_duplicate(artwork.title, artwork.artist, done + rejected)
        if dup:
            print(f"Pick round {round_no}: '{artwork.title}' by {artwork.artist} "
                  f"already done (matches '{dup[0]}' by {dup[1]}); asking again")
            rejected.append((artwork.title, artwork.artist))
            continue
        picked_category = payload.get("category") or category
        print(f"ChatGPT picked: {artwork.title} by {artwork.artist} ({artwork.year}) "
              f"[{picked_category}]")
        _current_pick.update(artwork=artwork, category=picked_category)
        return artwork

    raise RuntimeError(f"ChatGPT gave no new artwork after {MAX_PICK_ROUNDS} rounds")


_original_try_edit_image = base.try_edit_image


def try_edit_image_and_log(*args, **kwargs):
    """Log the artwork once its image exists, so a failed run can pick it again."""
    path = _original_try_edit_image(*args, **kwargs)
    artwork = _current_pick.get("artwork")
    if artwork is not None:
        append_generated_log(artwork, _current_pick.get("category"), path)
    return path


def _parse_own_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--pick-only", action="store_true")
    parser.add_argument("--category", type=str)
    parser.add_argument("--surprise", action="store_true")
    opts, rest = parser.parse_known_args()
    sys.argv = [sys.argv[0], *rest]  # the original parse_args sees only its own flags
    return opts


def main() -> int:
    global _opts
    _opts = _parse_own_args()

    base.load_artworks = lambda: []  # artworks.json is not used
    base.pick_artwork = chatgpt_pick_artwork
    base.try_edit_image = try_edit_image_and_log

    if _opts.pick_only:
        args = base.parse_args()
        base.load_environment(args.env)
        artwork = chatgpt_pick_artwork(args, [], exclude=base.load_failed_artworks())
        print(json.dumps({
            "title": artwork.title, "artist": artwork.artist, "year": artwork.year,
            "citation": artwork.citation, "category": _current_pick.get("category"),
        }, indent=2, ensure_ascii=False))
        return 0

    return base.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        raise SystemExit(1)
