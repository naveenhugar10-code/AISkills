# Script guide for faceless shorts

## Why the structure matters
Both Reels and Shorts push a video based on whether viewers stay past the first 2-3 seconds and whether they watch to the end or rewatch. So: hook immediately, one idea, no throat-clearing ("Hi guys, today we'll talk about…"), end so the loop feels natural.

## The 45-second structure (110-150 spoken words)
| Time | Beat | Purpose |
|---|---|---|
| 0-3s | **Hook** | stop the scroll |
| 3-12s | **Context** | who/when/where in one or two lines |
| 12-35s | **Core** | the story, the idea, or the quote unpacked — 2-3 scenes |
| 35-42s | **Takeaway** | what it means for the viewer's life today |
| 42-45s | **CTA / loop** | follow prompt, or a line that leads back to the hook |

Each scene = one sentence or two of narration (≈ 3-7s) and one visual. 6-9 scenes per video.

## Hook formulas (pick one; vary across days)
- **Surprising number**: "He spoke for under five minutes. The applause lasted two." (verify any number you use)
- **Direct question**: "What are the four strings in Bendre's *Naaku Tanti*?"
- **Myth-bust**: "Vivekananda never said this quote. Here's what he actually said."
- **You-frame**: "If you're 20 and lost, read what Vivekananda told students."
- **Contrast**: "A monk with no money, in a city of millionaires."
- **Date hook**: "On this day in 1893…" (only if it actually is that date)

## Voice and tone
- Warm, respectful, curious. Not preachy, not hyper-hype.
- Short sentences — TTS sounds best on 8-15-word sentences.
- Write numbers and names how they should be spoken ("eighteen ninety-three", "Da Ra Bendre"). For Kannada words in English narration, add a phonetic hint in parentheses in the spec only if TTS mispronounces in testing.
- Kannada narration: use natural spoken Kannada, not textbook register — Bendre himself championed the spoken Dharwad idiom.

## Accuracy rules (why: a single wrong fact in the comments kills trust and gets the video "fact-checked" by viewers)
- Every date, number and quote must come from `topics.md`, `calendar.md`, or a source you checked in this session. If unsure, soften ("around", "he's often credited with") or cut it.
- Quotes on screen carry the speaker's name; the source goes in the description.
- Don't invent dialogue for historical figures ("Vivekananda turned and said…") unless it is a recorded quote.

## Copyright rules
- Vivekananda, Upanishads, Gita, Tagore (d. 1941), and pre-1965 deaths generally: public domain in India — quote freely.
- Bendre (d. 1981), Kuvempu (d. 1994), and any modern writer: one or two lines max, credited, inside commentary. No full poems, no singing their lyrics in TTS.
- Music: only royalty-free tracks the user supplies or that come from a licence-clear library; never film songs.

## On-screen text
- `title_card`: ≤ 6 words, shown 0-2s over the first visual.
- `on_screen`: optional per scene, ≤ 6 words — a date, a name, a Kannada title (ನಾಕುತಂತಿ). Captions already show the narration, so don't duplicate.

## Worked example (English, ~45s)
```json
{
  "id": "naaku-tanti-explained",
  "language": "en-IN",
  "voice": "en-IN-NeerjaNeural",
  "title_card": "Bendre's four strings",
  "scenes": [
    {"narration": "One book of poems won Kannada its second Jnanpith. It's called Naaku Tanti. Four strings.", "visual": {"type": "video", "query": "veena strings close up"}, "on_screen": "ನಾಕುತಂತಿ · 1973"},
    {"narration": "Its poet was Da Ra Bendre, from Dharwad, who wrote as Ambikatanayadatta.", "visual": {"type": "video", "query": "old town street india morning"}, "on_screen": "Da Ra Bendre"},
    {"narration": "So what are the four strings? Readers have argued for fifty years.", "visual": {"type": "color"}, "on_screen": null},
    {"narration": "One common reading: I, you, the other, and the bond that ties all three.", "visual": {"type": "video", "query": "four candles dark"}, "on_screen": "I · You · They · The bond"},
    {"narration": "Pluck one, and the others hum. That's Bendre's idea of life.", "visual": {"type": "video", "query": "sitar playing slow motion"}, "on_screen": null},
    {"narration": "No self exists alone. Every relationship is a string in the same instrument.", "visual": {"type": "video", "query": "people walking crowd silhouette sunset"}, "on_screen": null},
    {"narration": "Follow for one idea from India's poets and thinkers, every day.", "visual": {"type": "color"}, "on_screen": null}
  ],
  "cta": null,
  "music": null
}
```
(Note: interpretations of *Naaku Tanti* vary — the script says "one common reading", which keeps it honest.)
