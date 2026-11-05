# Intent

> DRAFT from the planning session. Rewrite this in your own words on Day 1.

**Who:** A hiring manager juggling 40+ active candidates across several roles.

**Problem:** Candidates quietly go cold. Nobody notices someone has sat in "Offer" or "Final" for days,
or that a candidate replied and we never answered, until they withdraw.

**What I'm building:** A small tool that reads the hiring-board CSV, flags anyone with no movement for
3+ days, and tells the manager **who to chase first and exactly what to do**, in about 5 minutes of reading.

**Where AI is used, and where it isn't:**
- Not used: deciding who is stalled (date arithmetic) or the base priority (rules).
- Used: reading free-text notes to adjust priority within a limit, and writing the reason, the next action and an optional draft message.
- A human approves every draft. Nothing is sent automatically.

**Success:** _(fill in: the one sentence a reviewer can check in the Loom)_

**Out of scope:** sending messages, ATS integrations, a web UI.
