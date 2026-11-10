# Judging: turning links into a feed

The judge does three jobs per video:
1. **Labels each mention**: `strong_rec`, `rec`, `reference`, `joke`, `critical`, `spam`. Only `rec`/`strong_rec` count toward ranking, so a video linked 10 times as a rickroll goes nowhere.
2. **Writes the card**: summary, why it's here, type, level, shelf life, topics, clickbait score (0–3), plain title, and a verbatim quote per recommendation.
3. **Applies the owner's taste**: `keep: false` when it falls under their NEVER list.

The exact prompt is built by `instructions()` in `scripts/judge.py` from `tube.config.json`. Change the taste in the config, not the prompt.

## Mode A: your agent labels (no extra key)
This is what Karpathy did: a Claude Code Workflow of Sonnet agents.

```bash
python3 scripts/judge.py --config tube.config.json --emit
```
That writes `data/judge/INSTRUCTIONS.md` and `data/judge/batch_NNNN.json` (25 videos each). Then:
- Spawn subagents in parallel (use the cheaper/faster model tier if you can choose; this is reading comprehension, not reasoning). Give each one INSTRUCTIONS.md + one batch file. It writes **one JSON card per line** to the batch's `out` path (`batch_NNNN.out.jsonl`).
- If the user opted into a Workflow (multi-agent orchestration), use it. Otherwise run 4–8 subagents at a time.
- Check progress with `python3 scripts/judge.py --config tube.config.json --status`. Rerun `--emit` after failures; it only emits videos that aren't labeled or already pending.
- Spot-check 3 output files: valid JSON per line, `vid` matches, quotes look verbatim.

## Mode B: an API key
Any OpenAI-compatible `/chat/completions` endpoint:

| Provider | env |
|---|---|
| Publik | `PUBLIK_API_KEY` (defaults to `publik-balanced`) |
| OpenAI | `OPENAI_API_KEY` (defaults to `gpt-4o-mini`) |
| Anything else (OpenRouter, Together, a local Ollama/LM Studio, Anthropic's OpenAI-compatible endpoint…) | `TUBE_LLM_BASE_URL`, `TUBE_LLM_API_KEY`, `TUBE_LLM_MODEL` |

```bash
python3 scripts/judge.py --config tube.config.json --run --limit 20   # pilot
python3 scripts/judge.py --config tube.config.json --run              # the rest; resumable
```

**Show a cost estimate before the full run.** Rough size: ~1.5k input tokens + ~250 output tokens per video (more for videos with 20 mentions). For 7k videos that's about 10M input + 2M output tokens. On a small/cheap model that's a few dollars; on a frontier model, more. Karpathy's whole run was ~500M input tokens (90% cached) because he labeled every comment individually with rich context. This batched version is much cheaper.

## The pilot (don't skip)
Judge 20 videos, rank, then show the user 5 cards: 3 kept, 2 dropped (from `data/dropped.jsonl`), each with title, summary, why it's here, plain title and the drop reason. Ask: *"Does this match your taste? Anything kept that you'd never watch, or dropped that you'd want?"* Turn their answer into edits to `taste.more_of` / `taste.never` / rules, delete `data/labels.jsonl` (or the pilot `.out.jsonl` files), and rerun the pilot if the change was big.

## Quality checks after the full run
- `rank.py` drops quotes that aren't verbatim and prints drop reasons. If "not enough real recommendations" removes more than ~40%, the labeler is too strict: loosen `rules.min_rec_people` to 1 or review a sample.
- Topics: if there are hundreds of near-duplicates ("ml", "machine learning", "deep learning"), merge them. Write a small mapping, apply it to the labels, and rerun rank. Karpathy had Claude draft a fixed taxonomy (150 topics in 16 areas). For big tubes, do that first and put the topic list in `taste.more_of`.
- Expect a few percent label noise. That's fine.
