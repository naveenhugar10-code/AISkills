#!/usr/bin/env python3
"""Render a faceless vertical short (1080x1920) from a scene-spec JSON.

Pipeline: edge-tts narration (+word timings) -> visuals (local / Pexels / Pixabay /
Wikimedia Commons / gradient) -> per-scene clips with Ken Burns -> word-synced
ASS captions burned in -> optional ducked music -> video.mp4 + extras.

Usage:
  python make_video.py spec.json --out outdir/ [--font "Noto Sans Kannada"] [--no-tts]
Env (optional): PEXELS_API_KEY, PIXABAY_API_KEY
See ../SKILL.md for the spec format.
"""
import argparse
import asyncio
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap

try:
    import requests
    from PIL import Image, ImageDraw, ImageFilter
except ImportError:
    sys.exit("pip install requests pillow")

W, H, FPS = 1080, 1920, 30
UA = {"User-Agent": "bendre-vivekananda-shorts/1.0 (faceless short renderer)"}
DEFAULT_VOICES = {"en-IN": "en-IN-PrabhatNeural", "kn-IN": "kn-IN-GaganNeural", "hi-IN": "hi-IN-MadhurNeural",
                  "mr-IN": "mr-IN-ManoharNeural"}
SCRIPT_FONTS = {"kn-IN": "Noto Sans Kannada", "hi-IN": "Noto Sans Devanagari", "mr-IN": "Noto Sans Devanagari"}
GRADIENTS = [((32, 12, 4), (196, 92, 18)), ((10, 14, 38), (120, 60, 20)), ((6, 24, 30), (40, 110, 110)),
             ((20, 8, 30), (150, 50, 40))]


def run(cmd, quiet=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd[:6])}...\n{r.stderr[-1500:]}")
    return r.stdout


def probe_duration(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path])
    return float(out.strip())


