#!/usr/bin/env python3
"""AI judging: label each mention (real recommendation or not) and write one card per video,
checked against the user's own taste and rules. This is the step that turns links into a feed.

Two ways to run it (see references/judging.md):

  # A) Your coding agent labels the batches itself (no extra key). Emit batch files, then have
  #    subagents each take a batch and write data/judge/batch_NNNN.out.jsonl.
  python3 scripts/judge.py --config tube.config.json --emit

  # B) Any OpenAI-compatible API. Set TUBE_LLM_BASE_URL / TUBE_LLM_API_KEY / TUBE_LLM_MODEL,
  #    or PUBLIK_API_KEY or OPENAI_API_KEY.
  python3 scripts/judge.py --config tube.config.json --run --limit 20      # pilot first
  python3 scripts/judge.py --config tube.config.json --run

  python3 scripts/judge.py --config tube.config.json --status
"""
import argparse
import glob
import json
import os
import re
import sys
import threading
import time
import urllib.error
from concurrent.futures import ThreadPoolExecutor

from common import DATA, append_jsonl, get, http_json, load_config, read_jsonl

JUDGE_DIR = os.path.join(DATA, "judge")
LABELS = ("strong_rec", "rec", "reference", "joke", "critical", "spam")
TYPES = ("talk", "lecture", "documentary", "tutorial", "interview", "demo", "essay",
         "explainer", "music", "performance", "news", "vlog", "other")


def instructions(cfg):
    t = cfg.get("taste", {})
    r = cfg.get("rules", {})
    examples = ", ".join(t.get("examples") or []) or "(none given)"
    return f"""You curate a personal video feed called "{cfg.get('name', 'my tube')}".
The owner's taste, in their words:
- MORE OF: {t.get('more_of') or '(anything genuinely good)'}
- NEVER: {t.get('never') or '(nothing specific)'}
- Gold-standard examples: {examples}

For each video you get its YouTube title/channel/description (when known) and what people said
when they linked it (comment text + the thread title it was posted under). Return one JSON card
per video.

1. Label EVERY mention (by its index i):
   strong_rec = enthusiastic, specific recommendation ("best talk I've seen on X", "must watch")
   rec        = recommends it or clearly finds it worth watching
   reference  = cites it as a source or example, no opinion on quality
   joke       = meme, pun, rickroll, sarcasm
   critical   = says it's wrong, bad, misleading, or outdated
   spam       = self-promotion with no context, or unrelated
   Read the thread title for context: a link under "Ask HN: best lectures?" is likely a rec.
   For each mention also give `why` (≤15 words, what the person valued) and `quote`: a short phrase
   copied EXACTLY, character for character, from that comment, that best shows their opinion
   (≤25 words, "" if none). Quotes are checked against the source; paraphrases get discarded.
2. Write the card: `summary` (1–2 plain sentences: what the video is), `why_here` (≤20 words, why
   these people recommend it), `type` (one of {', '.join(TYPES)}), `level` (intro|intermediate|deep),
   `shelf_life` (evergreen|dated|news), `topics` (1–4 short lowercase topics, reuse common names
   like "machine learning", "history", "woodworking"), `clickbait` (0 = plain honest title ...
   3 = rage/curiosity-gap bait, shock words, ALL CAPS), `plain_title` (a calm, factual title of
   ≤70 chars saying what the video is; keep the original if it's already plain).
3. `keep`: false if the video falls under NEVER, or is clearly not what the owner wants, or is
   spam/joke-only. Otherwise true. If unsure, keep it: the community already vouched for it.
   `drop_reason`: ≤8 words when keep is false, else "".

Output ONLY JSON: {{"cards": [{{"vid": "...", "keep": true, "drop_reason": "", "mentions":
[{{"i": 0, "label": "rec", "why": "...", "quote": "..."}}], "summary": "...", "why_here": "...",
"type": "talk", "level": "deep", "shelf_life": "evergreen", "topics": ["..."], "clickbait": 0,
"plain_title": "..."}}]}}"""


def video_input(c, meta):
    m = meta.get(c["vid"], {})
    ch = c.get("channel_item") or {}
    d = {"vid": c["vid"],
         "title": m.get("title") or ch.get("title") or "(unknown)",
         "channel": m.get("channel") or ch.get("channel") or "(unknown)"}
    if m.get("duration_s"):
        d["minutes"] = round(m["duration_s"] / 60)
    if m.get("published") or ch.get("published"):
        d["published"] = (m.get("published") or ch.get("published"))[:10]
    desc = m.get("description") or ch.get("description") or ""
    if desc:
        d["description"] = desc[:300]
    d["mentions"] = [{"i": i, "thread": x.get("context", ""), "date": x.get("month", ""),
                      "text": x["text"][:700]} for i, x in enumerate(c.get("mentions", []))]
    if not d["mentions"]:
        d["note"] = "From a channel the owner subscribes to (no community mentions)."
    return d


def load(cfg):
    meta = {r["vid"]: r for r in read_jsonl(os.path.join(DATA, "meta.jsonl"))}
    cands = read_jsonl(os.path.join(DATA, "candidates.jsonl"))
    cands = [c for c in cands if meta.get(c["vid"], {}).get("ok", True)]  # skip deleted
    return cands, meta


