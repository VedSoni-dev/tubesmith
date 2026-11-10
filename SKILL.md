---
name: tubesmith
description: Make your own YouTube-style viewer for exactly the videos you want, the way Andrej Karpathy made HackerTube. Asks a few quick questions (what videos, what it should look like), turns the answers into one short build prompt, then builds it. Use when someone says "make my own YouTube", "filter YouTube", "a YouTube of just X", "HackerTube for X", or runs /tubesmith.
---

# Tubesmith

Karpathy built HackerTube (hackertube.org) by telling Claude, roughly, *"here's where the videos come from, build a YouTube-style viewer for them, add an about page, dark mode, and TV mode for laid-back watching."* The agent did the rest. His prompts were short. His point was that more detail just constrains the model.

This skill does the same for anyone and anything. You ask a few questions, write that one short prompt, then build it like you normally would. That's it. **Don't overthink it for them, and don't make it hard.**

## 1. Ask (two short rounds, and it should feel like magic)

The ask is the whole product. It should feel like talking to a friend who already gets it: one easy question, then smart options built from their answer, so they mostly just click. Never make them fill out a form. Never ask something you could infer.

### Round 1: one open question (plain chat)

> **What do you wish YouTube was just… that?** Tell me what you want to watch, and where the good stuff comes from if you know.
>
> *e.g. "horror video essays, the ones r/horror actually rates" · "only videos Hacker News recommends" · "my subscriptions without the Shorts and drama" · "cooking from real chefs, not influencers" · "every talk from this list: <link>"*

Read the answer closely. Pick out the **topic**, the **source of taste** (a community, a list, their subs, experts), and anything they already said they **don't** want. If they pasted a link, open it first so your options are real.

### Round 2: one AskUserQuestion call, every option tailored to their answer

Four questions max. Every option is specific to *their* topic, never generic. Put your best guess first, marked (Recommended). They can always pick "Other" and type.

1. **"Whose taste should decide what's in?"** (skip if they already named it). Name 2–3 real sources you know fit this topic, plus "The best of YouTube itself".
   *horror → r/horror + r/TrueFilm · Letterboxd lists · specific critics' channels.* *woodworking → r/woodworking · well-known teaching channels · forum favorites.* *programming → Hacker News · Lobsters · conference talks.*
2. **"What should never show up?"** multiSelect. The slop that's typical for *this* topic.
   *horror → reaction videos · "Top 10 scariest" listicles · AI-voiced creepypasta · spoiler thumbnails.* *cooking → mukbang · rage-bait "chef reacts" · 30-second hacks.* Shorts and clickbait are almost always worth offering.
3. **"What should it feel like?"** Three vibes that fit the topic, each in a few evocative words.
   *horror → "VHS rental store at midnight" · "Criterion-clean, black and white" · "Late-night cable TV".* *cooking → "Warm cookbook" · "Restaurant menu, minimal" · "Market-stall bright".*
4. **"Extras?"** multiSelect. The first three are recommended:
   - **TV mode**: lean back, full screen, the next video plays by itself
   - **Honest thumbnails**: a real frame from the middle of the video instead of the clickbait face (Karpathy's trick: `i.ytimg.com/vi/<id>/hq2.jpg`)
   - **About page**: what this is and where the videos come from
   - **Plain titles**: clickbait rewritten into what the video actually is (original on hover)
   - **"Why it's here"**: one line on each video saying who recommended it and why

Dark mode is a given unless their vibe says otherwise. Don't ask.

**Shortcuts.** If they say "just do it" or "like Karpathy's," skip Round 2: use your Recommended picks plus TV mode, honest thumbnails and an about page. If Round 1 already answered something, drop that question. If anything is still truly unclear, ask **one** follow-up, never a second round of forms.

## 2. Write the prompt

Turn the answers into one short prompt, in the user's words, Karpathy-style. Short beats thorough. Leave everything else to the build.

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
