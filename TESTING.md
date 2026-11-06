# How to test Stall Alerter

About 15 minutes. The sample board (`data/board.csv`, 46 candidates) is already in the repo and is
loaded by default in both the UI and the CLI. What it *should* produce is written down in
[data/EXPECTED.md](data/EXPECTED.md), so you can check the tool against it.

> The sample is dated around **2026-11-06**. Keep "Today" = 2026-11-06 (the UI default for the sample,
> or `--today 2026-11-06` in the CLI) or the day counts will drift.

---

## 1. Setup (once)

You need Python 3.10+. If `python` isn't on your PATH but `uv` is (as on the build machine), use Option A:

```bash
# Option A: uv
uv venv --python 3.12
uv pip install -r requirements.txt

# Option B: normal Python
python -m venv .venv
pip install -r requirements.txt
```
Activate: `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (macOS/Linux).

API keys (optional, only for the AI parts): `cp .env.example .env` and fill in **one** provider:

| Provider | Put in `.env` |
|---|---|
| Claude | `ANTHROPIC_API_KEY=...` |
| OpenAI | `OPENAI_API_KEY=...` |
| Groq (free tier, cheapest demo) | `GROQ_API_KEY=...` |
| OpenRouter | `OPENROUTER_API_KEY=...` |

With one key set, that provider is picked automatically. Set `LLM_PROVIDER=groq` (etc.) only if you have several keys.

---

## 2. Automated tests (1 minute)

```bash
pytest
```
Expect **38 passed**. They need no network and no keys. They cover:
- the flagged set equals `EXPECTED.md` (24 stalled), closed rows ignored, bad rows reported
- edge cases: 3-day boundary, a recent contact resets the clock, waiting on us, ties, day cap
- the AI score change clamped to ±2, unknown AI rows ignored, fallback to rules
- provider switching and JSON parsing for OpenAI-style providers (fake clients)
- the web UI over HTTP: sample + upload, bad CSV/date errors, HTML escaping, provider fallback,
  drafts generate, approve (with edits) / skip / undo, download contains only approved drafts

Runs in about 2 seconds.

---

## 3. The UI (this is what to demo)

```bash
python -m stall_alerter.web            # add --port 8001 if 8000 is busy
```
Open http://127.0.0.1:8000. It's FastAPI + HTMX: the server returns HTML fragments and HTMX swaps them
in, so there is no JavaScript build step. It listens on localhost only.

**Walkthrough**
1. Top panel: leave the upload empty (it uses the sample), Today = 2026-11-06, threshold = 3.
2. Provider: pick **Rules only** first and press **Find stalled candidates**.
   - Check the metrics: **40 open, 24 stalled, 4 waiting on us, 2 data problems**.
   - Check the top 2 are **Wanjiru Kamau** (Offer, 6 days) and **Grace Achieng** (Final, waiting on us).
   - Open **Data problems**: C044 (missing date) and C045 (unknown stage "Onsite").
3. Switch Provider to one you have a key for (or paste the key into the key box that appears) and run again.
   - Green/red **+N AI** badges in the Score column show the nudges, never more than ±2.
   - "Why" and "Next action" should now quote the notes (competing offer, CTO referral, etc.).
4. Scroll to **Follow-up drafts** and press **Generate drafts** (top 5).
   - Edit one message in its text box, then **Approve**. **Skip** another. **Undo** works.
   - Each click swaps only that card and the counter (no page reload).
   - **Download approved drafts** gives a `.md` of only the approved messages. Nothing is sent anywhere.
5. Try your own CSV with the file picker (same columns as the sample; see README).

---

## 4. The CLI

```bash
python -m stall_alerter data/board.csv --today 2026-11-06 --no-ai               # rules only
python -m stall_alerter data/board.csv --today 2026-11-06 --provider groq       # AI ranking
python -m stall_alerter data/board.csv --today 2026-11-06 --provider anthropic --drafts
```
- `--drafts` shows each draft in the terminal: type `a` (approve), `e` (edit, then type the new text) or `s` (skip).
- Reports are written to `out/report.md`, `out/report.csv` and `out/approved_drafts.md`.
- Other options: `--days 5`, `--top 3`, `--model <id>`, `--out <folder>`. See `--help`.

---

## 5. What to check by hand (the AI can't be unit-tested)

Run once with **Rules only** and once with a provider, and compare:

| Candidate | Notes say | What a good AI result looks like |
|---|---|---|
| Wanjiru Kamau (C001) | Competing offer, decision Monday | Stays #1 or +1/+2; action is to call today |
| Alex Kimani (C042) | Counter-offer likely | Moves up |
| Irene Moraa (C023) | Interviewing elsewhere | Moves up |
| Ruth Kemunto (C021) | CTO referral | Moves up from the bottom |
| Faith Njeri vs Peter Kiprop (C005/C006) | Tied in rules | AI separates them with a reason |
| Dennis Owino (C028) | Over salary band | 0 or negative; action may be to decline politely |

Red flags to log (these feed your daily log / unlearned note):
- Invented facts in a reason or draft (salary, dates, promises not in the CSV)
- A draft that promises an offer or an outcome
- The same candidate getting very different results across providers

If a provider fails, the tool says so (`[warn] ...` in the CLI, a yellow box in the UI) and
falls back to the rules ranking. That's expected, not a crash.

---

## 6. Troubleshooting

| Symptom | Fix |
|---|---|
| `python` opens the Microsoft Store | Use `uv` (Option A) or install Python from python.org with "Add to PATH" |
| "`X_API_KEY` is not set" | Add it to `.env` or paste it in the key box in the UI |
| "model not found" / 404 | The default model id is out of date; pass `--model` or edit it in the UI |
| Everyone (or no one) is stalled | "Today" is wrong for the data; use 2026-11-06 for the sample |
| Port 8000 busy | `python -m stall_alerter.web --port 8001` |
| "Run not found" after clicking a draft | The server restarted (runs are kept in memory); press Find stalled candidates again |