# ---------------------------------------------------------------- TTS
async def _tts(text, voice, rate, mp3_path):
    import edge_tts
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary", proxy=proxy)
    words = []
    with open(mp3_path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append({"start": chunk["offset"] / 1e7, "end": (chunk["offset"] + chunk["duration"]) / 1e7,
                              "word": chunk["text"]})
    return words


def synthesize(text, voice, rate, mp3_path):
    """Return word timings; raises on failure. Swap this for another TTS provider if needed."""
    words = asyncio.run(_tts(text, voice, rate, mp3_path))
    if not os.path.exists(mp3_path) or os.path.getsize(mp3_path) < 1000:
        raise RuntimeError("TTS returned no audio")
    return words


def even_word_timings(text, duration):
    toks = text.split()
    step = duration / max(1, len(toks))
    return [{"start": i * step, "end": (i + 1) * step, "word": t} for i, t in enumerate(toks)]


# ---------------------------------------------------------------- visuals
def _download(url, dest):
    r = requests.get(url, headers=UA, timeout=60, stream=True)
    r.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in r.iter_content(1 << 16):
            f.write(chunk)
    return dest


def from_pexels(query, kind, assets):
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return None
    hdr = {"Authorization": key, **UA}
    if kind == "video":
        j = requests.get("https://api.pexels.com/videos/search", headers=hdr, timeout=20,
                         params={"query": query, "orientation": "portrait", "per_page": 5}).json()
        for v in j.get("videos", []):
            files = [f for f in v["video_files"] if f.get("height") and f["height"] >= 1280]
            if files:
                best = min(files, key=lambda f: abs(f["height"] - 1920))
                dest = os.path.join(assets, f"pexels_{v['id']}.mp4")
                _download(best["link"], dest)
                return dest, f"Pexels video by {v['user']['name']} ({v['url']}) - Pexels License", "video"
    j = requests.get("https://api.pexels.com/v1/search", headers=hdr, timeout=20,
                     params={"query": query, "orientation": "portrait", "per_page": 5}).json()
    for p in j.get("photos", []):
        dest = os.path.join(assets, f"pexels_{p['id']}.jpg")
        _download(p["src"]["portrait"], dest)
        return dest, f"Pexels photo by {p['photographer']} ({p['url']}) - Pexels License", "image"
    return None


def from_pixabay(query, kind, assets):
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return None
    if kind == "video":
        j = requests.get("https://pixabay.com/api/videos/", timeout=20, params={"key": key, "q": query}).json()
        for h in j.get("hits", []):
            url = (h["videos"].get("large") or {}).get("url") or h["videos"]["medium"]["url"]
            if url:
                dest = os.path.join(assets, f"pixabay_{h['id']}.mp4")
                _download(url, dest)
                return dest, f"Pixabay video by {h['user']} ({h['pageURL']}) - Pixabay License", "video"
    j = requests.get("https://pixabay.com/api/", timeout=20,
                     params={"key": key, "q": query, "image_type": "photo", "orientation": "vertical"}).json()
    for h in j.get("hits", []):
        dest = os.path.join(assets, f"pixabay_{h['id']}.jpg")
        _download(h["largeImageURL"], dest)
        return dest, f"Pixabay image by {h['user']} ({h['pageURL']}) - Pixabay License", "image"
    return None


def from_commons(query, assets):
    j = requests.get("https://commons.wikimedia.org/w/api.php", headers=UA, timeout=20, params={
        "action": "query", "format": "json", "generator": "search", "gsrsearch": f"{query} filetype:bitmap",
        "gsrnamespace": 6, "gsrlimit": 6, "prop": "imageinfo", "iiprop": "url|extmetadata|size",
        "iiurlwidth": 1600}).json()
    pages = sorted((j.get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 99))
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]
        url = ii.get("thumburl") or ii.get("url")
        if not url:
            continue
        meta = ii.get("extmetadata", {})
        lic = meta.get("LicenseShortName", {}).get("value", "see file page")
        artist = re.sub("<[^>]+>", "", meta.get("Artist", {}).get("value", "unknown")).strip()
        ext = os.path.splitext(url.split("?")[0])[1] or ".jpg"
        dest = os.path.join(assets, "commons_" + hashlib.md5(url.encode()).hexdigest()[:10] + ext)
        _download(url, dest)
        return dest, f"Wikimedia Commons: {p['title']} by {artist} - {lic} ({ii.get('descriptionurl', '')})", "image"
    return None


def gradient(idx, assets):
    top, bot = GRADIENTS[idx % len(GRADIENTS)]
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse([W * 0.15, H * 0.25, W * 0.85, H * 0.6], fill=70)
    img = Image.composite(Image.new("RGB", (W, H), (255, 200, 120)), img, glow.filter(ImageFilter.GaussianBlur(160)))
    dest = os.path.join(assets, f"gradient_{idx}.png")
    img.save(dest)
    return dest, "Generated gradient background", "image"


def resolve_visual(scene, idx, assets, log):
    v = scene.get("visual") or {"type": "color"}
    kind = v.get("type", "image")
    if v.get("path") and os.path.exists(v["path"]):
        k = "video" if v["path"].lower().endswith((".mp4", ".mov", ".webm", ".mkv")) else "image"
        return v["path"], f"User-supplied: {os.path.basename(v['path'])}", k, v.get("fit")
    if kind != "color" and v.get("query"):
        for name, fn in (("pexels", lambda: from_pexels(v["query"], kind, assets)),
                         ("pixabay", lambda: from_pixabay(v["query"], kind, assets)),
                         ("commons", lambda: from_commons(v["query"], assets))):
            try:
                got = fn()
                if got:
                    return (*got, v.get("fit"))
            except Exception as e:  # noqa: BLE001
                log["warnings"].append(f"scene {idx}: {name} failed: {type(e).__name__}: {str(e)[:120]}")
        log["warnings"].append(f"scene {idx}: no stock result for '{v['query']}', using gradient")
    return (*gradient(idx, assets), "cover")


