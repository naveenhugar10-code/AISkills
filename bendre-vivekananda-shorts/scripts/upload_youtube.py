#!/usr/bin/env python3
"""Upload a rendered short to YouTube (Data API v3, resumable). Defaults to PRIVATE.

Usage:
  python upload_youtube.py video.mp4 metadata.json [--client-secret client_secret.json]
                           [--token youtube_token.json] [--public] [--dry-run]
Requires: pip install google-api-python-client google-auth-oauthlib
"""
import argparse
import json
import os
import sys

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def credentials(client_secret, token_path):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = Credentials.from_authorized_user_file(token_path, SCOPES) if os.path.exists(token_path) else None
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        if not os.path.exists(client_secret):
            sys.exit(f"missing {client_secret}: create an OAuth Desktop client in Google Cloud console "
                     "(YouTube Data API v3 enabled) and download it")
        creds = InstalledAppFlow.from_client_secrets_file(client_secret, SCOPES).run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return creds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("metadata")
    ap.add_argument("--client-secret", default=os.environ.get("YT_CLIENT_SECRET", "client_secret.json"))
    ap.add_argument("--token", default=os.environ.get("YT_TOKEN", "youtube_token.json"))
    ap.add_argument("--public", action="store_true", help="publish publicly instead of the metadata/private default")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    meta = json.load(open(a.metadata, encoding="utf-8"))["youtube"]
    title = meta["title"][:100]
    desc = meta.get("description", "")
    if "#shorts" not in (title + desc).lower():
        desc = desc.rstrip() + "\n\n#Shorts"
    body = {
        "snippet": {"title": title, "description": desc[:5000], "tags": meta.get("tags", [])[:30],
                    "categoryId": str(meta.get("categoryId", "27")),
                    "defaultLanguage": meta.get("language", "en"), "defaultAudioLanguage": meta.get("language", "en")},
        "status": {"privacyStatus": "public" if a.public else meta.get("privacyStatus", "private"),
                   "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": bool(meta.get("containsSyntheticMedia", False))},
    }
    if a.dry_run:
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return

    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    yt = build("youtube", "v3", credentials=credentials(a.client_secret, a.token))
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(a.video, chunksize=8 * 1024 * 1024, resumable=True,
                                                        mimetype="video/mp4"))
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"uploading... {int(status.progress() * 100)}%")
    vid = resp["id"]
    print(json.dumps({"platform": "youtube", "id": vid, "url": f"https://youtube.com/shorts/{vid}",
                      "privacy": body["status"]["privacyStatus"]}))


if __name__ == "__main__":
    main()
