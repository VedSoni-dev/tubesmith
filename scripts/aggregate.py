#!/usr/bin/env python3
"""First cut: keep videos recommended by enough different people, in enough different months.

Karpathy's rule: ≥3 different people, with real commentary, in ≥3 different months.
Keeps up to N mentions per video, spread across as many different people as possible.

Reads  data/mentions.*.jsonl (+ custom files from config), data/channel_videos.jsonl, seeds
Writes data/candidates.jsonl: {vid, people, months, mentions:[...], channel_item, seed}

  python3 scripts/aggregate.py --config tube.config.json
  python3 scripts/aggregate.py --config tube.config.json --min-people 2   # try a looser bar
"""
import argparse
import glob
import os
from collections import defaultdict

from common import DATA, get, load_config, read_jsonl, video_ids, write_jsonl


def pick_mentions(ms, n):
    """Round-robin across authors (most substantive comment first) so one fan can't dominate."""
    by_author = defaultdict(list)
    for m in sorted(ms, key=lambda m: -len(m["text"])):
        by_author[m["author"]].append(m)
    queues = sorted(by_author.values(), key=lambda q: q[0]["ts"])
    out = []
    while len(out) < n and any(queues):
        for q in queues:
            if q and len(out) < n:
                out.append(q.pop(0))
    return sorted(out, key=lambda m: m["ts"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="tube.config.json")
    ap.add_argument("--min-people", type=int)
    ap.add_argument("--min-months", type=int)
    args = ap.parse_args()
    cfg = load_config(args.config)

    # thresholds per source
    th = {}
    if get(cfg, "sources.hn.enabled", False):
        th["hn"] = (get(cfg, "sources.hn.min_people", 3), get(cfg, "sources.hn.min_months", 3))
    files = set(glob.glob(os.path.join(DATA, "mentions.*.jsonl")))
    if get(cfg, "sources.custom.enabled", False):
        files.update(get(cfg, "sources.custom.files", []) or [])
    default_th = (get(cfg, "sources.custom.min_people", 2), get(cfg, "sources.custom.min_months", 2))
    max_m = int(get(cfg, "sources.hn.max_mentions", 20))

    mentions = defaultdict(list)
    for path in sorted(files):
        for r in read_jsonl(path):
            mentions[r["vid"]].append(r)

    seeds = set()
    for s in get(cfg, "sources.seeds", []) or []:
        seeds.update(video_ids(s) or ([s] if len(s) == 11 else []))

    chan = {r["vid"]: r for r in read_jsonl(os.path.join(DATA, "channel_videos.jsonl"))
            if get(cfg, "sources.channels.enabled", False)}

    out, hist = [], defaultdict(int)
    for vid, ms in mentions.items():
        ok = False
        by_src = defaultdict(list)
        for m in ms:
            by_src[m["source"]].append(m)
        for src, sms in by_src.items():
            mp, mm = th.get(src, default_th)
            if args.min_people is not None:
                mp = args.min_people
            if args.min_months is not None:
                mm = args.min_months
            people = len({m["author"] for m in sms})
            months = len({m["month"] for m in sms})
            hist[min(people, 10)] += 1
            if people >= mp and months >= mm:
                ok = True
        if ok or vid in seeds or vid in chan:
            out.append({
                "vid": vid,
                "people": len({m["author"] for m in ms}),
                "months": len({m["month"] for m in ms}),
                "mentions": pick_mentions(ms, max_m),
                "channel_item": chan.get(vid),
                "seed": vid in seeds,
            })
    have = {c["vid"] for c in out}
    for vid in list(seeds) + list(chan):
        if vid not in have:
            have.add(vid)
            out.append({"vid": vid, "people": 0, "months": 0, "mentions": [],
                        "channel_item": chan.get(vid), "seed": vid in seeds})

    out.sort(key=lambda c: (-c["months"], -c["people"]))
    path = os.path.join(DATA, "candidates.jsonl")
    write_jsonl(path, out)

    print("Mentions: %d across %d distinct videos" % (sum(len(v) for v in mentions.values()), len(mentions)))
    if hist:
        print("Videos by # different people (capped at 10+): " +
              " ".join("%d:%d" % (k, hist[k]) for k in sorted(hist)))
    print("Candidates: %d (community %d · channels %d · seeds %d) → %s" % (
        len(out), sum(1 for c in out if c["mentions"]), len(chan), len(seeds), path))
    if len(out) < 200:
        print("Tip: that's a small tube. Try --min-people 2 or an earlier `since`.")
    elif len(out) > 20000:
        print("Tip: that's a lot to label. Try a stricter --min-people / --min-months.")


if __name__ == "__main__":
    main()
