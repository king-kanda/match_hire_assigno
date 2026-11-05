"""CLI: python -m stall_alerter data/board.csv [--days 3] [--today YYYY-MM-DD] [--no-ai] [--drafts]"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import textwrap
import time
from datetime import date
from pathlib import Path

from stall_alerter import drafts as drafts_mod
from stall_alerter import llm
from stall_alerter.load import load_board
from stall_alerter.rank import Ranked, rank
from stall_alerter.rules import DEFAULT_STALL_DAYS, find_stalled


def parse_args(argv=None):
    p = argparse.ArgumentParser(prog="stall_alerter", description="Find and rank stalled candidates on a hiring board.")
    p.add_argument("csv", help="Path to the hiring-board CSV")
    p.add_argument("--days", type=int, default=DEFAULT_STALL_DAYS, help="Days without movement to count as stalled (default 3)")
    p.add_argument("--today", type=date.fromisoformat, default=None, help="Override today's date (YYYY-MM-DD), for demos and tests")
    p.add_argument("--no-ai", action="store_true", help="Rules-only ranking, no API calls")
    p.add_argument("--drafts", action="store_true", help="Draft follow-ups for the top N and review each one")
    p.add_argument("--top", type=int, default=5, help="How many candidates get drafts (default 5)")
    p.add_argument("--out", default="out", help="Folder for report.md / report.csv (default ./out)")
    return p.parse_args(argv)


def _load_env():
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass


def print_report(ranked: list[Ranked], board, today: date, days: int, used_ai: bool) -> None:
    mode = f"AI-assisted ({llm.MODEL})" if used_ai else "rules only"
    print(f"\nStall Alerter | {today} | threshold {days}d | {mode}")
    print(
        f"{len(board.active)} open candidates, {len(ranked)} stalled, "
        f"{board.closed_count} closed ignored, {len(board.problems)} data problems\n"
    )
    for i, r in enumerate(ranked, 1):
        c = r.flag.candidate
        adj = f" ({r.adjustment:+d} AI)" if r.adjustment else ""
        owe = " | WAITING ON US" if r.flag.owe_reply else ""
        print(f"{i:>2}. {c.name} - {c.role} | {c.stage} | {r.flag.days_quiet}d quiet | score {r.final_score:g}{adj}{owe}")
        print(textwrap.fill(f"Why:  {r.reason}", width=100, initial_indent="    ", subsequent_indent="          "))
        print(textwrap.fill(f"Next: {r.next_action}", width=100, initial_indent="    ", subsequent_indent="          "))
        print(f"    Owner: {c.owner}\n")
    if board.problems:
        print("Data problems (fix these in the board):")
        for cid, msg in board.problems:
            print(f"  - {cid}: {msg}")
        print()


def write_reports(ranked: list[Ranked], board, out_dir: Path, today: date, days: int) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "report.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "candidate_id", "name", "role", "stage", "owner", "days_quiet", "waiting_on_us",
                    "base_score", "ai_adjustment", "final_score", "reason", "next_action", "source"])
        for i, r in enumerate(ranked, 1):
            c = r.flag.candidate
            w.writerow([i, c.candidate_id, c.name, c.role, c.stage, c.owner, r.flag.days_quiet, r.flag.owe_reply,
                        r.flag.base_score, r.adjustment, r.final_score, r.reason, r.next_action, r.source])

    with open(out_dir / "report.md", "w", encoding="utf-8") as f:
        f.write(f"# Stalled candidates ({today}, threshold {days} days)\n\n")
        f.write("| # | Candidate | Stage | Days quiet | Score | Why | Next action | Owner |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for i, r in enumerate(ranked, 1):
            c = r.flag.candidate
            adj = f" ({r.adjustment:+d})" if r.adjustment else ""
            f.write(f"| {i} | {c.name} ({c.role}) | {c.stage} | {r.flag.days_quiet} | {r.final_score:g}{adj} "
                    f"| {r.reason} | {r.next_action} | {c.owner} |\n")
        if board.problems:
            f.write("\n## Data problems\n\n")
            for cid, msg in board.problems:
                f.write(f"- {cid}: {msg}\n")


def main(argv=None) -> int:
    args = parse_args(argv)
    _load_env()
    today = args.today or date.today()

    try:
        board = load_board(args.csv)
    except (OSError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    flags = find_stalled(board.active, today, args.days)
    use_ai = not args.no_ai
    ai = {}
    if use_ai and flags:
        print(f"Asking {llm.MODEL} to review {len(flags)} stalled candidates...", file=sys.stderr)
        t0 = time.time()
        ai = llm.assess(flags)
        print(f"Done in {time.time() - t0:.1f}s.", file=sys.stderr)
    ranked = rank(flags, ai)
    used_ai = bool(ai)

    print_report(ranked, board, today, args.days, used_ai)
    out_dir = Path(args.out)
    write_reports(ranked, board, out_dir, today, args.days)
    print(f"Saved {out_dir / 'report.md'} and {out_dir / 'report.csv'}")

    if args.drafts and ranked:
        top = ranked[: args.top]
        drafts = drafts_mod.build_drafts(top, use_ai=use_ai)
        approved = drafts_mod.review(top, drafts)
        path = out_dir / "approved_drafts.md"
        drafts_mod.write_approved(approved, str(path))
        print(f"\n{len(approved)} of {len(top)} drafts approved. Saved to {path} (nothing was sent).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
