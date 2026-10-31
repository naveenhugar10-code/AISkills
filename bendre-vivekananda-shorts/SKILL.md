---
name: bendre-vivekananda-shorts
description: Finds trending, timely concepts around Swami Vivekananda, Da Ra Bendre (D.R. Bendre, the Kannada poet "Ambikatanayadatta") and broader Indian culture, history and philosophy, then runs an end-to-end agent pipeline that writes, voices, captions and renders faceless vertical short videos (9:16, 15-60s) ready for Instagram Reels and YouTube Shorts, with titles, descriptions, hashtags and optional upload. Use this skill whenever the user wants content ideas, trending topics, scripts, reels, shorts or faceless videos about Vivekananda, Bendre, Kannada poetry/literature, Indian heritage, Indian festivals, national days, Indian spirituality or "India trending" topics, or wants to automate a faceless Insta/YouTube channel on these themes, even if they don't say "video" or "skill" explicitly (e.g. "what should I post for National Youth Day", "make a reel on Naku Tanti", "daily shorts for my Kannada channel").
---

# Bendre · Vivekananda · India — Faceless Shorts Agent

This skill turns "what's trending about Vivekananda / Bendre / India today?" into finished, upload-ready vertical videos. It works as a pipeline of five stages. Run all of them by default; the user may ask for only one (e.g. just ideas, or just a script) — then stop there.

```
1 DISCOVER  →  2 PICK  →  3 SCRIPT  →  4 RENDER  →  5 PUBLISH
trend signals  rank &     hook-led     TTS + visuals  metadata +
+ calendar     choose     scene spec   + captions     (optional) upload
```

All scripts live in `scripts/` next to this file. Install dependencies once:

```bash
pip install edge-tts requests pillow           # required
pip install pytrends google-api-python-client google-auth-oauthlib   # optional: Google Trends, YouTube upload
# ffmpeg (with libass) must be on PATH.
# Kannada/Hindi text needs Noto fonts: `apt-get install fonts-noto-core` (Linux) or install
# "Noto Sans Kannada"/"Noto Sans Devanagari" from fonts.google.com. Without them Indic text renders
# as broken glyphs - the renderer warns if they're missing.
```

Work in a dated output folder, e.g. `shorts/2026-10-31/`, so each day's run is self-contained.

---

## 1. Discover trending concepts

Run the trend collector. It merges several free signals and never fails just because one source is unavailable — missing sources are listed under `"errors"` in the output.

```bash
python scripts/fetch_trends.py --out shorts/<date>/trends.json [--days-ahead 21]
```

What it gathers (and why each matters):

| Signal | Source | Needs key? | Why |
|---|---|---|---|
| Upcoming anniversaries & national days | built-in calendar (`references/calendar.md`) | no | Date-anchored posts are the most reliable traffic for heritage channels (Jan 12 National Youth Day, Sep 11 Chicago address, Jan 31 Bendre Jayanti...) |
| News mentions | Google News RSS (en-IN and kn-IN) | no | Catches news hooks — a statue, a film, a political speech quoting Vivekananda |
| Wikipedia pageview spikes | Wikimedia REST API | no | Shows curiosity spikes across en/kn/hi Wikipedia |
| Search interest | Google Trends via `pytrends` | no (optional lib) | Rising related queries in India |
| Popular videos | YouTube Data API | `YOUTUBE_API_KEY` | What formats/topics are already working |

If the network blocks every live source, the calendar and the evergreen bank in `references/topics.md` still give a usable list — say so to the user rather than pretending the list is "trending".

If you have a web-search tool, also run 2-4 quick searches (e.g. "Vivekananda news this week", "ಬೇಂದ್ರೆ" news, "India trending today") and add anything relevant. Live search beats any stale list.

## 2. Pick the concepts

Read `trends.json` and `references/topics.md`, then rank candidates. Score each on:

- **Timeliness** (0-3): anniversary within ~7 days, active news hook, or pageview spike.
- **Theme fit** (0-3): directly about Vivekananda/Bendre = 3; Indian philosophy, Kannada literature, national icons = 2; generic India = 1.
- **Hook strength** (0-2): is there a surprising fact, a strong quote, or a question people actually ask?
- **Safety** (0-2): 2 = non-partisan, verifiable; 0 = needs a contested political/communal claim. Skip anything scoring 0 here — these channels get mass-reported and demonetised over communal framing, and both figures stood for universality, so divisive takes also misrepresent them.

Present the top 5-10 as a table (concept, angle/hook, why now, score) and pick the top N to produce (default 3, or whatever the user asked). When running unattended, just proceed with the top picks.

## 3. Write the script and scene spec

Read `references/script_guide.md` before writing — it has the hook formulas, the 45-second structure, quote-accuracy rules and copyright rules. The short version:

- **Hook in the first 2 seconds** (a question, a surprising fact, or a strong line). Retention in the first 3s decides reach on both platforms.
- 110-150 spoken words for ~45s. One idea per video.
- **Quotes must be real.** Vivekananda is the most misquoted figure in Indian social media. Only use quotes you can trace to the *Complete Works* (or a named letter/lecture); `references/topics.md` lists verified ones. If unsure, paraphrase and say "Vivekananda taught that…".
- **Bendre's poems are still under copyright in India** (he died 1981; copyright runs to 2041). Quote at most a line or two for commentary, credit the poem and collection, and explain rather than recite. Never put a full poem on screen or in the voiceover. Vivekananda's works (d. 1902) are public domain.
- Language: match the user's channel. Default English narration with Kannada/Hindi phrases where they add flavour; Kannada (`kn-IN`) or Hindi (`hi-IN`) narration on request.

