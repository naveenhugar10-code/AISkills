# AISkills

Claude skills.

## bendre-vivekananda-shorts
Finds trending concepts around Swami Vivekananda, Da Ra Bendre and Indian culture, then writes, voices,
captions and renders faceless 9:16 shorts for Instagram Reels and YouTube Shorts (with optional upload).

```
1 DISCOVER → 2 PICK → 3 SCRIPT → 4 RENDER → 5 PUBLISH
```

- `SKILL.md` – the agent workflow Claude follows
- `scripts/fetch_trends.py` – calendar + Google News + Wikipedia pageviews + Google Trends + YouTube signals
- `scripts/make_video.py` – scene spec → 1080×1920 MP4 (edge-tts voice, stock/archival visuals, word-synced captions incl. Kannada)
- `scripts/upload_youtube.py`, `scripts/upload_instagram.py` – publishing (YouTube defaults to private)
- `references/` – topic bank & verified quotes, calendar, script guide, platform specs

### Setup
```bash
pip install -r bendre-vivekananda-shorts/requirements.txt
sudo apt-get install ffmpeg fonts-noto-core     # Noto fonts needed for Kannada/Hindi text
export PEXELS_API_KEY=...                       # free; strongly recommended for good B-roll
```
Install the skill by copying `bendre-vivekananda-shorts/` to `~/.claude/skills/` (Claude Code) or uploading the packaged `.skill` in Claude.ai, then ask e.g. *"make 3 shorts for National Youth Day"*.
