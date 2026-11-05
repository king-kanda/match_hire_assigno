"""Draft follow-up messages and make a human approve, edit or skip each one. Nothing is ever sent."""

from __future__ import annotations

from typing import Callable

from stall_alerter import llm
from stall_alerter.rank import Ranked


def template_draft(r: Ranked) -> str:
    c = r.flag.candidate
    first = c.name.split()[0]
    if r.flag.owe_reply:
        opener = f"Hi {first}, apologies for the slow reply on your last message."
    else:
        opener = f"Hi {first}, I wanted to check in on your application for the {c.role} role."
    return f"{opener} {r.next_action} Happy to answer any questions in the meantime.\n\n{c.owner}"


def build_drafts(top: list[Ranked], use_ai: bool) -> dict[str, str]:
    drafts: dict[str, str] = {}
    if use_ai:
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
        drafts = llm.draft_messages(items)
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