def prepare_still(src, dest, fit):
    """Cover-crop, or 'contain' over a blurred, darkened copy (better for archival photos)."""
    im = Image.open(src).convert("RGB")
    def cover(img, w, h):
        s = max(w / img.width, h / img.height)
        img = img.resize((max(w, int(img.width * s + 0.5)), max(h, int(img.height * s + 0.5))), Image.LANCZOS)
        l, t = (img.width - w) // 2, (img.height - h) // 2
        return img.crop((l, t, l + w, t + h))
    if fit is None:
        fit = "cover" if im.height >= im.width * 1.3 else "contain"
    if fit == "cover":
        out = cover(im, W, H)
    else:
        bg = cover(im, W, H).filter(ImageFilter.GaussianBlur(40))
        bg = Image.blend(bg, Image.new("RGB", (W, H), (0, 0, 0)), 0.45)
        s = min(W / im.width, (H * 0.62) / im.height)
        fg = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
        bg.paste(fg, ((W - fg.width) // 2, int(H * 0.19)))
        out = bg
    out.save(dest, quality=95)
    return dest


def render_scene_clip(src, kind, fit, dur, dest, idx):
    frames = int(round(dur * FPS))
    if kind == "video":
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1,"
              "eq=brightness=-0.05")
        run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", src, "-t", f"{dur:.3f}", "-vf", vf, "-an",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", dest])
        return
    still = prepare_still(src, dest + ".jpg", fit)
    zoom_in = idx % 2 == 0
    z = f"min(1+0.0009*on,1.15)" if zoom_in else f"max(1.15-0.0009*on,1.0)"
    vf = (f"scale={W * 2}:{H * 2},zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}"
          f":s={W}x{H}:fps={FPS},setsar=1,eq=brightness=-0.04")
    run(["ffmpeg", "-y", "-i", still, "-vf", vf, "-frames:v", str(frames), "-c:v", "libx264", "-preset",
         "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", dest])


