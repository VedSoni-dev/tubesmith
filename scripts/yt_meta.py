#!/usr/bin/env python3
"""Fetch YouTube metadata for every candidate. Also catches deleted/private videos (~6% on HN).

Two modes:
  api    : YouTube Data API v3 videos.list, 50 ids per request (1 quota unit each; free tier
           is 10,000/day). Gets duration, views, likes, publish date, description, tags.
           Needs $YOUTUBE_API_KEY (see references/sources.md).
  oembed : no key. Title + channel only, one request per video. Good enough to try things out.

Writes data/meta.jsonl: {vid, ok, title, channel, channel_id, published, duration_s, views,
likes, description, tags, embeddable}. Resumable.

  python3 scripts/yt_meta.py --config tube.config.json            # api if key is set, else oembed
"""
import argparse
import os
import re
import time
import urllib.error
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

from common import DATA, append_jsonl, get, http_json, load_config, progress, read_jsonl

DUR_RE = re.compile(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def iso_seconds(d):
    m = DUR_RE.fullmatch(d or "")
    if not m:
        return None
    dd, h, mi, s = (int(x or 0) for x in m.groups())
    return dd * 86400 + h * 3600 + mi * 60 + s


def from_api(item):
    sn, cd, stt, st = (item.get(k, {}) for k in ("snippet", "contentDetails", "statistics", "status"))
    return {
        "ok": st.get("privacyStatus") in ("public", "unlisted"),
        "title": sn.get("title"), "channel": sn.get("channelTitle"),
        "channel_id": sn.get("channelId"), "published": sn.get("publishedAt"),
        "duration_s": iso_seconds(cd.get("duration")),
        "views": int(stt["viewCount"]) if "viewCount" in stt else None,
        "likes": int(stt["likeCount"]) if "likeCount" in stt else None,
        "description": (sn.get("description") or "")[:600],
        "tags": (sn.get("tags") or [])[:12],
        "embeddable": st.get("embeddable", True),
        "live": sn.get("liveBroadcastContent") in ("live", "upcoming"),
    }


def oembed(vid):
    url = "https://www.youtube.com/oembed?" + urllib.parse.urlencode(
        {"url": "https://www.youtube.com/watch?v=" + vid, "format": "json"})
    try:
        d = http_json(url, tries=3)
        return {"vid": vid, "ok": True, "title": d.get("title"), "channel": d.get("author_name"),
                "channel_url": d.get("author_url"), "embeddable": True}
    except urllib.error.HTTPError as e:
        if e.code == 401:  # exists, but the uploader disabled embedding
            return {"vid": vid, "ok": True, "embeddable": False}
        if e.code in (400, 403, 404):
            return {"vid": vid, "ok": False}
        return None  # transient; retry on the next run
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="tube.config.json")
    ap.add_argument("--mode", choices=["auto", "api", "oembed"], default="auto")
    args = ap.parse_args()
    cfg = load_config(args.config)
    key = os.environ.get(get(cfg, "youtube.api_key_env", "YOUTUBE_API_KEY") or "")
    mode = args.mode if args.mode != "auto" else ("api" if key else "oembed")
    if mode == "api" and not key:
        raise SystemExit("Set $YOUTUBE_API_KEY first (references/sources.md), or use --mode oembed.")

    out = os.path.join(DATA, "meta.jsonl")
    done = {r["vid"] for r in read_jsonl(out) if r.get("mode") == mode or mode == "oembed"}
    todo = [c["vid"] for c in read_jsonl(os.path.join(DATA, "candidates.jsonl")) if c["vid"] not in done]
    print("Metadata (%s): %d to fetch, %d cached" % (mode, len(todo), len(done)))

    if mode == "api":
        for i in range(0, len(todo), 50):
            ids = todo[i:i + 50]
            q = urllib.parse.urlencode({"part": "snippet,contentDetails,statistics,status",
                                        "id": ",".join(ids), "key": key})
            try:
                items = http_json("https://www.googleapis.com/youtube/v3/videos?" + q).get("items", [])
            except urllib.error.HTTPError as e:
                raise SystemExit("\nYouTube API error %s. Quota used up (resets at midnight Pacific) "
                                 "or the key isn't enabled for YouTube Data API v3." % e.code)
            got = {it["id"]: it for it in items}
            rows = []
            for v in ids:  # ids missing from the response were deleted or made private
                row = from_api(got[v]) if v in got else {"ok": False}
                row.update({"vid": v, "mode": "api"})
                rows.append(row)
            append_jsonl(out, rows)
            progress("api %d/%d" % (min(i + 50, len(todo)), len(todo)))
            time.sleep(0.2)
    else:
        with ThreadPoolExecutor(8) as pool:
            batch = []
            for n, row in enumerate(pool.map(oembed, todo), 1):
                if row:
                    row["mode"] = "oembed"
                    batch.append(row)
                if len(batch) >= 50:
                    append_jsonl(out, batch)
                    batch = []
                progress("oembed %d/%d" % (n, len(todo)))
            append_jsonl(out, batch)

    rows = {r["vid"]: r for r in read_jsonl(out)}
    gone = sum(1 for r in rows.values() if not r.get("ok"))
    print("\nMeta: %d videos, %d deleted/private (%.0f%%) → %s" % (
        len(rows), gone, 100.0 * gone / max(1, len(rows)), out))


if __name__ == "__main__":
    main()
