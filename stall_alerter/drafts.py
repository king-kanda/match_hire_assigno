"""Draft follow-up messages and make a human approve, edit or skip each one. Nothing is ever sent."""

from __future__ import annotations

from typing import Callable

from stall_alerter import llm
from stall_alerter.providers import LLMConfig
from stall_alerter.rank import Ranked


CANDIDATE_LINE = {
    "Applied": "We're reviewing applications now and I'll be in touch with next steps within the next few days.",
    "Screening": "I'd like to set up a short screening call. Could you share a couple of times that work for you this week?",
    "Interview": "I'm pulling together the interview feedback and will come back to you with the next step shortly.",
    "Final": "We're finalising our decision after your final interview and I'll update you very soon.",
    "Offer": "I wanted to check how you're feeling about the offer and whether you have any questions I can answer.",
}


def template_draft(r: Ranked) -> str:
    """Rules-only draft, written to the candidate (the manager's to-do stays in next_action)."""
    c = r.flag.candidate
    first = c.name.split()[0]
    if r.flag.owe_reply:
        body = (f"Hi {first}, apologies for the slow reply to your last message about the {c.role} role. "
                f"I'm on it and will get back to you with a full answer by tomorrow.")
    else:
        body = f"Hi {first}, thanks for your patience with the {c.role} role. {CANDIDATE_LINE[c.stage]}"
    return f"{body}\n\nBest,\n{c.owner}"


def build_drafts(top: list[Ranked], cfg: LLMConfig | None) -> dict[str, str]:
    """cfg=None means templates only."""
    drafts: dict[str, str] = {}
    if cfg:
        items = [
            {
                "candidate_id": r.flag.candidate.candidate_id,
                "name": r.flag.candidate.name,
                "role": r.flag.candidate.role,
                "stage": r.flag.candidate.stage,
                "owner": r.flag.candidate.owner,
                "waiting_on_us": r.flag.owe_reply,
                "notes": r.flag.candidate.notes,
                "next_action": r.next_action,
            }
            for r in top
        ]
        drafts = llm.draft_messages(items, cfg)
    for r in top:
        drafts.setdefault(r.flag.candidate.candidate_id, template_draft(r))
    return drafts


def review(
    top: list[Ranked],
    drafts: dict[str, str],
    ask: Callable[[str], str] = input,
    say: Callable[[str], None] = print,
) -> list[tuple[Ranked, str]]:
    """Show each draft; the human picks [a]pprove, [e]dit or [s]kip. Returns approved (ranked, text) pairs."""
    approved = []
    for i, r in enumerate(top, 1):
        c = r.flag.candidate
        text = drafts[c.candidate_id]
        say(f"\n--- Draft {i}/{len(top)}: {c.name} ({c.stage}, {r.flag.days_quiet}d quiet) ---")
        say(text)
        while True:
            choice = ask("[a]pprove / [e]dit / [s]kip > ").strip().lower()
            if choice in ("a", "approve"):
                approved.append((r, text))
                break
            if choice in ("e", "edit"):
                new = ask("Type the replacement message (one line, \\n for new lines):\n> ")
                if new.strip():
                    text = new.replace("\\n", "\n")
                    say("Updated:\n" + text)
                continue
            if choice in ("s", "skip"):
                break
            say("Please type a, e or s.")
    return approved


def write_approved(approved: list[tuple[Ranked, str]], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Approved follow-ups (NOT sent; copy into your email or ATS)\n\n")
        for r, text in approved:
            c = r.flag.candidate
            f.write(f"## {c.name} ({c.candidate_id}, {c.role}, {c.stage})\n\n{text}\n\n")
