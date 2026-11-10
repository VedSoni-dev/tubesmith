#!/usr/bin/env python3
"""Collect every Hacker News comment that links a YouTube video, via the public Algolia HN API.

Writes data/mentions.hn.jsonl, one row per (comment, video):
  {vid, source, author, ts, month, text, context, url}

No key needed. Resumable: rerun and it continues where it stopped.
Karpathy used the full HuggingFace dump (open-index/hacker-news). Algolia gives the same
comments without downloading tens of GB, at about 1 request per 1,000 comments.

  python3 scripts/hn_collect.py --config tube.config.json
  python3 scripts/hn_collect.py --config tube.config.json --since 2025-01-01   # quick test
"""
import argparse
import calendar
import json
import os
import time
import urllib.parse
from datetime import datetime, timezone

from common import (DATA, append_jsonl, get, html_to_text, http_json, load_config,
                    own_text_len, progress, read_jsonl, video_ids)

API = "https://hn.algolia.com/api/v1/search_by_date"
QUERIES = ["youtube.com", "youtu.be"]


def ts_of(date_str):
    return calendar.timegm(datetime.strptime(date_str, "%Y-%m-%d").timetuple())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="tube.config.json")
    ap.add_argument("--since", help="YYYY-MM-DD (overrides config)")
    ap.add_argument("--max-pages", type=int, default=0, help="stop early (testing)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    since = args.since or get(cfg, "sources.hn.since", "2007-01-01")
    since_ts = ts_of(since)
    min_text = int(get(cfg, "sources.hn.min_text_chars", 100))

    out = os.path.join(DATA, "mentions.hn.jsonl")
    state_path = os.path.join(DATA, "hn_state.json")
    state = json.load(open(state_path)) if os.path.exists(state_path) else {}
    seen = {(r["url"], r["vid"]) for r in read_jsonl(out)}

    pages = 0
    for q in QUERIES:
        st = state.get(q, {})
        if st.get("done") and st.get("since") == since:
            continue
        cursor = st.get("cursor") or int(time.time()) + 60
        kept = 0
        while True:
            params = {
                "query": q,
                "tags": "comment",
                "hitsPerPage": 1000,
                "numericFilters": "created_at_i<%d,created_at_i>=%d" % (cursor, since_ts),
            }
            data = http_json(API + "?" + urllib.parse.urlencode(params))
            hits = data.get("hits", [])
            rows = []
            for h in hits:
                raw = h.get("comment_text") or ""
                vids = video_ids(raw)
                if not vids:
                    continue
                text = html_to_text(raw)
                if own_text_len(text) < min_text:
                    continue
                url = "https://news.ycombinator.com/item?id=%s" % h["objectID"]
                for v in vids:
                    if (url, v) in seen:
                        continue
                    seen.add((url, v))
                    ts = h.get("created_at_i") or 0
                    rows.append({
                        "vid": v, "source": "hn", "author": h.get("author") or "?",
                        "ts": ts,
                        "month": datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m"),
                        "text": text[:2000],
                        "context": h.get("story_title") or "",
                        "url": url,
                    })
            append_jsonl(out, rows)
            kept += len(rows)
            pages += 1
            if not hits:
                state[q] = {"cursor": cursor, "done": True, "since": since}
                json.dump(state, open(state_path, "w"))
                break
            cursor = min(h["created_at_i"] for h in hits)
            state[q] = {"cursor": cursor, "done": False, "since": since}
            json.dump(state, open(state_path, "w"))
            day = datetime.fromtimestamp(cursor, timezone.utc).strftime("%Y-%m-%d")
            progress("[%s] back to %s · %d mentions kept" % (q, day, kept))
            if len(hits) < 1000:
                state[q]["done"] = True
                json.dump(state, open(state_path, "w"))
                break
            if args.max_pages and pages >= args.max_pages:
                break
            time.sleep(0.4)  # Algolia allows ~10k req/h; stay far below it
        if args.max_pages and pages >= args.max_pages:
            break

    total = read_jsonl(out)
    print("\nHN: %d mentions of %d distinct videos in %s" % (
        len(total), len({r["vid"] for r in total}), out))


if __name__ == "__main__":
    main()
