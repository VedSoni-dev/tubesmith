# Interview script

Ask in rounds. Multiple-choice rounds use AskUserQuestion (≤4 questions per call, 2–4 options each, the recommended option first). Open-ended rounds are one plain chat message. Every answer maps to a `tube.config.json` key, shown in `code`.

If the user says "defaults" or "just do Karpathy's," use the **K** defaults below and skip ahead to the summary.

---

## Round 1: Whose taste do you trust? (multiple choice)

**Q1. "Where should good videos come from?"** multiSelect. Pick at least one → `sources.*`
- Hacker News comments (Recommended; Karpathy's source, no key needed) → `sources.hn.enabled` **K**
- My own channel list or YouTube subscriptions → `sources.channels`
- A community I trust (a subreddit, Lobsters, a Discord, a newsletter) → `sources.custom` (you'll write a collector)
- Specific videos I already love (seed list) → `sources.seeds`

**Q2. "How strict should the 'actually recommended' bar be?"** → `sources.*.min_people` / `min_months`
- Karpathy's bar: 3+ different people, across 3+ different months (Recommended) **K**
- Looser: 2+ people (more videos, more noise)
- Stricter: 5+ people, 5+ months (only the classics)

**Q3. "Name for your tube?"** Offer 2 suggestions based on their source (e.g. "LobsterTube", "QuietFeed") plus "I'll type one." → `name`

## Round 2: Your taste (open-ended, one chat message)

Ask all four at once, with an example:

> Tell me your taste in a few lines. No wrong answers:
> 1. **More of:** what do you want to see? *(e.g. "deep technical talks, history docs, people building things with their hands")*
> 2. **Never:** what should never show up? *(e.g. "reaction videos, drama, crypto hype, anything about the 2024 election")*
> 3. **Gold standard:** 1–3 videos or channels that are exactly your vibe. Links are fine.
> 4. **Hard blocks:** any channels, topics or keywords to always remove? (optional)

→ `taste.more_of`, `taste.never`, `sources.seeds` / `taste.examples`, `taste.block_channels`, `taste.block_keywords`

If they gave channel names in #3 and chose channels in Q1, add them to `sources.channels.list`.

## Round 3: Feed rules (yes/no, multiple choice)

**Q4. "Which rules should your feed enforce?"** multiSelect → `rules.*`
- Never show Shorts (Recommended) → `rules.hide_shorts` **K** *(needs the YouTube API key for durations; otherwise it only catches /shorts/ links)*
- Drop clickbait and ragebait, even if recommended → `rules.drop_clickbait`
- Hide news that has aged out (keep evergreen stuff) → `rules.hide_stale_news`
- Hide view and like counts → `display.hide_counts`

**Q5. "Video length?"** → `rules.min_minutes` / `rules.max_minutes`
- Any length (Recommended) **K**
- Only over 10 minutes (no quick hits)
- Only under 30 minutes (bite-size)

## Round 4: How it looks (multiple choice)

**Q6. "Thumbnails?"** → `display.thumbnails`
- Middle-of-video frame (Recommended; Karpathy's fix for clickbait faces) → `mid` **K**
- Scrub 3 real frames on hover → `frames`
- Blurred until I hover → `blur`
- Original thumbnails → `original`
*(Mention `none` = text-only cards if they ask for "no images.")*

**Q7. "Titles?"** → `display.titles`
- Keep original titles (Recommended; Karpathy kept them) → `original` **K**
- Rewrite clickbait into plain titles (original shown on hover) → `plain`
- Show both: plain title + original underneath → `both`

**Q8. "Extras?"** multiSelect → `display.*`
- "Why it's here" on hover, with a quote from the recommender (Recommended) → `why_tooltip` **K**
- Longs shelf: everything over an hour (Recommended) → `longs_shelf` **K**
- Finite feed: show N then stop → `finite_feed` (ask N, default 24)
- Hidden gems shelf: loved by your source, low YouTube views → `gems_shelf` **K** *(needs the API key)*

## Round 5: Running it (multiple choice)

**Q9. "Who does the AI labeling?"** → `judge.mode`
- You (my coding agent) do it with subagents, no extra key (Recommended in Claude Code) → `agent` **K**
- A script with my API key (Publik, OpenAI, OpenRouter, or a local model; any OpenAI-compatible endpoint) → `api`

**Q10. "YouTube Data API key?"** → `youtube.api_key_env`
- Yes, walk me through it (5 min, free) (Recommended; durations, views, Shorts filter, gems) **K**
- Skip (titles and channels only; no Shorts/length filtering)

**Q11. "Where does it live?"** → `deploy`
- On my computer only (Recommended) → `local` **K**
- A free static host (Vercel / Netlify / GitHub Pages) → `static`
- My own server + domain (Karpathy's setup) → `vps`

---

## The summary (show before building)

One screen, no JSON:

```
🎬 QuietFeed
Sources   Hacker News comments (3+ people, 3+ months) + 2 seed videos
More of   deep technical talks, history docs, maker builds
Never     reaction videos, drama, crypto hype
Rules     no Shorts · no clickbait · any length
Look      middle-frame thumbnails · original titles · "why it's here" · Longs shelf
Labeling  me (subagents), roughly 7k videos ≈ 30–60 min
Lives     on your computer → http://localhost:8787
Needs     YouTube API key (I'll walk you through it)
```

Then: "Look right? Say go, or tell me what to change."