def done_vids():
    done = {r["vid"] for r in read_jsonl(os.path.join(DATA, "labels.jsonl"))}
    for p in glob.glob(os.path.join(JUDGE_DIR, "*.out.jsonl")):
        done.update(r.get("vid") for r in read_jsonl(p))
    return done


def llm_settings():
    e = os.environ
    if e.get("TUBE_LLM_API_KEY") or e.get("TUBE_LLM_BASE_URL"):
        return (e.get("TUBE_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
                e.get("TUBE_LLM_API_KEY", ""), e.get("TUBE_LLM_MODEL", "gpt-4o-mini"))
    if e.get("PUBLIK_API_KEY"):
        return ("https://publikhq.com/api/v1", e["PUBLIK_API_KEY"], e.get("TUBE_LLM_MODEL", "publik-balanced"))
    if e.get("OPENAI_API_KEY"):
        return ("https://api.openai.com/v1", e["OPENAI_API_KEY"], e.get("TUBE_LLM_MODEL", "gpt-4o-mini"))
    raise SystemExit("No LLM key. Set TUBE_LLM_BASE_URL + TUBE_LLM_API_KEY (+ TUBE_LLM_MODEL), "
                     "or PUBLIK_API_KEY, or OPENAI_API_KEY. Or use --emit and let your agent label.")


def parse_cards(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1]).get("cards", [])


def call(base, key, model, system, batch):
    body = {"model": model, "temperature": 0.2, "messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps({"videos": batch}, ensure_ascii=False)}]}
    for attempt in range(3):
        try:
            d = http_json(base + "/chat/completions", headers={"Authorization": "Bearer " + key},
                          data=body, timeout=180)
            return parse_cards(d["choices"][0]["message"]["content"])
        except urllib.error.HTTPError as e:
            if e.code == 402:
                msg = e.read().decode("utf-8", "replace")[:300]
                raise SystemExit("\nOut of credit (402). " + msg)
            if e.code in (401, 403):
                raise SystemExit("\nLLM key rejected (%s). Check the key and base URL." % e.code)
            if attempt == 2:
                raise
        except (ValueError, KeyError):
            if attempt == 2:
                return []  # unparseable; those videos stay undone and retry next run
        time.sleep(3 * (attempt + 1))
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="tube.config.json")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--emit", action="store_true", help="write batch files for agent labeling")
    g.add_argument("--run", action="store_true", help="label via an OpenAI-compatible API")
    g.add_argument("--status", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="only the first N undone videos (pilot)")
    ap.add_argument("--per-call", type=int, default=8)
    args = ap.parse_args()
    cfg = load_config(args.config)
    cands, meta = load(cfg)
    done = done_vids()
    todo = [c for c in cands if c["vid"] not in done]
    if args.limit:
        todo = todo[:args.limit]

    if args.status:
        print("Judged %d / %d candidates (%d left)" % (len(cands) - len([c for c in cands if c["vid"] not in done]),
                                                       len(cands), len([c for c in cands if c["vid"] not in done])))
        return

    system = instructions(cfg)
    if args.emit:
        os.makedirs(JUDGE_DIR, exist_ok=True)
        with open(os.path.join(JUDGE_DIR, "INSTRUCTIONS.md"), "w") as f:
            f.write(system + "\n\nWrite one card per line (JSON Lines, no wrapper object) to the "
                    ".out.jsonl file named next to your batch file.\n")
        size = int(get(cfg, "judge.batch_size", 25))
        batch_files = glob.glob(os.path.join(JUDGE_DIR, "batch_*.json"))
        emitted = set()
        for p in batch_files:  # don't emit a video twice while its batch is still pending
            emitted.update(v["vid"] for v in json.load(open(p))["videos"])
        todo = [c for c in todo if c["vid"] not in emitted]
        existing = len(batch_files)
        n = 0
        for i in range(0, len(todo), size):
            n += 1
            name = os.path.join(JUDGE_DIR, "batch_%04d.json" % (existing + n))
            with open(name, "w") as f:
                json.dump({"out": name.replace(".json", ".out.jsonl"),
                           "videos": [video_input(c, meta) for c in todo[i:i + size]]},
                          f, ensure_ascii=False, indent=1)
        print("Wrote %d batch files (%d videos) to %s/ with INSTRUCTIONS.md" % (n, len(todo), JUDGE_DIR))
        print("Agent: give each subagent INSTRUCTIONS.md + one batch file; it writes the .out.jsonl.")
        return

    base, key, model = llm_settings()
    out = os.path.join(DATA, "labels.jsonl")
    print("Judging %d videos with %s at %s, %d per call" % (len(todo), model, base, args.per_call))
    lock = threading.Lock()
    count = [0]
    batches = [todo[i:i + args.per_call] for i in range(0, len(todo), args.per_call)]

    def work(b):
        cards = call(base, key, model, system, [video_input(c, meta) for c in b])
        wanted = {c["vid"] for c in b}
        cards = [c for c in cards if isinstance(c, dict) and c.get("vid") in wanted]
        with lock:
            append_jsonl(out, cards)
            count[0] += len(cards)
            sys.stderr.write("\r%d/%d judged" % (count[0], len(todo)))
            sys.stderr.flush()

    with ThreadPoolExecutor(int(get(cfg, "judge.concurrency", 8))) as pool:
        list(pool.map(work, batches))
    print("\nDone → %s. Rerun to retry anything that failed." % out)


if __name__ == "__main__":
    main()
