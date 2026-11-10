# tubesmith

**Build your own filtered YouTube, the way Andrej Karpathy built [HackerTube](https://hackertube.org).**

Karpathy got tired of YouTube's slop. In about two hours of talking to Claude, he built a YouTube made only of videos Hacker News commenters actually recommended: AI-labeled, ranked by years of steady recommendations, with honest mid-video thumbnails instead of clickbait faces ([blog post](https://karpathy.bearblog.dev/hacker-tube/), [HN thread](https://news.ycombinator.com/item?id=50319510)).

tubesmith is an agent skill that runs that same process for **you**, with your sources of trust and your rules. Your coding agent asks you a few yes/no and open-ended questions, then builds the whole thing:

- **Whose taste?** Hacker News comments, your own subscriptions, a subreddit, Lobsters, a Discord, or a seed list of videos you love
- **More of / never:** in your own words. An LLM judges every video against them
- **Feed rules:** no Shorts, no clickbait, no stale news, length limits, blocked channels and keywords
- **The look:** middle-of-video thumbnails (Karpathy's fix), frames that scrub on hover, blur-until-hover, plain de-clickbaited titles (with the original one hover away), "why it's here" with real quotes from recommenders, a Longs shelf, a finite daily feed
- **No accounts, no tracking:** likes, history and watch later live in your browser. Videos play through YouTube's privacy-enhanced embed, so creators still get the view.

## Install

**Claude Code**
```bash
git clone https://github.com/VedSoni-dev/tubesmith ~/.claude/skills/tubesmith
```
Then, in any folder: `/tubesmith`, or just say *"make me my own YouTube"*.

**Other agents** (Codex, Cursor, Gemini CLI, …): clone anywhere and tell your agent `Read tubesmith/SKILL.md and follow it.`

Needs Python 3.8+ (standard library only, nothing to pip install).

## What it builds

```
mytube/
  tube.config.json      ← your answers
  scripts/              ← collect → aggregate → meta → judge → rank
  data/                 ← JSONL, resumable at every step
  site/                 ← static site: index.html, app.js, style.css, videos.json
```

```bash
python3 scripts/hn_collect.py --config tube.config.json        # or channels_collect.py / your own collector
python3 scripts/aggregate.py  --config tube.config.json        # ≥3 people, ≥3 months
python3 scripts/yt_meta.py    --config tube.config.json        # titles, durations, deleted videos
python3 scripts/judge.py      --config tube.config.json --emit # or --run with an API key
python3 scripts/rank.py       --config tube.config.json        # rules + score → site/
python3 -m http.server 8787 -d site
```

## Keys (all optional)

- **YouTube Data API key** (free, 5 min): durations, view counts, Shorts filter, hidden gems. Without it you still get titles and channels.
- **LLM for judging**: your coding agent can do it with subagents (no key), or any OpenAI-compatible endpoint: `PUBLIK_API_KEY`, `OPENAI_API_KEY`, or `TUBE_LLM_BASE_URL` + `TUBE_LLM_API_KEY` + `TUBE_LLM_MODEL` (OpenRouter, a local Ollama, …).

## Credits

The method is Andrej Karpathy's HackerTube. Hacker News data comes from the [Algolia HN API](https://hn.algolia.com/api). Not affiliated with YouTube, Google, Hacker News, Y Combinator or Andrej Karpathy.

MIT licensed.