Write a scene spec JSON per video — this is the contract with the renderer:

```json
{
  "id": "vivekananda-chicago-1893",
  "language": "en-IN",
  "voice": "en-IN-PrabhatNeural",
  "rate": "+0%",
  "title_card": "The 4 words that stunned Chicago",
  "scenes": [
    {"narration": "In 1893, a young monk said four words, and seven thousand people stood up.",
     "visual": {"type": "image", "query": "Swami Vivekananda Chicago 1893", "path": null},
     "on_screen": "Chicago · 11 Sept 1893"},
    {"narration": "...", "visual": {"type": "video", "query": "old library books dust light"}, "on_screen": null}
  ],
  "cta": "Follow for one idea from India's thinkers every day.",
  "music": null
}
```

`visual.type` is `image`, `video` or `color`. Give a `path` if you already have the asset; otherwise a stock-search `query`. Prefer abstract/atmospheric B-roll (lamps, rivers, mountains, books, temples, Dharwad landscapes) over images of people; for Vivekananda use public-domain historical photographs (Wikimedia Commons), never AI-generated likenesses — fake "photos" of real historical figures get flagged as misleading and erode trust.

## 4. Render the video

```bash
python scripts/make_video.py shorts/<date>/<id>/spec.json --out shorts/<date>/<id>/
```

The renderer:
1. Synthesises narration per scene with `edge-tts` (free; voices for en-IN, kn-IN, hi-IN — see `references/platforms.md`) and captures word timings.
2. Resolves visuals: local `path` → Pexels (`PEXELS_API_KEY`) → Pixabay (`PIXABAY_API_KEY`) → Wikimedia Commons → a tasteful gradient background. It logs which source and licence each asset came from into `credits.txt`.
3. Builds word-synced, large, centred captions (burned in — most viewers watch muted).
4. Assembles 1080×1920 @30fps H.264/AAC with a slow Ken Burns zoom on stills, optional background music ducked under the voice.

Outputs per video: `video.mp4`, `captions.srt`, `voiceover.mp3`, `credits.txt`, `render_log.json`.

After rendering, sanity-check: `ffprobe` duration is 15-60s (Shorts max is 3 min, but 30-50s performs best), resolution is 1080×1920, and open one frame (`ffmpeg -ss 3 -i video.mp4 -frames:v 1 frame.png`) to confirm captions are readable and not covering the centre of the subject. Indic text should show as proper conjuncts, not dotted circles — if it doesn't, the font is missing. If TTS was unavailable (offline), the renderer produces a silent preview (`tts` in `render_log.json` is not `edge-tts`) and says so — tell the user rather than shipping it. `--no-tts` deliberately renders a quick silent preview for layout checks.

Visual sources depend on keys: with no `PEXELS_API_KEY`/`PIXABAY_API_KEY`, only Wikimedia Commons is searched, and abstract queries ("lamp flame dark") rarely match there, so videos fall back to gradients. Suggest the user get a free Pexels key — it's the biggest quality jump.

## 5. Publish metadata and (optionally) upload

For each video write `metadata.json`:

```json
{
  "youtube": {"title": "≤ 70 chars, hook first, include #Shorts", "description": "2-4 lines + source/credits + 3-5 hashtags", "tags": ["Vivekananda", "..."], "categoryId": "27", "privacyStatus": "private", "containsSyntheticMedia": true},
  "instagram": {"caption": "hook line\n\n2-3 lines of context\n\nCTA\n\n#hashtags (8-15, mix of broad and niche)", "share_to_feed": true},
  "pinned_comment": "a question that invites replies",
  "best_post_time_ist": "19:00"
}
```

Hashtag and timing guidance is in `references/platforms.md`.

**Uploading is outward-facing — confirm with the user before the first upload in a session**, and default to `private` (YouTube) so they can review. Then:

```bash
python scripts/upload_youtube.py shorts/<date>/<id>/video.mp4 shorts/<date>/<id>/metadata.json   # OAuth client_secret.json required
python scripts/upload_instagram.py shorts/<date>/<id>/video.mp4 shorts/<date>/<id>/metadata.json --video-url <public https URL>
```

Instagram's Graph API needs a Business/Creator account linked to a Facebook Page, `IG_USER_ID` + `IG_ACCESS_TOKEN`, and the video at a public HTTPS URL. If credentials aren't set, stop at "ready to upload" and give the user the folder — that's a fine outcome.

Disclose AI voice/visuals: set YouTube's "altered or synthetic content" flag when visuals are AI-generated or realistic, and add "Voice: AI narration" in descriptions. It's required by platform policy for realistic synthetic media and protects the channel.

---

## Final report to the user

End with a short summary:

```
## Today's shorts (<date>)
| # | Concept | Why now | Length | File |
|---|---------|---------|--------|------|
| 1 | ... | Bendre Jayanti in 3 days | 42s | shorts/<date>/<id>/video.mp4 |

Sources used: calendar ✓, Google News ✓, Wikipedia ✗ (blocked), ...
Next: review videos → say "upload 1 and 3" to publish (private on YouTube).
```

## Running it as a daily agent

If the user wants this automated, offer to schedule a daily run (e.g. 06:30 IST) that executes stages 1-4 and leaves videos for review, with upload only after their approval — or fully automatic upload as `private` if they explicitly ask for it. Keep a `shorts/posted.json` log of concept ids already published and skip repeats within 60 days.
