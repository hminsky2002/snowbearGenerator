# Release Notes

## 2026-11-05: Gemini as an image provider, cheaper runs, sharper GIFs

### New: draw the bear with Gemini

`ICEBEAR_IMAGE_PROVIDER=gemini` draws the bear (the daily still and the GIF
keyframes) with Google's Gemini 3.1 Flash Image instead of OpenAI. In a
three-artwork comparison it drew Ice Bear's face as well as OpenAI or better,
and it kept the original composition and text intact. It blended into painted
styles a little less than OpenAI. It costs about $0.07 per image against about
$0.20 for OpenAI at high quality, and takes about 10 s instead of 30 s. Text
calls (search, verification, blurb, GIF motion) still use OpenAI.

| Setting | Default | Meaning |
| --- | --- | --- |
| `ICEBEAR_IMAGE_PROVIDER` | `openai` | `openai` or `gemini`. |
| `GEMINI_IMAGE_MODEL` | `gemini-3.1-flash-image` | Gemini model used when the provider is `gemini`. |
| `GEMINI_API_KEY` | none | Gemini API key, billed through AI Studio. |
| `GEMINI_VERTEX_PROJECT` | none | If set, call Gemini through Vertex AI with Application Default Credentials (`gcloud auth application-default login`), billed to this Google Cloud project. It takes priority over `GEMINI_API_KEY`. |
| `GEMINI_VERTEX_LOCATION` | `global` | Vertex AI location. |
| `GCLOUD_PATH` | found automatically | Full path to `gcloud`, if cron can't find it on its PATH or in the usual install locations. |
| `GEMINI_ASPECT_RATIO` | `1:1` | Output aspect ratio. |

Vertex AI often answers HTTP 429 when its shared capacity is busy. Gemini calls
wait and retry (15 s, 45 s, 90 s) on 429 and temporary server errors.

### Cost changes

- Text calls use `gpt-5.4-mini` at low reasoning effort (`OPENAI_TEXT_MODEL`,
  `OPENAI_REASONING_EFFORT`). The image check sends its picture at low detail.
- Reference images are found with Google Image search first. OpenAI web search
  is only the fallback. Each source gets 3 rejected candidates before giving up
  (`OPENAI_IMAGE_VERIFY_TRIES`).
- Artworks with no findable reference image are listed in
  `failed_artworks.json` and skipped by later runs. Delete an entry to retry it.
- The OpenAI still stays at `high` quality and `high` input fidelity. `medium`
  was tried and lost the bear's nose and mouth detail.

### GIFs

- Full 1024px resolution (`ICEBEAR_GIF_WIDTH`, was 480), and keyframes at high
  quality.
- Every keyframe is edited from the still, not the previous keyframe, so the
  bear doesn't degrade from frame to frame.
- Only a padded, feathered box around what moved is pasted onto the still, so
  the rest of the scene stays sharp and identical. Motion is measured as the
  share of strongly changed pixels per 16px block
  (`ICEBEAR_GIF_MOTION_THRESHOLD`, default 60), which also catches thin objects
  such as a stick that moved.
- A keyframe that comes back without visible motion is generated once more.
- All frames share one 256-colour palette, so colours don't flicker.

## `91f582d` (2026-11-02): Animated Ice Bear GIFs

### New: `--gif` flag

Passing `--gif` makes the generator produce a short looping GIF of Ice Bear
doing his activity in the artwork, as well as the usual still. Both go in the
email. Without the flag nothing changes: runs produce the still only.

How the GIF is built:

1. The text model looks at the finished still and describes a short, loopable
   motion for the bear's activity (rowing, painting, sunbathing…).
2. The still is edited into a few keyframes. Each one changes only the bear's
   pose, one step on from the previous keyframe, and leaves the rest of the
   scene as it was.
3. The keyframes play forward and back (1-2-3-4-3-2) so the loop has no jump,
   scaled to 480px wide.

The still always comes first. If the GIF fails, the email goes out with the
still only.

### Options

