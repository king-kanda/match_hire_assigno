# Plan: Stall Alerter (Quest Format C)

**Quest:** Unlearn, Use, Raise the Load (Match Hire)
**Window:** 5 days, starting 2026-11-06. Deadline is the countdown on the quest page.
**Build style:** AI-first. Every day I log what the AI did, where it was wrong, and what I changed.

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
| Output | Terminal table plus a `report.md`/`report.csv` |
| Drafted nudge | In scope, **first to cut**. Always needs human approval and is never sent automatically. |
| Stack | Python 3.10+ CLI. LLM is switchable with no fixed default: Anthropic, OpenAI, Groq, OpenRouter |
| No API key | Falls back to a rules-only ranking so the demo can't fail |

## CSV schema (`data/board.csv`)
`candidate_id, name, role, stage, stage_entered_date, last_contact_date, last_contact_by, owner, notes`
- Dates: `YYYY-MM-DD`
- `last_contact_by`: `us` | `them`
- `stage`: `Applied | Screening | Interview | Final | Offer | Hired | Rejected` (Hired and Rejected are ignored)

## Architecture
```
board.csv -> load (validate) -> rules.py (stalled? base score) -> llm.py (adjust within the limit, reason, action)
          -> rank.py (final order) -> cli.py (table + report) -> [optional] drafts.py (human approves each)
```

## Day-by-day
### Day 1: Intent + data
- [ ] Rewrite `intent.md` in my own words (the AI draft is only a starting point)
- [ ] `directive.md` v1: the instructions I give the AI for this build
- [ ] Hand-write `data/board.csv` with about 45 rows **including the edge cases** (below)
- [ ] Write the expected output: which candidates *should* be flagged, and in roughly what order
- [ ] `logs/day-1.md`

### Day 2: Rules engine (no AI)
- [ ] `load.py` + validation (missing dates, bad stage, Hired/Rejected filtered out)
- [ ] `rules.py`: stalled detection + base score
- [ ] Tests against the expected output from Day 1
- [ ] Working rules-only CLI
- [ ] `directive.md` v2, `logs/day-2.md`

### Day 3: AI layer
- [ ] `llm.py`: structured output (score adjustment within the limit, one-sentence reason, next action)
- [ ] Limit enforced in code, not trusted to the prompt
- [ ] Compare AI ranking against the rules-only ranking; log the disagreements
- [ ] `directive.md` v3, `logs/day-3.md`

### Day 4: Drafts + polish
- [ ] `drafts.py`: a follow-up draft per top-N candidate, with approve / edit / skip prompts (cut this if behind)
- [ ] `report.md` export
- [ ] README run instructions verified on a clean venv
- [ ] `logs/day-4.md`

### Day 5: Ship
- [ ] Final `directive.md`
- [ ] `unlearned.md` (one page)
- [ ] Quest Loom (max 5 min): run, ranked list, explain #1 vs #2, approve one draft
- [ ] Career path & leverage video (separate, max 5 min)
- [ ] `logs/day-5.md`, then submit all 7 deliverables

## Edge cases the sample data must contain
- Contacted yesterday, so **not** stalled despite an old stage date
- `last_contact_by = them`, so we owe a reply (should rank high)
- Competing offer mentioned in notes (AI should push it up)
- Missing `last_contact_date` (falls back to `stage_entered_date`)
- Two candidates tied on base score (AI notes should break the tie)
- Hired/Rejected rows (must be ignored)
- Offer stage at exactly 3 days (boundary)

## Done means
Given `data/board.csv`, `python -m stall_alerter data/board.csv` prints a ranked list where every
expected-stalled candidate appears, nobody unexpected appears, and every row has a reason and an action.
It runs in under 30 seconds with an API key, and also runs without one.

## Deliverables checklist
- [ ] Loom: tool working (max 5 min)
- [ ] `intent.md`
- [ ] Final `directive.md`
- [ ] Working code + README
- [ ] `logs/day-1..5.md`
- [ ] `unlearned.md`
- [ ] Career path & leverage video

## Things only I can write
- What I'm unlearning (daily logs + `unlearned.md`)
- Career leverage story (video)
