# tubesmith

**Make your own YouTube of just the videos you want, the way Andrej Karpathy made [HackerTube](https://hackertube.org).**

Karpathy got tired of YouTube's slop. He told Claude, more or less: *here's where the videos come from, build a YouTube-style viewer for them, add an about page, dark mode, and TV mode.* A couple of hours later he had HackerTube ([blog post](https://karpathy.bearblog.dev/hacker-tube/), [HN thread](https://news.ycombinator.com/item?id=50319510)).

tubesmith is an agent skill that helps you write that prompt for anything, then builds it:

1. **What videos?** In your own words: "horror video essays r/horror loves", "my subscriptions minus Shorts and drama", "the channels on this list".
2. **What should it look like?** "Calm and dark", "like an old TV guide", whatever you picture.
3. **Extras:** about page, dark mode, TV mode, mid-video frames instead of clickbait thumbnails, plain titles, no Shorts.

It turns your answers into one short prompt, shows it to you, and on "go" your agent builds it.

## Install

**Claude Code**
```bash
git clone https://github.com/VedSoni-dev/tubesmith ~/.claude/skills/tubesmith
```
Then run `/tubesmith`, or just say *"make me my own YouTube"*.

**Other agents**: clone it anywhere and tell your agent `Read tubesmith/SKILL.md and follow it.`

## Credits

The idea is Andrej Karpathy's HackerTube. Not affiliated with YouTube, Google or Andrej Karpathy. MIT licensed.
