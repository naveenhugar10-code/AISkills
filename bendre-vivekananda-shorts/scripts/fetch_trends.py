#!/usr/bin/env python3
"""Collect trend signals for Vivekananda / Bendre / India short-video ideas.

Every source is optional: failures are recorded under "errors" and the script
still writes a usable JSON (the calendar always works offline).

Usage:
  python fetch_trends.py --out trends.json [--days-ahead 21] [--date 2026-10-31]
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.parse
import xml.etree.ElementTree as ET

try:
    import requests
except ImportError:  # pragma: no cover
    sys.exit("pip install requests")

UA = {"User-Agent": "bendre-vivekananda-shorts/1.0 (trend research)"}
TIMEOUT = 15

# (month, day, title, theme, angle)  -- keep in sync with references/calendar.md
CALENDAR = [
    (1, 12, "Swami Vivekananda Jayanti / National Youth Day", "vivekananda", "His message to youth: strength, character, 'Arise, awake'"),
    (9, 11, "Vivekananda's Chicago address (1893)", "vivekananda", "'Sisters and Brothers of America' and universal acceptance"),
    (7, 4, "Vivekananda Mahasamadhi (1902)", "vivekananda", "What he achieved in 39 years"),
    (5, 1, "Ramakrishna Mission founded (1897)", "vivekananda", "Service to people as worship"),
    (12, 25, "Vivekananda at Kanyakumari rock (1892)", "vivekananda", "Three days of meditation that shaped his mission"),
    (1, 31, "Da Ra Bendre Jayanti", "bendre", "Who was Varakavi Bendre? Dharwad, Sadhanakeri, Jnanpith"),
    (10, 26, "Da Ra Bendre death anniversary (1981)", "bendre", "His lines on time, love and life (explain, don't recite)"),
    (11, 1, "Karnataka Rajyotsava", "bendre", "Kannada poets you must know: Bendre, Kuvempu, Masti..."),
    (12, 29, "Kuvempu Jayanti", "india", "Kannada's first Jnanpith; Vishwamanava idea"),
    (1, 23, "Netaji Subhas Chandra Bose Jayanti (Parakram Diwas)", "india", "Netaji called Vivekananda his spiritual guide"),
    (1, 26, "Republic Day", "india", "Constitution ideas in 45 seconds"),
    (2, 21, "International Mother Language Day", "bendre", "Why Bendre wrote in spoken Dharwad Kannada"),
    (2, 28, "National Science Day (C.V. Raman)", "india", "The Raman effect story"),
    (3, 21, "World Poetry Day", "bendre", "One Bendre idea explained"),
    (4, 14, "Ambedkar Jayanti", "india", "Ambedkar on education"),
    (5, 7, "Rabindranath Tagore Jayanti", "india", "Tagore and Vivekananda: two Bengal voices"),
    (6, 21, "International Yoga Day", "vivekananda", "Vivekananda's Raja Yoga brought yoga to the West"),
    (8, 15, "Independence Day", "india", "Vivekananda's influence on freedom fighters"),
    (9, 15, "Engineers' Day (Visvesvaraya)", "india", "Karnataka's Sir M.V."),
    (10, 2, "Gandhi Jayanti", "india", "Gandhi on reading Vivekananda"),
    (11, 14, "Children's Day", "india", "Vivekananda's idea of education"),
    (11, 26, "Constitution Day", "india", "Preamble in 45 seconds"),
    (12, 22, "National Mathematics Day (Ramanujan)", "india", "Ramanujan's story"),
]

NEWS_QUERIES = [
    ("Swami Vivekananda", "en-IN", "IN", "IN:en"),
    ("Vivekananda", "hi", "IN", "IN:hi"),
    ("Bendre poet", "en-IN", "IN", "IN:en"),
    ("ಬೇಂದ್ರೆ", "kn", "IN", "IN:kn"),
    ("ವಿವೇಕಾನಂದ", "kn", "IN", "IN:kn"),
    ("Kannada literature", "en-IN", "IN", "IN:en"),
    ("Indian culture heritage", "en-IN", "IN", "IN:en"),
]

WIKI_ARTICLES = [
    ("en.wikipedia", "Swami_Vivekananda"),
    ("en.wikipedia", "D._R._Bendre"),
    ("en.wikipedia", "Ramakrishna"),
    ("en.wikipedia", "Naaku_Tanti"),
    ("kn.wikipedia", "ದ._ರಾ._ಬೇಂದ್ರೆ"),
    ("kn.wikipedia", "ಸ್ವಾಮಿ_ವಿವೇಕಾನಂದ"),
    ("hi.wikipedia", "स्वामी_विवेकानन्द"),
]

TREND_KEYWORDS = ["Swami Vivekananda", "Vivekananda quotes", "Bendre", "Kannada poem", "National Youth Day"]


def calendar_events(today, days_ahead):
    out = []
    for m, d, title, theme, angle in CALENDAR:
        for year in (today.year, today.year + 1):
            try:
                date = dt.date(year, m, d)
            except ValueError:
                continue
            delta = (date - today).days
            if -1 <= delta <= days_ahead:
                out.append({"date": date.isoformat(), "days_away": delta, "title": title,
                            "theme": theme, "angle": angle})
    return sorted(out, key=lambda e: e["days_away"])


def google_news(errors, per_query=8):
    items = []
    for q, hl, gl, ceid in NEWS_QUERIES:
        url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(q + " when:7d")
               + f"&hl={hl}&gl={gl}&ceid={ceid}")
        try:
            r = requests.get(url, headers=UA, timeout=TIMEOUT)
            r.raise_for_status()
            root = ET.fromstring(r.content)
            for it in root.iter("item"):
                items.append({"query": q, "title": it.findtext("title"), "link": it.findtext("link"),
                              "published": it.findtext("pubDate"),
                              "source": (it.find("source").text if it.find("source") is not None else None)})
                if sum(1 for x in items if x["query"] == q) >= per_query:
                    break
        except Exception as e:  # noqa: BLE001
            errors.append(f"google_news[{q}]: {type(e).__name__}: {e}"[:200])
    return items


def wiki_pageviews(errors, today):
    end = today - dt.timedelta(days=1)
    start = end - dt.timedelta(days=27)
    out = []
    for project, article in WIKI_ARTICLES:
        url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
               f"{project}/all-access/user/{urllib.parse.quote(article, safe='')}/daily/"
               f"{start:%Y%m%d}/{end:%Y%m%d}")
        try:
            r = requests.get(url, headers=UA, timeout=TIMEOUT)
            r.raise_for_status()
            views = [x["views"] for x in r.json().get("items", [])]
            if not views:
                continue
            last7 = sum(views[-7:]) / max(1, len(views[-7:]))
            prev = views[:-7] or views
            base = sum(prev) / len(prev)
            out.append({"project": project, "article": article, "avg_last7": round(last7),
                        "avg_prev21": round(base), "spike_ratio": round(last7 / base, 2) if base else None})
        except Exception as e:  # noqa: BLE001
            errors.append(f"wikipedia[{project}/{article}]: {type(e).__name__}: {e}"[:200])
    return sorted(out, key=lambda x: -(x["spike_ratio"] or 0))


def google_trends(errors):
    try:
        from pytrends.request import TrendReq  # type: ignore
    except ImportError:
        errors.append("google_trends: pytrends not installed (pip install pytrends)")
        return {}
    out = {}
    try:
        pt = TrendReq(hl="en-IN", tz=330)
        pt.build_payload(TREND_KEYWORDS, timeframe="now 7-d", geo="IN")
        related = pt.related_queries()
        for kw, d in related.items():
            rising = d.get("rising") if d else None
            if rising is not None:
                out[kw] = rising.head(10).to_dict("records")
        try:
            daily = pt.trending_searches(pn="india")
            out["_india_trending_searches"] = daily[0].head(20).tolist()
        except Exception as e:  # noqa: BLE001
            errors.append(f"google_trends.trending_searches: {e}"[:200])
    except Exception as e:  # noqa: BLE001
        errors.append(f"google_trends: {type(e).__name__}: {e}"[:200])
    return out


def youtube(errors, today):
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        errors.append("youtube: YOUTUBE_API_KEY not set")
        return []
    out = []
    since = (today - dt.timedelta(days=14)).isoformat() + "T00:00:00Z"
    for q in ["Vivekananda shorts", "Bendre kannada", "ವಿವೇಕಾನಂದ", "Indian philosophy shorts"]:
        try:
            r = requests.get("https://www.googleapis.com/youtube/v3/search", timeout=TIMEOUT, params={
                "part": "snippet", "q": q, "type": "video", "order": "viewCount", "regionCode": "IN",
                "publishedAfter": since, "maxResults": 10, "key": key})
            r.raise_for_status()
            ids = [it["id"]["videoId"] for it in r.json().get("items", [])]
            if not ids:
                continue
            s = requests.get("https://www.googleapis.com/youtube/v3/videos", timeout=TIMEOUT, params={
                "part": "snippet,statistics,contentDetails", "id": ",".join(ids), "key": key}).json()
            for v in s.get("items", []):
                out.append({"query": q, "title": v["snippet"]["title"], "channel": v["snippet"]["channelTitle"],
                            "views": int(v["statistics"].get("viewCount", 0)),
                            "duration": v["contentDetails"]["duration"],
                            "url": f"https://youtu.be/{v['id']}"})
        except Exception as e:  # noqa: BLE001
            errors.append(f"youtube[{q}]: {type(e).__name__}: {e}"[:200])
    return sorted(out, key=lambda x: -x["views"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="trends.json")
    ap.add_argument("--days-ahead", type=int, default=21)
    ap.add_argument("--date", help="override today's date (YYYY-MM-DD)")
    ap.add_argument("--offline", action="store_true", help="calendar only, no network")
    a = ap.parse_args()

    today = dt.date.fromisoformat(a.date) if a.date else dt.date.today()
    errors = []
    result = {"generated_for": today.isoformat(),
              "calendar": calendar_events(today, a.days_ahead)}
    if not a.offline:
        result["news"] = google_news(errors)
        result["wikipedia"] = wiki_pageviews(errors, today)
        result["google_trends"] = google_trends(errors)
        result["youtube"] = youtube(errors, today)
    result["errors"] = errors
    live = [k for k in ("news", "wikipedia", "google_trends", "youtube") if result.get(k)]
    result["live_sources_ok"] = live

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"wrote {a.out}: {len(result['calendar'])} calendar events, live sources: {live or 'none'}, "
          f"{len(errors)} errors")


if __name__ == "__main__":
    main()
