#!/usr/bin/env python3
"""Pull recent uploads from channels the user trusts, through YouTube's public RSS feeds (no key).

Channel list comes from tube.config.json `sources.channels.list` (@handles, channel URLs or UC… ids)
and/or a Google Takeout `subscriptions.csv` (YouTube and YouTube Music → subscriptions).

Writes data/channel_videos.jsonl:
  {vid, source:"channel", title, channel, channel_id, published, description, is_short}

  python3 scripts/channels_collect.py --config tube.config.json
  python3 scripts/channels_collect.py --config tube.config.json --subscriptions-csv ~/Downloads/subscriptions.csv
"""
import argparse
import csv
import os
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET

from common import DATA, get, http_json, http_text, load_config, progress, write_jsonl

NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015",
      "media": "http://search.yahoo.com/mrss/"}
UC_RE = re.compile(r"(UC[A-Za-z0-9_-]{22})")


def resolve(entry, api_key):
    entry = entry.strip()
    m = re.fullmatch(r"(?:https?://(?:www\.)?youtube\.com/channel/)?(UC[A-Za-z0-9_-]{22})/?", entry)
    if m:
        return m.group(1)
    handle = entry
    m = re.search(r"youtube\.com/(@[^/?#]+)", entry)
    if m:
        handle = m.group(1)
    if not handle.startswith("@"):
        handle = "@" + handle
    if api_key:
        q = urllib.parse.urlencode({"part": "id", "forHandle": handle, "key": api_key})
        items = http_json("https://www.googleapis.com/youtube/v3/channels?" + q).get("items") or []
        if items:
            return items[0]["id"]
    page = http_text("https://www.youtube.com/" + urllib.parse.quote(handle))
    m = (re.search(r'"externalId":"(UC[A-Za-z0-9_-]{22})"', page)
         or re.search(r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[A-Za-z0-9_-]{22})"', page))
    return m.group(1) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="tube.config.json")
    ap.add_argument("--subscriptions-csv", help="Google Takeout subscriptions.csv")
    args = ap.parse_args()
    cfg = load_config(args.config)
    api_key = os.environ.get(get(cfg, "youtube.api_key_env", "YOUTUBE_API_KEY") or "")
    per = int(get(cfg, "sources.channels.per_channel", 15))

    entries = list(get(cfg, "sources.channels.list", []) or [])
    if args.subscriptions_csv:
        with open(os.path.expanduser(args.subscriptions_csv), newline="") as f:
            for row in csv.DictReader(f):
                cid = row.get("Channel Id") or row.get("Channel ID") or ""
                if cid:
                    entries.append(cid.strip())

    rows, failed = [], []
    for i, e in enumerate(entries, 1):
        progress("channel %d/%d %s" % (i, len(entries), e))
        try:
            cid = resolve(e, api_key)
            if not cid:
                failed.append(e)
                continue
            xml = http_text("https://www.youtube.com/feeds/videos.xml?channel_id=" + cid)
            root = ET.fromstring(xml)
            for ent in root.findall("a:entry", NS)[:per]:
                vid = ent.findtext("yt:videoId", namespaces=NS)
                link = ent.find("a:link", NS)
                href = link.get("href") if link is not None else ""
                rows.append({
                    "vid": vid, "source": "channel",
                    "title": ent.findtext("a:title", namespaces=NS),
                    "channel": ent.findtext("a:author/a:name", namespaces=NS),
                    "channel_id": cid,
                    "published": ent.findtext("a:published", namespaces=NS),
                    "description": (ent.findtext("media:group/media:description", namespaces=NS) or "")[:600],
                    "is_short": "/shorts/" in href,
                })
        except Exception as ex:  # one broken channel should not stop the rest
            failed.append("%s (%s)" % (e, ex))
        time.sleep(0.3)

    uniq = {}
    for r in rows:  # the same channel can be listed twice (handle + id)
        uniq.setdefault(r["vid"], r)
    rows = list(uniq.values())
    out = os.path.join(DATA, "channel_videos.jsonl")
    write_jsonl(out, rows)
    print("\nChannels: %d videos from %d channels → %s" % (len(rows), len(entries) - len(failed), out))
    if failed:
        print("Could not resolve: " + "; ".join(failed))


if __name__ == "__main__":
    main()
