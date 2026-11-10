#!/usr/bin/env python3
"""Apply the user's rules, score, and build the site.

Score (Karpathy's): months with a recommendation + 0.5 × months with a strong recommendation.
Steady recommendations over years beat one viral spike.

Reads  data/candidates.jsonl, data/meta.jsonl, data/labels.jsonl, data/judge/*.out.jsonl
Writes site/videos.json (+ copies template/ into site/ the first time), data/dropped.jsonl

Works before judging too (every mention counts as a rec), so you can preview the site early.

  python3 scripts/rank.py --config tube.config.json
  python3 scripts/rank.py --config tube.config.json --refresh-template   # overwrite site/ html/js/css
"""
import argparse
import glob
import json
import math
import os
import re
import shutil
from collections import Counter
from datetime import datetime, timezone

from common import DATA, get, load_config, read_jsonl

HERE = os.path.dirname(os.path.abspath(__file__))


def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="tube.config.json")
    ap.add_argument("--site", default="site")
    ap.add_argument("--template", default=None, help="template dir (default: ../template next to scripts/)")
    ap.add_argument("--refresh-template", action="store_true")
    args = ap.parse_args()
    cfg = load_config(args.config)
    rules = cfg.get("rules", {})
    taste = cfg.get("taste", {})

    cands = read_jsonl(os.path.join(DATA, "candidates.jsonl"))
    meta = {r["vid"]: r for r in read_jsonl(os.path.join(DATA, "meta.jsonl"))}
    labels = {}
    for p in [os.path.join(DATA, "labels.jsonl")] + sorted(glob.glob(os.path.join(DATA, "judge", "*.out.jsonl"))):
        for r in read_jsonl(p):
            if isinstance(r, dict) and r.get("vid"):
                labels[r["vid"]] = r
    judged = bool(labels)
    if not judged:
        print("No labels yet: previewing with every mention counted as a recommendation.")

    min_rec_people = int(get(cfg, "rules.min_rec_people", 2))
    block_ch = {norm(x) for x in taste.get("block_channels", []) or []}
    block_kw = [norm(x) for x in taste.get("block_keywords", []) or [] if x.strip()]
    min_s = 60 * float(rules.get("min_minutes") or 0)
    max_s = 60 * float(rules.get("max_minutes") or 0)

    videos, dropped, why = [], [], Counter()
    for c in cands:
        vid = c["vid"]
        m = meta.get(vid, {})
        ch = c.get("channel_item") or {}
        lab = labels.get(vid)

        def drop(reason):
            why[reason] += 1
            dropped.append({"vid": vid, "title": m.get("title") or ch.get("title"), "reason": reason})

        if m and not m.get("ok", True):
            drop("deleted or private")
            continue
        if m.get("embeddable") is False:
            drop("embedding disabled")
            continue
        if judged and lab is None:
            drop("not judged yet")
            continue

        # mention labels → recommendation months
        ml = {x.get("i"): x for x in (lab or {}).get("mentions", []) if isinstance(x, dict)}
        rec_people, rec_months, strong_months, quotes = set(), set(), set(), []
        for i, mn in enumerate(c.get("mentions", [])):
            label = ml.get(i, {}).get("label", "rec" if not judged else "reference")
            if label in ("rec", "strong_rec"):
                rec_people.add(mn["author"])
                rec_months.add(mn["month"])
                if label == "strong_rec":
                    strong_months.add(mn["month"])
                q = ml.get(i, {}).get("quote") or ""
                if q and norm(q) in norm(mn["text"]):  # keep only verbatim quotes
                    quotes.append({"q": q.strip(), "by": mn["author"], "url": mn.get("url"),
                                   "d": mn.get("month"), "why": ml.get(i, {}).get("why", ""),
                                   "s": label == "strong_rec"})
        community = bool(c.get("mentions"))
        exempt = c.get("seed") or c.get("channel_item") or (not community)
        if community and not exempt and len(rec_people) < min_rec_people:
            drop("not enough real recommendations")
            continue
        if lab and lab.get("keep") is False and not c.get("seed"):
            drop("taste: " + (lab.get("drop_reason") or "doesn't fit"))
            continue

        title = m.get("title") or ch.get("title") or ""
        channel = m.get("channel") or ch.get("channel") or ""
        dur = m.get("duration_s")
        lab = lab or {}
        hay = norm(" ".join([title, channel, m.get("description") or ch.get("description") or "",
                             lab.get("summary", ""), " ".join(lab.get("topics", []))]))
        if norm(channel) in block_ch or (m.get("channel_id") or ch.get("channel_id")) in block_ch:
            drop("blocked channel")
            continue
        hit = next((k for k in block_kw if k in hay), None)
        if hit:
            drop("blocked keyword")
            continue
        if rules.get("hide_shorts") and (ch.get("is_short") or (dur is not None and dur <= 60)):
            drop("short")
            continue
        if dur is not None and min_s and dur < min_s:
            drop("too short")
            continue
        if dur is not None and max_s and dur > max_s:
            drop("too long")
            continue
        if rules.get("drop_clickbait") and int(lab.get("clickbait", 0) or 0) > int(rules.get("clickbait_max", 2)):
            drop("clickbait")
            continue
        if rules.get("hide_stale_news") and lab.get("shelf_life") == "news":
            drop("stale news")
            continue

        if community:
            score = len(rec_months) + 0.5 * len(strong_months)
        else:  # channel uploads: newer first, decays over ~2 months
            pub = ch.get("published") or m.get("published")
            age = 999
            if pub:
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(pub.replace("Z", "+00:00"))).days
            score = 1 + 2 * math.exp(-age / 60.0)
        if c.get("seed"):
            score += 1

        last = max((mn["month"] for mn in c.get("mentions", [])), default=None)
        videos.append({
            "id": vid, "t": title, "pt": lab.get("plain_title") or "", "ch": channel,
            "dur": dur, "pub": (m.get("published") or ch.get("published") or "")[:10] or None,
            "views": m.get("views"), "likes": m.get("likes"),
            "sum": lab.get("summary", ""), "why": lab.get("why_here", ""),
            "type": lab.get("type", ""), "lvl": lab.get("level", ""), "life": lab.get("shelf_life", ""),
            "top": lab.get("topics", []), "cb": lab.get("clickbait"),
            "sc": round(score, 2), "ppl": len(rec_people), "mo": len(rec_months),
            "last": last, "q": quotes[:6], "src": "community" if community else "channel",
            "seed": bool(c.get("seed")),
        })

    # hidden gems: well-recommended, few YouTube views (needs API metadata)
    with_views = sorted(v["views"] for v in videos if v["views"])
    if len(with_views) > 20:
        cut = with_views[len(with_views) // 4]
        med = sorted(v["sc"] for v in videos)[len(videos) // 2]
        for v in videos:
            v["gem"] = bool(v["views"] and v["views"] <= cut and v["sc"] >= med)

    videos.sort(key=lambda v: -v["sc"])
    site = args.site
    os.makedirs(site, exist_ok=True)
    tpl = args.template or os.path.join(os.path.dirname(HERE), "template")
    if not os.path.isdir(tpl):
        tpl = os.path.join(HERE, "..", "template")
    for fn in os.listdir(tpl) if os.path.isdir(tpl) else []:
        dst = os.path.join(site, fn)
        if args.refresh_template or not os.path.exists(dst):
            shutil.copy(os.path.join(tpl, fn), dst)

    payload = {
        "meta": {"name": cfg.get("name", "My Tube"), "tagline": cfg.get("tagline", ""),
                 "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                 "display": cfg.get("display", {}), "judged": judged,
                 "counts": {"videos": len(videos), "dropped": len(dropped)}},
        "videos": videos,
    }
    with open(os.path.join(site, "videos.json"), "w") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(DATA, "dropped.jsonl"), "w") as f:
        for d in dropped:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print("Site: %d videos → %s/videos.json" % (len(videos), site))
    if why:
        print("Dropped %d: %s" % (len(dropped), ", ".join("%s %d" % kv for kv in why.most_common())))
    print("Run it:  python3 -m http.server 8787 -d %s   →  http://localhost:8787" % site)


if __name__ == "__main__":
    main()
