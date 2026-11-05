# Stall Alerter

Reads a hiring-board CSV, finds candidates who haven't moved in N days (default 3), and ranks who
a hiring manager should follow up with first, with a one-sentence reason and next action for each.

> Status: scaffolding. See [plan.md](plan.md).

## Setup
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # add your ANTHROPIC_API_KEY (optional: rules-only without it)
```

## Run
```bash
python -m stall_alerter data/board.csv            # default: 3-day threshold
python -m stall_alerter data/board.csv --days 5
python -m stall_alerter data/board.csv --no-ai    # rules-only ranking
python -m stall_alerter data/board.csv --drafts   # draft follow-ups, approve each one
```

## Test
```bash
pytest
```

## Docs
- [plan.md](plan.md): the 5-day plan and decisions
- [intent.md](intent.md): what and why
- [directive.md](directive.md): how I direct the AI (versioned daily)
- [logs/](logs/): daily logs
- [unlearned.md](unlearned.md): what I unlearned
