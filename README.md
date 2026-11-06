# Stall Alerter

Reads a hiring-board CSV, finds candidates who haven't moved in N days (default 3), and ranks who
a hiring manager should follow up with first, with a one-sentence reason and a next action for each.
It can also draft follow-up messages that **a human approves, edits or skips. Nothing is ever sent.**

- **Rules decide** who is stalled and the base priority (stage, days quiet, whether we owe a reply).
- **An LLM of your choice** (Anthropic, OpenAI, Groq or OpenRouter) reads the free-text notes, can nudge
  each score by at most ±2 (clamped in code), and writes the reason, the next action and the drafts.
- **No API key, or the provider fails?** It falls back to rules-only output, so the tool always runs.
- Two front ends on one engine: a **web UI** (FastAPI + HTMX) for day-to-day use and the demo, and a **CLI**.

## Setup
Requires Python 3.10+.
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # optional: add an API key for any one provider
```
With [uv](https://docs.astral.sh/uv/): `uv venv --python 3.12 && uv pip install -r requirements.txt`.

## Web UI (for the demo)
```bash
python -m stall_alerter.web              # open http://127.0.0.1:8000  (--port 8001 to change)
```
1. Leave the upload empty to use the sample board (or pick your own CSV), keep Today = 2026-11-06 for the sample.
2. Pick an AI provider (or **Rules only**) and press **Find stalled candidates**: summary counts, ranked table,
   data problems.
3. **Generate drafts** for the top N, then **edit / approve / skip / undo** each one.
   **Download approved drafts** exports only the approved messages as Markdown.

Server-rendered HTML with HTMX (vendored in `stall_alerter/static`, so it works offline; no JS build).
It listens on localhost only, since API keys can be pasted into the page. Runs are kept in memory, so
restarting the server clears them. Full walkthrough: [TESTING.md](TESTING.md).

## CLI
The sample data is dated around **2026-11-06**, so pass `--today 2026-11-06` to reproduce the demo.
Drop `--today` to use the real date on your own board.

```bash
python -m stall_alerter data/board.csv --today 2026-11-06            # AI ranking if a provider/key is set, else rules only
python -m stall_alerter data/board.csv --today 2026-11-06 --no-ai    # force rules only
python -m stall_alerter data/board.csv --today 2026-11-06 --drafts   # + review drafts for the top 5 (a / e / s)
python -m stall_alerter data/board.csv --today 2026-11-06 --provider groq
python -m stall_alerter data/board.csv --today 2026-11-06 --provider openrouter --model anthropic/claude-sonnet-4.5
python -m stall_alerter data/board.csv --days 5 --top 3 --out out/   # other options (see --help)
```

Output:
- Terminal: ranked list with why / next action / owner, plus any data problems
- `out/report.md` and `out/report.csv`
- `out/approved_drafts.md`, only with `--drafts` (approved messages to copy into email/ATS)

## LLM providers
No provider is the default. The choice is made in this order:
1. `--provider` / `--model` (CLI) or the dropdown and model box (web UI)
2. `LLM_PROVIDER` / `LLM_MODEL` in `.env`
3. otherwise, the first provider that has an API key in the environment
4. no keys at all: rules only

| Provider | Key in `.env` | Default model |
|---|---|---|
| `anthropic` | `ANTHROPIC_API_KEY` | `claude-sonnet-5-5` |
| `openai` | `OPENAI_API_KEY` | `gpt-4.1-mini` |
| `groq` | `GROQ_API_KEY` | `llama-3.3-70b-versatile` |
| `openrouter` | `OPENROUTER_API_KEY` | `openai/gpt-4.1-mini` |

Default models are starting points; check the provider's current model list and override with `--model`.
Anthropic uses its SDK's structured output. OpenAI, Groq and OpenRouter share one OpenAI-compatible
adapter using JSON mode. Every response is validated with Pydantic before it is used.

## CSV format
`candidate_id, name, role, stage, stage_entered_date, last_contact_date, last_contact_by, owner, notes`
- Dates `YYYY-MM-DD`. `last_contact_by` is `us` or `them` (`them` = they're waiting on us).
- Stages: `Applied, Screening, Interview, Final, Offer`. `Hired` and `Rejected` are ignored.
- "Movement" is the later of `stage_entered_date` and `last_contact_date` (a logged contact resets the clock).
- Rows with a missing stage date, a bad date or an unknown stage are listed as **data problems**, never silently dropped.

## How the score works
`2 × stage weight (Applied 1 … Offer 5) + 0.5 × days quiet (capped at 14) + 3 if we owe a reply`,
then `± up to 2` from the chosen LLM, based on the notes (competing offer, referral, mismatch, etc.).
Ties go to whoever has waited longer. Weights live at the top of `stall_alerter/rules.py`; the ±2 limit is
`MAX_ADJUSTMENT` in `stall_alerter/llm.py`.

## Test
```bash
pytest          # 38 tests, ~2 seconds, no network or keys needed
```
Covers the sample board against [data/EXPECTED.md](data/EXPECTED.md) (flagged set, boundary, contact
resets the clock, owe-reply, ties, capped days), the AI clamp and fallback, provider selection, the CLI,
and the web UI over HTTP (upload, errors, HTML escaping, draft approve / edit / skip / undo / download).
Manual testing, including what to check in real AI output: [TESTING.md](TESTING.md).

## Project structure
```
stall_alerter/
  load.py         read + validate the CSV (bad rows -> data problems)
  rules.py        who is stalled, base score, rules-only reason/action
  llm.py          prompts + schemas for the AI review and drafts
  providers.py    anthropic | openai | groq | openrouter behind one function
  rank.py         combine base score + clamped AI adjustment, final order
  drafts.py       draft follow-ups, approve/edit/skip review (CLI), templates without AI
  cli.py          command-line front end
  web.py          FastAPI + HTMX front end (templates/, static/)
data/board.csv    sample board (46 candidates, every edge case)
data/EXPECTED.md  what the sample should produce
tests/            pytest suite
```

## Project docs
- [plan.md](plan.md): background: decision history, timeline, what's left (not a deliverable)
- [intent.md](intent.md): what and why (working version)
- [directive.md](directive.md): how I direct the AI
- [TESTING.md](TESTING.md): how to test and demo
- [logs/](logs/): daily logs
- [unlearned.md](unlearned.md): what I unlearned
