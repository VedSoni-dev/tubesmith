---
name: tubesmith
description: Build your own filtered YouTube, the way Andrej Karpathy built HackerTube. Interviews you (yes/no + open-ended) about what you want more of, what you never want to see, whose taste you trust, and how thumbnails/titles should look, then builds a working site with a data pipeline, AI curation, de-clickbaited thumbnails and titles, and a local-first player. Use when someone says "make my own YouTube", "filter YouTube", "HackerTube for X", "no more slop in my feed", or runs /tubesmith.
---

# Tubesmith: forge your own YouTube

On 31 Oct 2026 Andrej Karpathy got fed up with YouTube's "wall of slop." In about two hours of talking to Claude he built **HackerTube** (hackertube.org), a YouTube made only of videos that Hacker News commenters actually recommended. He wrote it up on his blog (karpathy.bearblog.dev/hacker-tube) and on HN (item 50319510). This skill runs the same process for anyone, with *their* sources of trust and *their* rules.

The insight to keep in mind (and tell the user once): **the website is the easy part ("like 3 min"); the data pipeline is the product.** YouTube's ranking is trained on everyone's clicks, and you are a rounding error in that signal. Here you swap in a signal you actually trust.

Read `references/karpathy-process.md` before you start. It is the method, step by step. Read the other references when the step that needs them comes up.

## How to run this skill

You are the builder. The user talks; you do everything else. Keep the momentum Karpathy had: short questions, fast defaults, something working quickly. Never make them read code.

Work in a new folder: `./<their-tube-name>/` (ask for a name in Round 1, or default to `mytube`). Copy `scripts/` and `template/` from this skill's own directory (the folder containing this SKILL.md) into it, and copy `config.example.json` to start `tube.config.json`. All pipeline files live in `data/` and the built site in `site/`. Run every script from inside that folder.

**Get to a first working site fast**, then go deep. After the interview, do a quick pass first: HN `--since` one year back (or their channels), oEmbed metadata, `rank.py` with no labels. They'll see their tube in ~2 minutes. Then run the full history, the API metadata and the judge. Seeing it early keeps them engaged and catches wrong answers cheaply.

### Phase 1: Interview (≈3 minutes)

Use `references/interview.md`. It has the exact questions, options and defaults. Rules:

- Use the **AskUserQuestion** tool for multiple-choice and yes/no rounds (≤4 questions per call). In agents without that tool, ask in chat as a numbered list with the default marked, so they can just reply "defaults".
- Ask open-ended questions in plain chat, **one message, all at once**, with an example answer so they know the shape.
- Recommended option first, marked "(Recommended)". The Karpathy setting is usually the recommendation.
- Don't ask what you can default. If they say "just do what Karpathy did," take every Karpathy default and skip to Phase 2.

At the end, write `tube.config.json` (schema in `config.example.json`) and show a **one-screen summary**: sources, rules, look, where it runs, what it costs. Get a "go" before Phase 3. This is the moment to catch "wait, I didn't mean that."

### Phase 2: Keys and accounts (only what their answers need)

- **YouTube Data API key**: only if they want durations, view counts, Shorts filtering, or search-by-topic sources. Walk them through `references/sources.md#youtube-data-api-key` (5 minutes, free). You cannot do this step for them. Have them `export YOUTUBE_API_KEY=...` in their shell. Never ask them to paste it into chat or a file you commit. Without a key, `yt_meta.py --mode oembed` still gets titles, channels and deleted-video detection.
- **LLM for judging**: either *you* do the labeling with subagents (no extra key, works in Claude Code; this is what Karpathy did with a Workflow of Sonnet agents) or `scripts/judge.py` runs it through any OpenAI-compatible API. See `references/judging.md` for the trade-off and the cost estimate to show them first.

### Phase 3: Build the pipeline (the real work)

Run it as a sequence of small, resumable steps. Every script writes JSONL and skips work it has already done, so a crash or Ctrl-C costs nothing.

