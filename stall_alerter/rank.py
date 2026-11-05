"""Combine rule scores with (clamped) AI adjustments into the final order."""

from __future__ import annotations

from dataclasses import dataclass

from stall_alerter.llm import MAX_ADJUSTMENT, Assessment
from stall_alerter.rules import Flag, default_action, default_reason


@dataclass
class Ranked:
    flag: Flag
    adjustment: int
    final_score: float
    reason: str
    next_action: str
    source: str  # "ai" or "rules"


def clamp(n: int, limit: int = MAX_ADJUSTMENT) -> int:
    return max(-limit, min(limit, int(n)))


def rank(flags: list[Flag], ai: dict[str, Assessment] | None = None) -> list[Ranked]:
    ai = ai or {}
    out = []
    for f in flags:
        a = ai.get(f.candidate.candidate_id)
        if a:
            adj = clamp(a.adjustment)
            out.append(Ranked(f, adj, f.base_score + adj, a.reason.strip(), a.next_action.strip(), "ai"))
        else:
            out.append(Ranked(f, 0, f.base_score, default_reason(f), default_action(f), "rules"))
    # Highest score first; ties go to whoever has waited longer, then by id for a stable order.
    out.sort(key=lambda r: (-r.final_score, -r.flag.days_quiet, r.flag.candidate.candidate_id))
    return out
