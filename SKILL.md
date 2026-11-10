---
name: tubesmith
description: Make your own YouTube-style viewer for exactly the videos you want, the way Andrej Karpathy made HackerTube. Asks a few quick questions (what videos, what it should look like), turns the answers into one short build prompt, then builds it. Use when someone says "make my own YouTube", "filter YouTube", "a YouTube of just X", "HackerTube for X", or runs /tubesmith.
---

# Tubesmith

Karpathy built HackerTube (hackertube.org) by telling Claude, roughly, *"here's where the videos come from, build a YouTube-style viewer for them, add an about page, dark mode, and TV mode for laid-back watching."* The agent did the rest. His prompts were short. His point was that more detail just constrains the model.

This skill does the same for anyone and anything. You ask a few questions, write that one short prompt, then build it like you normally would. That's it. **Don't overthink it for them, and don't make it hard.**

## 1. Ask (one round, keep it light)

Ask in plain chat (or AskUserQuestion for the multiple-choice parts). Give examples so they know the shape:

1. **What videos?** Describe the source and the filter, in your own words.
   *e.g. "videos Hacker News commenters recommend", "horror video essays r/horror loves", "the top channels on this list: <link>", "my subscriptions minus Shorts and drama", "woodworking from people who actually know what they're doing"*
2. **What should it look like?** *e.g. "like YouTube but calmer", "dark, minimal, big thumbnails", "like an old TV guide"*
3. **Extras?** multiSelect. Recommend the first four:
   - About page (what this is, where the videos come from)
   - Dark mode
   - TV mode: lean-back, full screen, autoplays the next video
   - No clickbait thumbnails: use YouTube's auto frame from the middle of the video (`i.ytimg.com/vi/<id>/hq2.jpg`, Karpathy's trick)
   - Plain titles: rewrite clickbait into what the video actually is (original on hover)
   - "Why it's here" on each video
   - No Shorts

If they say "just do it" or "like Karpathy's," use: dark mode, about page, TV mode, mid-frame thumbnails.

## 2. Write the prompt

Turn the answers into one short prompt, in the user's words, Karpathy-style:

> Build me a YouTube-style viewer for **[what videos, from where, filtered how]**. It should look **[look]**. Add **[extras]**.

Example: *"Build me a YouTube-style viewer for horror video essays that r/horror and r/TrueFilm actually recommend, no reaction videos. Calm and dark, big thumbnails. Add an about page, TV mode for laid-back watching, and use mid-video frames instead of thumbnails."*

Show it to them in one line, and say "go?" Let them tweak it.

## 3. Build it

On "go," treat that prompt as the task and do it the way you normally would. Use your own judgment for everything the prompt doesn't say: find the videos, check what people actually recommend, gather the metadata, build the site, run it, and open it for them.

A few things that keep it good (not rules to recite to the user):
- **Play videos through YouTube's embed** (`youtube-nocookie.com`). Never download or re-host videos.
- **Own name and look.** Don't copy YouTube's logo or red play button. Karpathy changed his logo when people said it looked too much like YouTube's.
- **Keys go in env vars, never in the code.** A YouTube Data API key (free, from Google Cloud Console) helps with durations and view counts. Walk them through getting one only if it's actually needed.
- **Ask before anything outward**: deploying, pushing, buying a domain.
- Start small, show it running fast, then improve it with them. Rebuild and reload after each change.