# ---------------------------------------------------------------- captions
def ass_time(t):
    t = max(0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def esc(s):
    return s.replace("\\", "\\\\").replace("{", "(").replace("}", ")").replace("\n", "\\N")


INDIC_RANGES = [((0x0C80, 0x0CFF), "Noto Sans Kannada"), ((0x0900, 0x097F), "Noto Sans Devanagari"),
                ((0x0B80, 0x0BFF), "Noto Sans Tamil"), ((0x0C00, 0x0C7F), "Noto Sans Telugu"),
                ((0x0980, 0x09FF), "Noto Sans Bengali")]


def script_font(text):
    for (lo, hi), fam in INDIC_RANGES:
        if any(lo <= ord(c) <= hi for c in text):
            return fam
    return None


def fontify(text):
    """Escape for ASS and switch to a script-capable font when the text is Indic."""
    fam = script_font(text)
    return (r"{\fn" + fam + "}" if fam else "") + esc(text)


def check_fonts(texts, log):
    needed = {f for f in (script_font(t) for t in texts) if f}
    try:
        have = run(["fc-list", ":", "family"])
    except Exception:  # noqa: BLE001
        return
    for fam in needed:
        if fam not in have:
            log["warnings"].append(f"font '{fam}' not installed - Indic text will render as boxes. "
                                   "Install fonts-noto-core (apt) or Noto fonts from fonts.google.com")


def build_captions(words, overlays, font, ass_path, srt_path, chunk=3):
    header = textwrap.dedent(f"""\
        [Script Info]
        ScriptType: v4.00+
        PlayResX: {W}
        PlayResY: {H}
        WrapStyle: 0
        ScaledBorderAndShadow: yes

        [V4+ Styles]
        Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
        Style: Cap,{font},84,&H00FFFFFF,&H0000D7FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,6,2,2,90,90,560,1
        Style: Top,{font},60,&H00FFFFFF,&H00FFFFFF,&H00000000,&H8C000000,-1,0,0,0,100,100,0,0,3,18,0,8,90,90,300,1
        Style: Title,{font},104,&H0040D0FF,&H00FFFFFF,&H00000000,&H78000000,-1,0,0,0,100,100,0,0,1,7,3,8,80,80,600,1

        [Events]
        Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        """)
    lines, srt = [header], []
    # group words into chunks; one event per word with the active word highlighted
    groups = [words[i:i + chunk] for i in range(0, len(words), chunk)]
    for gi, g in enumerate(groups):
        g_end = groups[gi + 1][0]["start"] if gi + 1 < len(groups) else g[-1]["end"] + 0.4
        g_end = min(g_end, g[-1]["end"] + 0.6)
        srt.append(f"{len(srt) + 1}\n{srt_time(g[0]['start'])} --> {srt_time(g_end)}\n"
                   + " ".join(w["word"] for w in g) + "\n")
        for wi, w in enumerate(g):
            st = w["start"]
            en = g[wi + 1]["start"] if wi + 1 < len(g) else g_end
            txt = " ".join((r"{\c&H0000D7FF&}" + esc(x["word"]) + r"{\c&H00FFFFFF&}") if j == wi else esc(x["word"])
                           for j, x in enumerate(g))
            fam = script_font(txt)
            if fam:
                txt = r"{\fn" + fam + "}" + txt
            lines.append(f"Dialogue: 0,{ass_time(st)},{ass_time(en)},Cap,,0,0,0,,{txt}\n")
    for o in overlays:
        lines.append(f"Dialogue: 1,{ass_time(o['start'])},{ass_time(o['end'])},{o['style']},,0,0,0,,"
                     + r"{\fad(250,250)}" + fontify(o["text"]) + "\n")
    with open(ass_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt))


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--out", required=True)
    ap.add_argument("--font", help="caption font family (default: DejaVu Sans / Noto for Indic scripts)")
    ap.add_argument("--no-tts", action="store_true", help="silent preview with estimated timings")
    ap.add_argument("--keep-temp", action="store_true")
    a = ap.parse_args()

    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found on PATH")
    spec = json.load(open(a.spec, encoding="utf-8"))
    out = os.path.abspath(a.out)
    tmp = os.path.join(out, "_work")
    assets = os.path.join(out, "assets")
    os.makedirs(tmp, exist_ok=True)
    os.makedirs(assets, exist_ok=True)

    lang = spec.get("language", "en-IN")
    voice = spec.get("voice") or DEFAULT_VOICES.get(lang, "en-IN-PrabhatNeural")
    rate = spec.get("rate", "+0%")
    font = a.font or SCRIPT_FONTS.get(lang, "DejaVu Sans")
    scenes = list(spec["scenes"])
    if spec.get("cta"):
        scenes.append({"narration": spec["cta"], "visual": {"type": "color"}, "on_screen": None})

    log = {"id": spec.get("id"), "voice": voice, "font": font, "tts": "edge-tts", "warnings": [], "scenes": []}
    credits = []
    all_words, overlays, wavs, clips = [], [], [], []
    t = 0.0
    for i, sc in enumerate(scenes):
        text = sc["narration"].strip()
        mp3 = os.path.join(tmp, f"s{i:02d}.mp3")
        wav = os.path.join(tmp, f"s{i:02d}.wav")
        words = None
        if not a.no_tts and log["tts"] == "edge-tts":
            try:
                words = synthesize(text, voice, rate, mp3)
                speech = probe_duration(mp3)
            except Exception as e:  # noqa: BLE001
                log["tts"] = "silent-fallback"
                log["warnings"].append(f"TTS failed ({type(e).__name__}: {str(e)[:150]}); rendering SILENT preview")
        if words is None:
            log["tts"] = "silent-fallback" if not a.no_tts else "disabled"
            speech = max(1.5, len(text.split()) / 2.6)
            words = even_word_timings(text, speech)
            run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{speech:.3f}", mp3])
        if not words:  # TTS returned audio but no boundaries
            words = even_word_timings(text, speech)
        pad = 0.7 if i == len(scenes) - 1 else 0.3
        dur = speech + pad
        run(["ffmpeg", "-y", "-i", mp3, "-af", f"apad=whole_dur={dur:.3f}", "-t", f"{dur:.3f}", "-ar", "44100",
             "-ac", "2", wav])
        for w in words:
            all_words.append({"start": t + w["start"], "end": t + w["end"], "word": w["word"]})
        if sc.get("on_screen"):
            overlays.append({"start": t + 0.1, "end": t + dur - 0.1, "style": "Top", "text": sc["on_screen"]})
        src, credit, kind, fit = resolve_visual(sc, i, assets, log)
        credits.append(f"Scene {i + 1}: {credit}")
        clip = os.path.join(tmp, f"v{i:02d}.mp4")
        render_scene_clip(src, kind, fit, dur, clip, i)
        clips.append(clip)
        wavs.append(wav)
        log["scenes"].append({"index": i, "start": round(t, 2), "duration": round(dur, 2), "visual": credit})
        t += dur

    check_fonts([sc["narration"] for sc in scenes] + [sc.get("on_screen") or "" for sc in scenes]
                + [spec.get("title_card") or ""], log)
    if spec.get("title_card"):
        overlays.append({"start": 0.0, "end": min(2.2, t), "style": "Title", "text": spec["title_card"]})

    # concat video + audio
    vlist = os.path.join(tmp, "v.txt")
    alist = os.path.join(tmp, "a.txt")
    open(vlist, "w").write("".join(f"file '{c}'\n" for c in clips))
    open(alist, "w").write("".join(f"file '{w}'\n" for w in wavs))
    vcat, voice_wav = os.path.join(tmp, "video_noaudio.mp4"), os.path.join(tmp, "voice.wav")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", vlist, "-c", "copy", vcat])
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", alist, "-c", "copy", voice_wav])
    run(["ffmpeg", "-y", "-i", voice_wav, "-c:a", "libmp3lame", "-b:a", "192k", os.path.join(out, "voiceover.mp3")])

    ass, srt = os.path.join(out, "captions.ass"), os.path.join(out, "captions.srt")
    build_captions(all_words, overlays, font, ass, srt)

    final = os.path.join(out, "video.mp4")
    ass_arg = ass.replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    cmd = ["ffmpeg", "-y", "-i", vcat, "-i", voice_wav]
    music = spec.get("music")
    if music and os.path.exists(music):
        cmd += ["-stream_loop", "-1", "-i", music]
        afilter = (f"[2:a]volume=0.12,afade=t=out:st={max(0, t - 1.5):.2f}:d=1.5[m];"
                   "[1:a][m]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5[a]")
        credits.append(f"Music: {os.path.basename(music)} (user-supplied)")
    else:
        afilter = "[1:a]loudnorm=I=-14:TP=-1.5[a]"
    cmd += ["-filter_complex", f"[0:v]ass='{ass_arg}'[v];{afilter}", "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-t", f"{t:.3f}", final]
    run(cmd)
    run(["ffmpeg", "-y", "-ss", "0.8", "-i", final, "-frames:v", "1", "-q:v", "2", os.path.join(out, "cover.jpg")])

    with open(os.path.join(out, "credits.txt"), "w", encoding="utf-8") as f:
        f.write(f"Narration: AI voice ({voice}, Microsoft Edge TTS)\n" + "\n".join(credits) + "\n")
    log["duration_s"] = round(probe_duration(final), 2)
    log["output"] = final
    with open(os.path.join(out, "render_log.json"), "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    if not a.keep_temp:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"rendered {final} ({log['duration_s']}s, tts={log['tts']})")
    for w in log["warnings"]:
        print("WARNING:", w)
    if log["tts"] != "edge-tts":
        print("NOTE: this is a SILENT PREVIEW - do not publish it.")


if __name__ == "__main__":
    main()
