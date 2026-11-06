# Intent

**Status:** working version. This is the reference for what the tool is meant to do; `plan.md` is
background (decision history and timeline).

**Quest format:** C, the stall alerter.

**Who:** A hiring manager juggling 40+ active candidates across several roles, checking the board in
short bursts between other work.

**Problem:** Candidates quietly go cold. Nobody notices someone has sat in "Offer" or "Final" for days,
or that a candidate replied and we never answered, until they withdraw.

**What I'm building:** A small tool that reads the hiring-board CSV, flags anyone with no movement for
3+ days, and tells the manager **who to chase first and exactly what to do**, in about 5 minutes of reading.
The manager uses it through a simple web page (upload the board, see the ranked list, approve drafts);
the same engine also runs from the command line.

**Key decisions**
- **Stalled** = no movement for 3+ days (adjustable). Movement = a stage change **or** a logged contact.
- **Who goes first** is a rules score: later stage counts more, longer silence counts more (capped),
  and a candidate waiting on *our* reply gets a bonus.
- **The AI can only nudge** that score by ±2, enforced in code, based on the notes (competing offer,
  referral, mismatch). It never decides who is stalled.
- **Any LLM**: Anthropic, OpenAI, Groq or OpenRouter, with no fixed default. With no key it runs rules-only,
  so the tool always works.
- **Bad data is shown**, not silently dropped (missing dates, unknown stages).

**Where AI is used, and where it isn't:**
- Not used: deciding who is stalled (date arithmetic) or the base priority (rules).
- Used: reading free-text notes to adjust priority within the ±2 limit, and writing the reason, the next
  action and an optional draft message.
- A human approves, edits or skips every draft. Nothing is sent automatically.

**Success:** On the 46-row sample board, one run (web UI or CLI) flags exactly the 24 expected candidates
(see `data/EXPECTED.md`), puts the two most urgent (an Offer gone quiet and a candidate waiting on our reply)
in the top 2, gives every row a reason and a next action, and still works with no API key.

**Out of scope:** sending messages (drafts are approved and exported, never sent), ATS integrations,
user accounts / multi-user hosting (it's a local, single-user tool), saving runs between restarts.
