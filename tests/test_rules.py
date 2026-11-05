"""Checks the sample board against data/EXPECTED.md (today = 2026-11-06, threshold 3)."""

from datetime import date
from pathlib import Path

import pytest

from stall_alerter.load import load_board
from stall_alerter.rank import rank
from stall_alerter.rules import find_stalled

BOARD = Path(__file__).resolve().parent.parent / "data" / "board.csv"
TODAY = date(2026, 11, 6)

EXPECTED_STALLED = {
    "C001", "C002", "C003", "C005", "C006", "C007", "C011", "C014", "C015", "C019", "C020", "C021",
    "C022", "C023", "C028", "C029", "C032", "C034", "C035", "C037", "C040", "C041", "C042", "C046",
}


@pytest.fixture(scope="module")
def board():
    return load_board(BOARD)


@pytest.fixture(scope="module")
def flags(board):
    return {f.candidate.candidate_id: f for f in find_stalled(board.active, TODAY, 3)}


def test_flagged_set_matches_expected(flags):
    assert set(flags) == EXPECTED_STALLED


def test_closed_rows_ignored(board):
    assert board.closed_count == 4
    ids = {c.candidate_id for c in board.active}
    assert not ids & {"C008", "C009", "C026", "C027"}


def test_bad_rows_reported_not_dropped(board):
    problems = dict(board.problems)
    assert set(problems) == {"C044", "C045"}
    assert "stage_entered_date" in problems["C044"]
    assert "Onsite" in problems["C045"]


def test_boundary_is_inclusive(flags):
    assert flags["C002"].days_quiet == 3


def test_recent_contact_resets_clock(flags):
    assert "C004" not in flags  # old stage date, contacted yesterday


def test_waiting_on_us_but_under_threshold_not_flagged(flags):
    assert "C012" not in flags


def test_missing_contact_falls_back_to_stage_date(flags):
    assert flags["C007"].days_quiet == 17


def test_owe_reply_detected(flags):
    assert flags["C003"].owe_reply and not flags["C001"].owe_reply


def test_rules_top_two(flags):
    ranked = rank(list(flags.values()))
    assert [r.flag.candidate.candidate_id for r in ranked[:2]] == ["C001", "C003"]


def test_tie_is_real_and_stable(flags):
    assert flags["C005"].base_score == flags["C006"].base_score
    ranked = [r.flag.candidate.candidate_id for r in rank(list(flags.values()))]
    assert ranked.index("C005") < ranked.index("C006")


def test_days_credit_is_capped(flags):
    # C028 has 22 quiet days at Applied; credit caps at 14 days -> 2*1 + 7 = 9
    assert flags["C028"].base_score == 9


def test_threshold_option(board):
    assert len(find_stalled(board.active, TODAY, 10)) < len(find_stalled(board.active, TODAY, 3))


def test_upload_text_matches_file(board):
    from stall_alerter.load import load_board_text

    text_board = load_board_text(BOARD.read_text(encoding="utf-8"))
    assert len(text_board.active) == len(board.active) and text_board.problems == board.problems


def test_missing_columns_rejected():
    from stall_alerter.load import load_board_text

    with pytest.raises(ValueError, match="missing required columns"):
        load_board_text("candidate_id,name\nC1,X\n")