| Setting | Default | Meaning |
| --- | --- | --- |
| `--gif-seconds` / `ICEBEAR_GIF_SECONDS` | `3` | Length of one pass of the loop, split evenly across the frames (at least 80 ms each). |
| `ICEBEAR_GIF_KEYFRAMES` | `4` | Distinct bear poses, counting the original still. `1` gives a GIF that doesn't move. |
| `ICEBEAR_GIF_WIDTH` | `480` | GIF width in pixels; height keeps the still's proportions. |

### Upgrade notes

- **Opt in.** Add `--gif` to `run_icebear_new.sh` (or whichever script cron
  runs) to get GIFs in the daily email.
- **Cost.** Each GIF adds one vision call plus `ICEBEAR_GIF_KEYFRAMES - 1`
  image edits at the configured quality: 3 extra edits by default.
- **Size.** The first real run (Hopper's *People in the Sun*) gave a 746 KB GIF.
- **No video model.** An early version animated the still with OpenAI's Sora
  video API. That API shut down on 2026-09-24, so it was removed before
  release.

## `c3e174f` – `1188b24` (2026-08-21 to 2026-09-21)

The theme of this stretch is **getting the right reference image**. Nearly every
code change tightens the pipeline that finds, checks, and falls back on source
images for an artwork; the rest grows the artwork catalog.

### Reference image accuracy

**Visual verification of the chosen image** (`1188b24`)
The generator now sends each downloaded candidate back to ChatGPT with the
artwork's title, artist, year, and citation, and asks whether the image really is
that work. Candidates that come back as a mismatch are deleted and the next
search result is tried. The prompt explicitly rejects the failure modes that were
slipping through: a different work by the same artist, a similarly titled work,
tributes, parodies, memes, fan art, merchandise photos, artist portraits, book
covers, gallery interiors, museum wall labels, heavy crops, and watermarked
thumbnails. A parse failure or API error counts as a mismatch, so a broken
verdict never passes the gate.

Verification gets a budget of 10 rejections per artwork
(`OPENAI_IMAGE_VERIFY_TRIES`, default 10), shared across the ChatGPT and Google
result sets. Exhausting it gives up on that artwork and moves to another rather
than failing the run. Setting the variable to `0` disables verification and
restores the previous accept-the-first-download behavior.

Images are downscaled to 1024px JPEG before being sent for verification, to keep
the check cheap.

**Google image search as a backup** (`a149709`)
When ChatGPT cannot find the artwork with high confidence, the generator now
falls back to the Google Custom Search image API instead of giving up. Requires
`GOOGLE_SEARCH_API_KEY` and `GOOGLE_SEARCH_ENGINE_ID`.

**Stronger search prompt** (`1d032a8`)
The image-search prompt now asks the model to actually look at the candidate
image and judge whether it is plausible given the title and what it knows about
the work, rather than trusting the surrounding page.

### Artwork catalog

Roughly 250 entries were added across five commits, broadening the mix well
beyond fine art:

- **Magazine ads** (`7458263`) — 79 entries
- **More artworks** (`35b35c9`) — 60 entries
- **Travel posters** (`2adc5b3`) — 40 entries
- **Classic illustrated books** (`91c98f1`) — 40 entries, replacing 30 earlier
  picture-book entries with better-known illustrated editions (Alice, Oz, The
  Little Prince, The Hobbit)
- **Children's books** (`5ba368b`) — 30 entries

**Fix extra bracket** (`7b8f725`) repaired a malformed `artworks.json`.

### Infrastructure

**Process-local media directories** (`c3e174f`)
Output now goes to `./media/pid-<pid>/` instead of a shared `./media/`, so
several generator processes can run at once without overwriting each other's
downloads and edits. The run prints the directory it is using.

### Upgrade notes

- Set `GOOGLE_SEARCH_API_KEY` and `GOOGLE_SEARCH_ENGINE_ID` to enable the search
  fallback; without them a low-confidence ChatGPT result ends the attempt.
- Each generated image now costs one or more extra vision calls. Tune with
  `OPENAI_IMAGE_VERIFY_TRIES`.
- Generated output moved from `./media/` to `./media/pid-<pid>/`; anything that
  globbed the old path needs updating.
