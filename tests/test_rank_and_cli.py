"""AI clamping, fallback behaviour, drafts review and the CLI end to end (no network)."""

from datetime import date
from pathlib import Path

from stall_alerter import cli, drafts
from stall_alerter.llm import MAX_ADJUSTMENT, Assessment
from stall_alerter.load import load_board
from stall_alerter.rank import rank
from stall_alerter.rules import find_stalled

BOARD = Path(__file__).resolve().parent.parent / "data" / "board.csv"
TODAY = date(2026, 11, 6)


def _flags():
    return find_stalled(load_board(BOARD).active, TODAY, 3)


def test_ai_adjustment_is_clamped():
    flags = _flags()
    target = next(f for f in flags if f.candidate.candidate_id == "C021")
    ai = {"C021": Assessment(candidate_id="C021", adjustment=50, reason="r", next_action="a")}
    r = next(x for x in rank(flags, ai) if x.flag.candidate.candidate_id == "C021")
    assert r.adjustment == MAX_ADJUSTMENT
    assert r.final_score == target.base_score + MAX_ADJUSTMENT
    assert r.source == "ai"


def test_ai_can_break_tie():
    ai = {"C006": Assessment(candidate_id="C006", adjustment=1, reason="r", next_action="a")}
    ids = [r.flag.candidate.candidate_id for r in rank(_flags(), ai)]
    assert ids.index("C006") < ids.index("C005")


def test_unknown_or_missing_ai_rows_fall_back_to_rules():
    ai = {"C999": Assessment(candidate_id="C999", adjustment=2, reason="r", next_action="a")}
    ranked = rank(_flags(), ai)
    assert all(r.source == "rules" for r in ranked)
    assert all(r.reason and r.next_action for r in ranked)


def test_review_approve_edit_skip():
    top = rank(_flags())[:3]
    d = drafts.build_drafts(top, None)
    answers = iter(["a", "e", "New text", "a", "s"])
    approved = drafts.review(top, d, ask=lambda _: next(answers), say=lambda _: None)
    assert [t for _, t in approved][1] == "New text"
    assert len(approved) == 2


def test_cli_rules_only_writes_reports(tmp_path, capsys):
    code = cli.main([str(BOARD), "--today", "2026-11-06", "--no-ai", "--out", str(tmp_path)])
    assert code == 0
    out = capsys.readouterr().out
    assert "24 stalled" in out and "Data problems" in out
    csv_text = (tmp_path / "report.csv").read_text(encoding="utf-8")
    assert csv_text.count("\n") == 25  # header + 24 rows
    assert (tmp_path / "report.md").exists()


def test_cli_missing_file(tmp_path):
    assert cli.main([str(tmp_path / "nope.csv"), "--no-ai"]) == 1
