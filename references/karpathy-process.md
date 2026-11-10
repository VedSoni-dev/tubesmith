# The HackerTube method (what Karpathy actually did)

Sources: the HN thread (news.ycombinator.com/item?id=50319510, 31 Oct 2026), his blog post (karpathy.bearblog.dev/hacker-tube/), and hackertube.org/about + /data. Paraphrased; read the originals for his exact words.

## Setup
- Claude Code with Opus 5.5 on medium effort. He talked; Claude did everything, including deploying to his VPS.
- He did three things by hand: a Google Cloud API key for YouTube metadata, booting a VPS, and buying the domain (plus one DNS record).
- About 2 hours in total. Most tokens went to Sonnet labeling comments. The app and deploy were about 1M Opus tokens.
- His prompts were short. Over-specifying constrains the model.

## Pipeline
1. **Collect.** Download every HN comment (2007–2026) from the public HuggingFace dump (`open-index/hacker-news`) and find YouTube links. A comment counts only if it has **≥100 characters of its own text** besides the link (so bare links don't count).
2. **First cut.** Keep a video only if **≥3 different people** linked it, with real commentary, in **≥3 different months**. Keep up to **20 mentions** per video, preferring different commenters. That leaves about 7,000 videos.
3. **Label (LLM).** Sonnet agents in a Claude Code Workflow read each comment *with its story title* and decide whether the commenter is recommending the video, citing it, joking, or criticizing it. Labels: `strong_rec`, `rec`, `reference`, `joke`, `critical`. Only the first two count. Each mention also gets a "why" (≤15 words), a **verbatim quote checked against the comment text**, and topics. Spam is dropped here.
4. **Cards (LLM).** One card per video, built from the mentions plus YouTube metadata: summary, why HN likes it, type (talk, lecture, documentary…), level, **shelf life** (evergreen / dated / news). There are 150 topics in 16 areas, from a taxonomy Claude drafted.
5. **Rank.** `score = months_with_a_rec + 0.5 × months_with_a_strong_rec`. Steady recommendations over years beat one viral spike.
6. **Result.** 6,454 videos from 39,834 comments. About 6% of linked videos had already been deleted or made private.

## The product
- **Thumbnails:** uses `i.ytimg.com/vi/<id>/hq2.jpg`, YouTube's auto-generated frame from the middle of the video, instead of the uploader's thumbnail. It shows what the video really looks like. Original thumbnails are a Settings toggle (a commenter wanted them for recognition).
- **Titles:** kept as is. The anti-clickbait filtering happens through *which* videos get in, plus an AI summary drawn from what people said.
- **Home feed:** a mix of HN classics, **hidden gems** (loved on HN, low YouTube views), recent favorites, and topics you haven't explored. After a few likes it adds similar videos and videos recommended by the same people. Hovering shows **why it's here**.
- **Search** by topic, not just keywords: bge-small embeddings, reranked with a Jina reranker.
- **No accounts.** Likes, history and Watch later live in localStorage. Playback goes through the privacy-enhanced embed.
- **Added during the thread, from comments:** filters for duration, type and upload date (shown up front, not hidden behind search), a "recently recommended" sort, a like/view ratio sort smoothed so tiny videos can't win, "Play all on YouTube" (a temporary playlist), an "Evergreen only" filter, a new logo that looks less like YouTube's, and **"Longs"** (all videos over an hour, placed where YouTube puts Shorts). Shorts: never.

## What didn't work / caveats
- The server code was a "vibe coded mess," so he shipped the data, not the code.
- YouTube's terms don't allow redistributing its metadata, so forks need their own (free) API key.
- LLM labels carry a few percent of noise. Some talks show up twice under different video IDs.
- Filters hidden behind search confused people.

## Ideas from the thread worth offering
- Rank your *own* sources (RSS, channels) with a cheap model. The feed is yours, not the platform's.
- Some people want serendipity. Keep an "unexplored topics" shelf so the feed doesn't become an echo chamber.
- A keyword/topic block list for sensitive viewers (one commenter's 87-year-old father wanted WWII footage filtered out).
- Friends publish their picks, and you subscribe to people, not algorithms.
- Export the curated list as auto-updating YouTube playlists.
- The same pipeline works for other things: books, Wikipedia articles and films have all been done this way.
