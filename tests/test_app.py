"""Drives the Streamlit UI headlessly: run on the sample board (rules only), draft, approve, skip."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def _run_rules_only():
    at = AppTest.from_file(APP, default_timeout=120).run()
    assert not at.exception
    at.sidebar.selectbox[0].select("Rules only (no AI)").run()
    at.sidebar.button[0].click().run()
    assert not at.exception
    return at


def test_sample_board_loads_and_ranks():
    at = _run_rules_only()
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Open candidates"] == "40"
    assert metrics["Stalled (3+ days)"] == "24"
    assert metrics["Data problems"] == "2"


def test_draft_approve_and_skip():
    at = _run_rules_only()
    gen = next(b for b in at.button if b.label == "Generate drafts")
    gen.click().run()
    assert len(at.text_area) == 5
    at.button(key="ok_C001").click().run()
    at.button(key="skip_C003").click().run()
    assert not at.exception
    assert any("1** approved" in m.value and "1** skipped" in m.value for m in at.markdown)


def test_metrics_match_testing_guide():
    at = _run_rules_only()
    assert {m.label: m.value for m in at.metric}["Waiting on us"] == "4"
