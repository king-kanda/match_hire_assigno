"""Stalled detection and base score: plain rules, no AI.

Score = 2 x stage weight + 0.5 x days quiet (capped at 14 days) + 3 if we owe the candidate a reply.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from stall_alerter.load import Candidate

DEFAULT_STALL_DAYS = 3
STAGE_WEIGHT = {"Applied": 1, "Screening": 2, "Interview": 3, "Final": 4, "Offer": 5}
DAYS_CAP = 14
OWE_REPLY_BONUS = 3.0


@dataclass
class Flag:
    candidate: Candidate
    last_movement: date
    days_quiet: int
    owe_reply: bool
    base_score: float


def last_movement(c: Candidate) -> date:
    """A stage change or a logged contact both count as movement."""
    if c.last_contact and c.last_contact > c.stage_entered:
        return c.last_contact
    return c.stage_entered


def base_score(stage: str, days_quiet: int, owe_reply: bool) -> float:
    score = 2 * STAGE_WEIGHT[stage] + 0.5 * min(days_quiet, DAYS_CAP)
    if owe_reply:
        score += OWE_REPLY_BONUS
    return score


def find_stalled(candidates: list[Candidate], today: date, stall_days: int = DEFAULT_STALL_DAYS) -> list[Flag]:
    flags = []
    for c in candidates:
        moved = last_movement(c)
        days = max((today - moved).days, 0)
        if days < stall_days:
            continue
        owe = c.last_contact_by == "them"
        flags.append(Flag(c, moved, days, owe, base_score(c.stage, days, owe)))
    return flags


NEXT_STEP = {
    "Applied": "Screen the CV and either book a phone screen or send a polite decline.",
    "Screening": "Book the screening call or move them to interview.",
    "Interview": "Chase interviewer feedback and tell the candidate the next step.",
    "Final": "Get the hiring decision made and call the candidate with it.",
    "Offer": "Call the candidate today to close the offer or hear their concerns.",
}


def default_reason(f: Flag) -> str:
    """Rules-only explanation, used when AI is off or fails."""
    if f.owe_reply:
        return f"They replied {f.days_quiet} days ago at {f.candidate.stage} stage and are waiting on us."
    return f"No movement for {f.days_quiet} days at {f.candidate.stage} stage."


def default_action(f: Flag) -> str:
    if f.owe_reply:
        return "Reply to their last message today."
    return NEXT_STEP[f.candidate.stage]
