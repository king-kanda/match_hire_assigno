# Plan: Stall Alerter (Quest Format C)

**Quest:** Unlearn, Use, Raise the Load (Match Hire)
**Window:** 5 days allowed. **The tool itself was built in about one day** (2026-11-05 evening to 2026-11-06 midday),
working AI-first. The remaining days go to testing it with real models, the write-ups and the videos.
**Build style:** AI-first. I log what the AI did, where it was wrong, and what I changed.

## The tool in one line
A hiring manager with 40+ candidates runs one command on their hiring-board CSV. They get a ranked
shortlist of stalled candidates, each with a one-sentence reason and a concrete next action. Optionally,
there's a drafted follow-up message that they approve or edit before anything is sent.

## Decisions made (grill session, 2026-11-05)
| Topic | Decision |
|---|---|
| User | A hiring manager with 40+ active candidates who checks in short bursts and wants about 5 minutes to act |
| Stall rule | **3 days** without movement (can be changed with `--days`) |
| "Moved" means | A stage change **or** a logged contact (email, call or interview) |
| Ranking | Rules compute a base score. The chosen LLM reads `notes` and can only adjust it **within a limit**. |
| Rule signals | Days stalled, stage weight (Offer > Final > Interview > Screening > Applied), `last_contact_by = them` (we owe a reply) |
| AI signals | Free-text notes: competing offers, availability, flight risk, enthusiasm |
| Output | Web UI (FastAPI + HTMX) and a CLI; `report.md`/`report.csv` export |
| Drafted nudge | Built. Always needs human approval (approve / edit / skip / undo) and is never sent. |
| Stack | Python 3.10+, FastAPI + HTMX UI, CLI. LLM is switchable with no fixed default: Anthropic, OpenAI, Groq, OpenRouter |
| No API key | Falls back to a rules-only ranking so the demo can't fail |

## CSV schema (`data/board.csv`)
`candidate_id, name, role, stage, stage_entered_date, last_contact_date, last_contact_by, owner, notes`
- Dates: `YYYY-MM-DD`
- `last_contact_by`: `us` | `them`
- `stage`: `Applied | Screening | Interview | Final | Offer | Hired | Rejected` (Hired and Rejected are ignored)

## Architecture
```
board.csv -> load (validate) -> rules.py (stalled? base score) -> llm.py (adjust within the limit, reason, action)
          -> rank.py (final order) -> web.py (HTMX UI) or cli.py (terminal) -> drafts.py (human approves each)
providers.py: anthropic | openai | groq | openrouter, picked by flag > LLM_PROVIDER > whichever key is set
```

## What actually happened: built in ~1 day
The original plan spread the build over 5 days. Working AI-first, it took two sessions:

### Session 1: 2026-11-05, ~23:00 to 00:00
- [x] Grilled the idea first: picked format C, user = hiring manager with 40+ candidates, 3-day stall rule
- [x] Repo scaffold + this plan
- [x] Sample board (46 rows with every edge case) and `data/EXPECTED.md` written **before** the logic
- [x] Rules engine (`load.py`, `rules.py`, `rank.py`), tests against the expected output
- [x] LLM layer with the ±2 limit enforced in code; rules-only fallback
- [x] Drafts with approve / edit / skip; `report.md` / `report.csv`
- [x] Switchable providers (Anthropic, OpenAI, Groq, OpenRouter)
- [x] First UI (Streamlit) + `TESTING.md`

### Session 2: 2026-11-06, midday
- [x] Replaced Streamlit with FastAPI + HTMX (looks like a real tool, no JS build)
- [x] Checked it in a real browser: fixed 2 console errors
- [x] Removed the hard-coded Anthropic default; provider now auto-detected from whichever key is set
- [x] 38 automated tests passing

### Course corrections along the way (material for the logs and `unlearned.md`)
- The template drafts pasted the manager's to-do into the message to the candidate. Caught on a manual run.
- The testing guide said 6 candidates were "waiting on us"; the real number was 4. Checked the numbers against the code.
- Streamlit was the fast choice, but it looked like a prototype, so I swapped it for HTMX.
- The docs and the default provider still assumed Claude after providers became switchable.

## Remaining days: prove it, write it up, record it
- [ ] Run with at least one real API key; compare against rules-only using `TESTING.md` section 5
- [ ] Run the same board on two providers; note where they disagree
- [ ] Fix anything the real-model runs reveal (invented facts, weak drafts, bad JSON)
- [ ] Rewrite `intent.md` and `directive.md` in my own words; add a final directive version
- [ ] Logs (see note below), `unlearned.md`
- [ ] Quest Loom (max 5 min): run, ranked list, explain #1 vs #2, AI vs rules, approve one draft
- [ ] Career path & leverage video (separate, max 5 min)
- [ ] Submit all 7 deliverables

**Note on the 5 daily logs:** the quest asks for a log for each of the 5 days. Since the build took about a day,
write that honestly: day 1 = the build, the later days = testing with real models, fixes, write-ups and recording.
Don't backfill a fake 5-day build.

## Edge cases the sample data must contain
- Contacted yesterday, so **not** stalled despite an old stage date
- `last_contact_by = them`, so we owe a reply (should rank high)
- Competing offer mentioned in notes (AI should push it up)
- Missing `last_contact_date` (falls back to `stage_entered_date`)
- Two candidates tied on base score (AI notes should break the tie)
- Hired/Rejected rows (must be ignored)
- Offer stage at exactly 3 days (boundary)

## Done means
Given `data/board.csv` (today = 2026-11-06), the UI or `python -m stall_alerter data/board.csv` shows a ranked list where every
expected-stalled candidate appears, nobody unexpected appears, and every row has a reason and an action.
It runs in under 30 seconds with an API key, and also runs without one.

## Deliverables checklist
- [ ] Loom: tool working (max 5 min)
- [ ] `intent.md` (draft exists; rewrite in my own words)
- [ ] Final `directive.md` (v1 drafted)
- [x] Working code + README (+ `TESTING.md`)
- [ ] `logs/day-1..5.md` (day 1 = build; days 2-5 = testing, fixes, write-ups)
- [ ] `unlearned.md`
- [ ] Career path & leverage video

## Things only I can write
- What I'm unlearning (daily logs + `unlearned.md`)
- Career leverage story (video)
