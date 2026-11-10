# Sources: where "good" comes from

Every source turns into one of two files in `data/`:

- `mentions.<source>.jsonl`: **community signal**, one row per (comment/post, video):
  ```json
  {"vid": "SxdOUGdseq4", "source": "reddit", "author": "someuser", "ts": 1700000000,
   "month": "2023-11", "text": "the full comment text, plain", "context": "thread / post title",
   "url": "permalink to the comment"}
  ```
  `aggregate.py` picks up every `data/mentions.*.jsonl` automatically. Use `common.video_ids(text)` to pull IDs out of any text or HTML. Require real text (`common.own_text_len(text) >= 100` is Karpathy's bar) so bare links don't count.
- `channel_videos.jsonl`: **your own channels**, written by `channels_collect.py`.

## Hacker News (built in)
`scripts/hn_collect.py` uses the public Algolia HN API (no key). The full history (2007 to now) is roughly 185k comments mentioning YouTube, fetched at about 1,000 per request, so it takes about 15 minutes. It's resumable. For a quick first build, pass `--since 2024-01-01`, then backfill later.

Prefer the exact dataset Karpathy used? The HuggingFace `open-index/hacker-news` dump has every comment as parquet (big download). Write a collector that emits the same schema.

## Your channels / subscriptions (built in)
`scripts/channels_collect.py` reads each channel's public RSS feed (`youtube.com/feeds/videos.xml?channel_id=UC…`, last 15 uploads, no key). Accepts `@handles`, channel URLs and `UC…` ids.
- Full subscription list: Google Takeout (takeout.google.com) → deselect all → *YouTube and YouTube Music* → *subscriptions* only → export. The user downloads it and passes `--subscriptions-csv path/to/subscriptions.csv`.
- This is "filter on top of YouTube": your channels, minus whatever your rules drop (Shorts, clickbait, topics you never want).

## Reddit (write a collector)
Reddit's API needs an app (reddit.com/prefs/apps → "script" type, free for personal use) and OAuth. Walk the user through creating one; keep the client id/secret in env vars. Search the subreddit for `site:youtube.com OR youtu.be` and pull the top/all-time posts plus their comments. Emit `mentions.reddit.jsonl` with `author` = username and `context` = post title. Lower thresholds (`sources.custom.min_people: 2`) suit smaller communities.

## Lobsters (write a collector)
Public JSON with no key: `https://lobste.rs/domain/youtube.com.json?page=N` (and `youtu.be`) lists stories. Each story's comments are at `https://lobste.rs/s/<short_id>.json`. The story submitter counts as one mention, and each comment that links the video counts as another.

## Anything else
Discord export (DiscordChatExporter JSON), Slack export, a newsletter archive, your browser bookmarks, Pocket/Raindrop export, an Obsidian vault, a friend's list. If it contains YouTube links plus who said what, it's a source. Write a 30-line collector, emit the schema, and show 5 sample rows before moving on.

## Seeds
`sources.seeds` = video URLs that always get in (the user's gold-standard examples). The judge also sees them as taste examples.

## YouTube Data API key
Needed for durations, views/likes, publish dates, Shorts filtering and hidden gems. Free, no credit card. **You can't do these steps for the user. Walk them through it:**

1. Open https://console.cloud.google.com/ and sign in.
2. Top bar → project picker → **New project** (any name, e.g. "my-tube").
3. **APIs & Services → Library** → search **YouTube Data API v3** → **Enable**.
4. **APIs & Services → Credentials → Create credentials → API key**. Copy it.
5. Click the key → **API restrictions → Restrict key → YouTube Data API v3** → Save. Now a leaked key can't be used for anything else.
6. In the terminal that will run the pipeline: `export YOUTUBE_API_KEY=...` (or add that line to their shell profile). Never paste it into chat, code, or `tube.config.json`.

Quota: `videos.list` costs 1 unit per 50 videos, so 7,000 videos ≈ 140 units out of 10,000/day. `search.list` costs 100 units each; avoid it.

## Terms
- YouTube API data: show it with attribution, keep the key private, don't redistribute raw metadata dumps, and refresh stored data periodically (counts and availability change). https://developers.google.com/youtube/terms/developer-policies
- Thumbnails are loaded straight from `i.ytimg.com` and videos play through the official embed. Never download or re-host either.
- Community text: link back to every quoted comment (the site does), and credit the community in `display.credits`.
