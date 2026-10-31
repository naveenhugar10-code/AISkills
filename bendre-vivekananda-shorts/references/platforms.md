# Platform specs, voices, metadata and upload

## Video specs (both platforms)
- 1080×1920 (9:16), 30 fps, H.264 High, AAC 44.1/48 kHz, ≤ 60s recommended (Shorts allow up to 3 min; Reels up to 3 min via app, 15 min via API for some accounts — keep it short anyway).
- Keep captions and text inside the safe zone: away from the top ~250px and bottom ~400px (UI overlays), and the right ~120px (buttons). The renderer centres captions at ~62% height for this reason.
- Loudness around -14 LUFS; voice clearly above music (renderer ducks music to ~12%).

## edge-tts voices (free, Microsoft neural)
List all: `edge-tts --list-voices | grep -E "IN-"`
| Language | Female | Male |
|---|---|---|
| English (India) `en-IN` | en-IN-NeerjaNeural | en-IN-PrabhatNeural |
| Kannada `kn-IN` | kn-IN-SapnaNeural | kn-IN-GaganNeural |
| Hindi `hi-IN` | hi-IN-SwaraNeural | hi-IN-MadhurNeural |
| Marathi `mr-IN` | mr-IN-AarohiNeural | mr-IN-ManoharNeural |
For a calm, reflective tone use `rate: "-5%"`. edge-tts is an unofficial endpoint; for a commercial channel consider Azure TTS, Google Cloud TTS or ElevenLabs (swap in `synthesize()` in `make_video.py`).

## Stock visuals
| Source | Env var | Licence notes |
|---|---|---|
| Pexels | `PEXELS_API_KEY` | free, no attribution required (credit appreciated) |
| Pixabay | `PIXABAY_API_KEY` | free, no attribution required |
| Wikimedia Commons | none | per-file licence; old photos of Vivekananda are public domain — the renderer records the licence in `credits.txt`; include attribution in the description when the licence requires it (CC BY / CC BY-SA) |
Avoid AI-generated likenesses of Vivekananda or Bendre; use real archival photos or abstract B-roll.

## Metadata
**YouTube Shorts**
- Title ≤ 70 chars, hook first. Add `#Shorts` at the end of title or description.
- Description: 2-4 lines of context, the quote source, credits, then 3-5 hashtags. YouTube ignores all hashtags if there are more than 60, and shows the first 3 above the title.
- categoryId: 27 (Education) or 22 (People & Blogs).
- Set `containsSyntheticMedia: true` if visuals are realistic AI-generated; AI voice narration over stock footage generally doesn't require it, but stating "AI narration" in the description is good practice.
- Default `privacyStatus: private` so the owner reviews before going public.

**Instagram Reels**
- Caption: hook line → 2-3 lines → CTA ("Save this for later", "Share with a friend who needs this") → 8-15 hashtags.
- Mix broad and niche: #vivekananda #swamivivekananda #nationalyouthday #indianphilosophy #spirituality #bendre #darabendre #kannada #kannadasahitya #kannadapoetry #karnataka #dharwad #india #incredibleindia #reels #explore (pick relevant ones).
- Cover: the title-card frame (renderer saves `cover.jpg`).

**Posting times (IST, starting points — check the account's own insights)**: 7-9 am, 12-2 pm, 7-10 pm. Date-anchored posts: publish the evening before or early morning on the day.

## Upload APIs
**YouTube Data API v3** (`scripts/upload_youtube.py`)
1. Google Cloud console → enable YouTube Data API v3 → OAuth client (Desktop) → download `client_secret.json`.
2. First run opens a browser for consent and stores `youtube_token.json`. On a headless server, run the first auth on a machine with a browser and copy the token.
3. Unverified API projects can only upload as private until the project passes Google's audit — another reason to default to private.
4. Quota: an upload costs ~1,600 units of the default 10,000/day → ~6 uploads/day.

**Instagram Graph API** (`scripts/upload_instagram.py`)
1. Instagram Business or Creator account linked to a Facebook Page; Meta app with `instagram_content_publish` permission.
2. Env: `IG_USER_ID`, `IG_ACCESS_TOKEN` (long-lived).
3. The video must be at a public HTTPS URL (S3, GCS, Cloudflare R2, a GitHub release asset…). The API pulls it; it can't take a local file upload.
4. Flow: POST `/{ig-user-id}/media` with `media_type=REELS`, `video_url`, `caption` → poll container `status_code` until `FINISHED` → POST `/{ig-user-id}/media_publish`. Limit: 50 API-published posts per 24h.
