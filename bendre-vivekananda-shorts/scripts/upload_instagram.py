#!/usr/bin/env python3
"""Publish a Reel via the Instagram Graph API (Business/Creator account).

The Graph API fetches the video from a PUBLIC HTTPS URL - it cannot take a local file.
Host video.mp4 somewhere (S3/GCS/R2/release asset) and pass --video-url.

Usage:
  python upload_instagram.py video.mp4 metadata.json --video-url https://.../video.mp4
                             [--cover-url https://.../cover.jpg] [--dry-run]
Env: IG_USER_ID, IG_ACCESS_TOKEN (long-lived), optional IG_GRAPH_VERSION (default v21.0)
"""
import argparse
import json
import os
import sys
import time

import requests


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", help="local file (only used for sanity checks)")
    ap.add_argument("metadata")
    ap.add_argument("--video-url", required=True)
    ap.add_argument("--cover-url")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    meta = json.load(open(a.metadata, encoding="utf-8"))["instagram"]
    caption = meta["caption"][:2200]
    params = {"media_type": "REELS", "video_url": a.video_url, "caption": caption,
              "share_to_feed": str(meta.get("share_to_feed", True)).lower()}
    if a.cover_url:
        params["cover_url"] = a.cover_url
    if a.dry_run:
        print(json.dumps(params, ensure_ascii=False, indent=2))
        return

    user, token = os.environ.get("IG_USER_ID"), os.environ.get("IG_ACCESS_TOKEN")
    if not (user and token):
        sys.exit("set IG_USER_ID and IG_ACCESS_TOKEN (see references/platforms.md)")
    base = f"https://graph.facebook.com/{os.environ.get('IG_GRAPH_VERSION', 'v21.0')}"

    r = requests.post(f"{base}/{user}/media", data={**params, "access_token": token}, timeout=60)
    r.raise_for_status()
    container = r.json()["id"]
    print("container", container, "- waiting for Instagram to process the video...")
    for _ in range(60):  # up to ~10 minutes
        s = requests.get(f"{base}/{container}", params={"fields": "status_code,status", "access_token": token},
                         timeout=30).json()
        code = s.get("status_code")
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            sys.exit(f"processing failed: {s}")
        time.sleep(10)
    else:
        sys.exit("timed out waiting for processing")
    p = requests.post(f"{base}/{user}/media_publish", data={"creation_id": container, "access_token": token},
                      timeout=60)
    p.raise_for_status()
    media_id = p.json()["id"]
    link = requests.get(f"{base}/{media_id}", params={"fields": "permalink", "access_token": token},
                        timeout=30).json().get("permalink")
    print(json.dumps({"platform": "instagram", "id": media_id, "url": link}))


if __name__ == "__main__":
    main()
