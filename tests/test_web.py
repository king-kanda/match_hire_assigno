"""Web UI (FastAPI + HTMX) through the HTTP layer, no network, no keys."""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from stall_alerter.web import app

BOARD = Path(__file__).resolve().parent.parent / "data" / "board.csv"
client = TestClient(app)


def _run(**extra):
    data = {"today": "2026-11-06", "days": "3", "provider": "rules", **extra.pop("data", {})}
    return client.post("/run", data=data, **extra)


def _run_id(html: str) -> str:
    return re.search(r'/runs/([\w-]+)/drafts"', html).group(1)


def _stat(html: str, sid: str) -> str:
    return re.search(rf'id="{sid}">(\d+)<', html).group(1)


def test_index_serves_page_and_htmx():
    page = client.get("/")
    assert page.status_code == 200 and 'hx-post="/run"' in page.text
    assert client.get("/static/htmx.min.js").status_code == 200
    assert client.get("/static/style.css").status_code == 200


def test_sample_board_results():
    html = _run().text
    assert _stat(html, "stat-stalled") == "24"
    assert _stat(html, "stat-waiting") == "4"
    assert _stat(html, "stat-problems") == "2"
    ids = re.findall(r'<tr class="[^"]*" data-id="(C\d+)"', html)
    assert ids[:2] == ["C001", "C003"] and len(ids) == 24
    assert "rules only" in html and "C044" in html and "Onsite" in html


def test_upload_csv():
    with open(BOARD, "rb") as f:
        html = _run(files={"csv_file": ("my_board.csv", f, "text/csv")}).text
    assert "my_board.csv" in html and _stat(html, "stat-stalled") == "24"


def test_bad_csv_and_bad_date_show_errors():
    html = _run(files={"csv_file": ("bad.csv", b"candidate_id,name\nC1,X\n", "text/csv")}).text
    assert "missing required columns" in html
    assert "not a valid date" in client.post("/run", data={"today": "nope", "provider": "rules"}).text


def test_notes_are_html_escaped():
    csv = (BOARD.read_text(encoding="utf-8").splitlines()[0] + "\n"
           "X1,<script>alert(1)</script>,Dev,Offer,2026-10-01,,,Amina,\n")
    html = _run(files={"csv_file": ("x.csv", csv.encode(), "text/csv")}).text
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html


def test_provider_without_key_falls_back(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    html = _run(data={"provider": "groq", "model": "some-model"}).text
    assert "gave no usable answer" in html and "rules only" in html


def test_provider_fields_partial():
    assert 'name="model"' in client.get("/provider-fields", params={"provider": "openai"}).text
    assert 'name="model"' not in client.get("/provider-fields", params={"provider": "rules"}).text


def test_drafts_approve_edit_skip_undo_download():
    rid = _run_id(_run().text)
    drafts = client.post(f"/runs/{rid}/drafts", data={"top_n": "5"}).text
    assert drafts.count('class="card status-pending"') == 5
    assert "0</b> approved" in drafts and "5</b> pending" in drafts

    card = client.post(f"/runs/{rid}/drafts/C001/approve", data={"text": "Edited by the manager."}).text
    assert "status-approved" in card and "Edited by the manager." in card
    assert 'hx-swap-oob="true"' in card and "1</b> approved" in card

    card = client.post(f"/runs/{rid}/drafts/C003/skip", data={"text": ""}).text
    assert "status-skipped" in card and "1</b> skipped" in card

    md = client.get(f"/runs/{rid}/approved.md")
    assert md.status_code == 200 and "Edited by the manager." in md.text and "Grace" not in md.text

    card = client.post(f"/runs/{rid}/drafts/C001/undo").text
    assert "status-pending" in card and "0</b> approved" in card


@pytest.mark.parametrize("path", ["/runs/nope/drafts", "/runs/nope/drafts/C001/approve"])
def test_unknown_run_404(path):
    assert client.post(path, data={"top_n": "5", "text": ""}).status_code == 404
