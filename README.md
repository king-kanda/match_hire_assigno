# Stall Alerter

Reads a hiring-board CSV, finds candidates who haven't moved in N days (default 3), and ranks who
a hiring manager should follow up with first, with a one-sentence reason and a next action for each.
Optionally drafts follow-up messages that **a human approves, edits or skips. Nothing is ever sent.**

- **Rules decide** who is stalled and the base priority (stage, days quiet, whether we owe a reply).
- **An LLM of your choice** reads the free-text notes, can nudge each score by at most ±2
  (clamped in code), and writes the reason, the next action and the drafts.
- **No API key, or the provider fails?** It falls back to rules-only output, so the tool always runs.

## LLM providers
Switch with `--provider` / `--model`, or set `LLM_PROVIDER` / `LLM_MODEL` in `.env` (flags win).

| `--provider` | Key in `.env` | Default model |
|---|---|---|
| `anthropic` (default) | `ANTHROPIC_API_KEY` | `claude-sonnet-5-5` |
| `openai` | `OPENAI_API_KEY` | `gpt-4.1-mini` |
| `groq` | `GROQ_API_KEY` | `llama-3.3-70b-versatile` |
| `openrouter` | `OPENROUTER_API_KEY` | `openai/gpt-4.1-mini` |

Defaults are starting points; check the provider's current model list and pass `--model` to change.
Claude uses the Anthropic SDK's structured output. OpenAI, Groq and OpenRouter share one
OpenAI-compatible adapter using JSON mode, and every response is validated with Pydantic before use.

## Setup
Requires Python 3.10+.
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # add ANTHROPIC_API_KEY (optional)
```
With [uv](https://docs.astral.sh/uv/): `uv venv --python 3.12 && uv pip install -r requirements.txt`.

## Web UI (for the demo)
```bash
python -m stall_alerter.web      # then open http://127.0.0.1:8000
```
FastAPI + HTMX (server-rendered HTML, no JS build; htmx is vendored in `stall_alerter/static`). It loads the sample board by default (or upload your own CSV). Pick a provider, see the ranked list,
then generate drafts and **edit / approve / skip** each one; download only the approved ones.
Full walkthrough: [TESTING.md](TESTING.md).

## CLI
The sample data is dated around **2026-11-06**, so pass `--today 2026-11-06` to reproduce the demo.
Drop `--today` to use the real date on your own board.

```bash
python -m stall_alerter data/board.csv --today 2026-11-06            # AI-assisted ranking
python -m stall_alerter data/board.csv --today 2026-11-06 --no-ai    # rules only
python -m stall_alerter data/board.csv --today 2026-11-06 --drafts   # + review drafts for the top 5
python -m stall_alerter data/board.csv --today 2026-11-06 --provider groq
python -m stall_alerter data/board.csv --today 2026-11-06 --provider openrouter --model anthropic/claude-sonnet-4.5
python -m stall_alerter data/board.csv --days 5 --top 3 --out out/   # other options
```

Output:
- Terminal: ranked list with why / next action / owner, plus any data problems
- `out/report.md` and `out/report.csv`
- `out/approved_drafts.md`, only with `--drafts` (approved messages to copy into email/ATS)

## CSV format
`candidate_id, name, role, stage, stage_entered_date, last_contact_date, last_contact_by, owner, notes`
- Dates `YYYY-MM-DD`. `last_contact_by` is `us` or `them` (`them` = they're waiting on us).
- Stages: `Applied, Screening, Interview, Final, Offer`. `Hired` and `Rejected` are ignored.
- Rows with a missing stage date or an unknown stage are listed as **data problems**, never silently dropped.

## Test
```bash
pytest
```
Step-by-step manual testing (UI, CLI, what to check in the AI output): [TESTING.md](TESTING.md).
Tests check the sample board against [data/EXPECTED.md](data/EXPECTED.md): the flagged set, boundary,
contact-resets-clock, owe-reply, ties, capped days, AI clamp, fallback, draft review and CLI output.

## How the score works
`2 × stage weight (Applied 1 … Offer 5) + 0.5 × days quiet (capped at 14) + 3 if we owe a reply`,
then `± up to 2` from Claude based on notes (competing offer, referral, mismatch, etc.).

## Project docs
- [plan.md](plan.md): plan and decisions
- [intent.md](intent.md): what and why
- [directive.md](directive.md): how I direct the AI
- [logs/](logs/): daily logs
- [unlearned.md](unlearned.md): what I unlearned
