"""Claude layer: limited score adjustment, reason, next action. TODO (Day 3)."""

MODEL = "claude-sonnet-5-5"
MAX_ADJUSTMENT = 2  # AI may move a score by at most this much; enforced in code
