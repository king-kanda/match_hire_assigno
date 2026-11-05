"""AI layer: reads notes, suggests a limited score adjustment, a reason and a next action.

The AI never decides who is stalled; rules do that. Its adjustment is clamped in rank.py,
so the prompt is not trusted to enforce the limit. The provider/model is pluggable (see providers.py).
"""

from __future__ import annotations

import json

from pydantic import BaseModel

from stall_alerter.providers import LLMConfig, complete_json
from stall_alerter.rules import Flag

MAX_ADJUSTMENT = 2  # enforced in rank.py

SYSTEM = f"""You help a busy hiring manager decide which stalled candidates to follow up first.
You get a list of candidates who have had no movement for several days, each with a rules-based
base score. For each candidate return:
- adjustment: an integer from -{MAX_ADJUSTMENT} to +{MAX_ADJUSTMENT}. Use it ONLY when the notes give a
  concrete reason (competing offer, counter-offer, interviewing elsewhere, referral => up;
  clear mismatch or explicit flexibility on timing => down). Otherwise 0.
- reason: one sentence, under 25 words, saying why this person needs attention. Cite the notes if they matter.
- next_action: one concrete action the manager can do today, under 20 words.
Do not invent facts that are not in the data. Return every candidate_id you were given exactly once."""


class Assessment(BaseModel):
    candidate_id: str
    adjustment: int
    reason: str
    next_action: str


class AssessmentBatch(BaseModel):
    assessments: list[Assessment]


class Draft(BaseModel):
    candidate_id: str
    message: str


class DraftBatch(BaseModel):
    drafts: list[Draft]


def _flag_payload(f: Flag) -> dict:
    c = f.candidate
    return {
        "candidate_id": c.candidate_id,
        "name": c.name,
        "role": c.role,
        "stage": c.stage,
        "days_quiet": f.days_quiet,
        "waiting_on_us": f.owe_reply,
        "base_score": f.base_score,
        "notes": c.notes,
    }


def assess(flags: list[Flag], cfg: LLMConfig, client=None) -> dict[str, Assessment]:
    """One call for the whole stalled list. Returns {} on any failure (caller falls back to rules)."""
    if not flags:
        return {}
    user = json.dumps([_flag_payload(f) for f in flags], indent=1)
    result = complete_json(cfg, SYSTEM, user, AssessmentBatch, client)
    return {a.candidate_id: a for a in result.assessments} if result else {}


DRAFT_SYSTEM = """You draft short follow-up messages from a hiring manager to candidates.
Each message: 2-4 sentences, warm and specific, plain text, no subject line, no placeholders like [Name].
Address the candidate by first name and sign off as the given owner. Base it on the stage, the notes
and the suggested next action. Never promise an offer, salary or outcome that is not in the data.
Return one draft per candidate_id."""


def draft_messages(items: list[dict], cfg: LLMConfig, client=None) -> dict[str, str]:
    """items: dicts with candidate_id, name, role, stage, owner, notes, next_action. Returns {} on failure."""
    if not items:
        return {}
    result = complete_json(cfg, DRAFT_SYSTEM, json.dumps(items, indent=1), DraftBatch, client)
    return {d.candidate_id: d.message for d in result.drafts} if result else {}
