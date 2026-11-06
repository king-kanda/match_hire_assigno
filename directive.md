# Directive

> Versioned. Keep earlier versions below so the changes are visible.
> v1 is an AI-drafted starting point. Rewrite it in your own words and record what you changed.

## v1
**Role:** You are building a small tool (web UI + CLI on one engine) for a hiring manager with 40+ candidates. Optimise for
"can act on it in 5 minutes," not for features.

**Rules for the build**
1. Write the expected output (`data/EXPECTED.md`) **before** the logic, and make tests prove it.
2. Anything that can be computed (dates, thresholds, scores) is plain code. The LLM only handles
   judgment on free text: reading notes, writing reasons, actions and drafts.
3. Never trust the prompt to enforce a limit. Clamp AI output in code (±2 score adjustment).
4. Every AI step must have a rules-only fallback. The demo must work offline.
5. Bad data is reported, never silently dropped.
6. Nothing is sent. Drafts always go through approve / edit / skip by a human.
7. One batched API call per step (not one per candidate), structured output via a Pydantic schema.
8. The LLM is swappable (Anthropic, OpenAI, Groq, OpenRouter). No provider-specific logic outside `providers.py`,
   and every response is validated against the schema before it is used.

**How to check the work**
- `pytest` passes, the flagged set equals `EXPECTED.md`, and the top 2 are the expected two.
- Run once with the AI and once with `--no-ai`; read the differences and log the ones that are wrong.

**Never**
- Let the AI decide who is stalled.
- Invent facts not in the CSV (no made-up salaries, dates or promises in drafts).