1. **Collect** mentions/videos from each source they chose (`references/sources.md`):
   - Hacker News → `python3 scripts/hn_collect.py --config tube.config.json`
   - Their channels / subscriptions → `python3 scripts/channels_collect.py --config tube.config.json`
   - Reddit, Lobsters, a Discord export, a newsletter archive, bookmarks: write a small collector that emits the same `mentions.jsonl` schema (documented in `references/sources.md`). Write it, run it, show 5 sample rows.
2. **First cut** → `python3 scripts/aggregate.py --config tube.config.json`. This applies the "≥N different people, in ≥M different months, with real text" rule. Print the count. If it's under ~200 or over ~20k, propose a threshold change and rerun before spending any LLM money.
3. **Metadata** → `python3 scripts/yt_meta.py --config tube.config.json` (API mode if the key is set, otherwise oEmbed).
4. **Judge** → AI labeling per `references/judging.md`: is each mention a real recommendation, plus a card per video (summary, why it's here, type, level, shelf life, topics, clickbait score, plain title), all checked against the user's own "more of / never" rules.
   - Pilot on 20 videos first. Show the user 5 cards, including at least one dropped and one kept. Ask "does this match your taste?" Tune the rules, then run the rest.
5. **Rank + build** → `python3 scripts/rank.py --config tube.config.json`. It applies the rules, scores, and writes `site/videos.json` + the site template.
6. **Run** → `python3 -m http.server 8787 -d site` and open it. Click through it yourself (home, a topic, search, a video, settings, like/watch later) before you show them.

### Phase 4: Make it theirs (look and feel)

Walk through the display answers live. They can flip these in the site's Settings panel too, but the config sets the defaults:

- **Thumbnails** (`references/thumbnails-and-titles.md`): `mid` = YouTube's auto frame from the middle of the video (Karpathy's choice, kills the "HOLY SHIT face"), `frames` = scrub through 3 auto frames on hover, `original`, `blur` until hover, or `none` (text cards).
- **Titles**: `original`, `plain` (AI rewrite that says what the video *is*; the original is always one hover away), or `both`.
- Shelves: Classics, Hidden gems, Recently recommended, **Longs** (everything over an hour, where Shorts would be), unexplored topics.
- Optional finite feed: show N videos, then stop. "That's the feed."

After every change, rebuild (`rank.py`) and reload. Fast loops are the point.

### Phase 5: Ship it (only if they want it online)

- **Local only** (the default): done. Give them the one command to start it again.
- **Static host** (Vercel / Netlify / GitHub Pages / Cloudflare Pages): `site/` is plain static files. Deploy it with their CLI. **Ask before any deploy or push.**
- **Their own VPS** (what Karpathy did): they rent the box and point DNS; you handle the rest over SSH ("update, deploy, secure, harden and optimize"). Ask before every outward step.
- **Keep it fresh**: offer a weekly cron/launchd job that reruns collect → aggregate → meta → judge (new items only) → rank.

Before deploying publicly, tell them about the YouTube API terms in `references/sources.md#terms` (attribution, don't redistribute raw metadata, refresh periodically).

## Hard rules

- **Their taste, not yours.** Rules come from their answers. Don't sneak in your own idea of "good."
- **Keys stay secret.** Read keys from env vars only. Never echo them, write them into the repo, or put them in `site/`.
- **No YouTube look-alike.** Own name, own logo, own colors. Karpathy changed HackerTube's logo when people said it looked too much like YouTube's. Never use YouTube's logo or red play-button mark.
- **Play videos through YouTube's embed** (`youtube-nocookie.com`). Never download or re-host videos. Creators still get the view.
- **Don't hide that titles were rewritten.** A plain title always shows the original on hover and on the watch page.
- **Respect sources.** Use public APIs and be polite about rate limits (the scripts sleep between requests). Credit the communities whose recommendations power the feed, on the About panel.
- **Ask before outward actions**: deploying, pushing to GitHub, buying a domain, creating cloud resources.
