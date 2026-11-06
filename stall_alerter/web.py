"""Web UI: FastAPI + HTMX. Run: python -m stall_alerter.web  (then open http://127.0.0.1:8000)

Same engine as the CLI. The server renders HTML fragments; HTMX swaps them into the page, so there is
no JS build. Runs and draft approvals are kept in memory (single-user local tool). Nothing is ever sent.
"""

from __future__ import annotations

import os
import secrets
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from stall_alerter import drafts as drafts_mod
from stall_alerter import llm
from stall_alerter.load import Board, load_board, load_board_text
from stall_alerter.providers import PROVIDERS, LLMConfig, detect_provider, resolve
from stall_alerter.rank import Ranked, rank
from stall_alerter.rules import DEFAULT_STALL_DAYS, find_stalled

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

HERE = Path(__file__).parent
SAMPLE = HERE.parent / "data" / "board.csv"
SAMPLE_TODAY = date(2026, 11, 6)
RULES_ONLY = "rules"
MAX_RUNS = 20

app = FastAPI(title="Stall Alerter")
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
templates = Jinja2Templates(directory=HERE / "templates")


@dataclass
class Run:
    id: str
    board: Board
    ranked: list[Ranked]
    cfg: LLMConfig | None
    today: date
    days: int
    source: str
    warning: str | None = None
    drafts: dict[str, str] = field(default_factory=dict)
    status: dict[str, str] = field(default_factory=dict)  # candidate_id -> pending | approved | skipped

    def by_id(self) -> dict[str, Ranked]:
        return {r.flag.candidate.candidate_id: r for r in self.ranked}

    def counts(self) -> dict[str, int]:
        values = list(self.status.values())
        return {s: values.count(s) for s in ("pending", "approved", "skipped")}


RUNS: OrderedDict[str, Run] = OrderedDict()


def _save(run: Run) -> None:
    RUNS[run.id] = run
    while len(RUNS) > MAX_RUNS:
        RUNS.popitem(last=False)


def _get(run_id: str) -> Run:
    run = RUNS.get(run_id)
    if run is None:
        raise HTTPException(404, "Run not found (the server may have restarted). Run the board again.")
    return run


def _provider_context(provider: str) -> dict:
    if provider == RULES_ONLY or provider not in PROVIDERS:
        return {"provider": RULES_ONLY}
    info = PROVIDERS[provider]
    return {"provider": provider, "default_model": info.default_model, "key_env": info.key_env,
            "key_loaded": bool(os.getenv(info.key_env))}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    default_provider = detect_provider()  # LLM_PROVIDER, else first provider with a key, else rules only
    if default_provider not in PROVIDERS:
        default_provider = RULES_ONLY
    return templates.TemplateResponse(request, "index.html", {
        "providers": list(PROVIDERS), "rules_only": RULES_ONLY, "sample_today": SAMPLE_TODAY.isoformat(),
        "default_days": DEFAULT_STALL_DAYS, **_provider_context(default_provider),
    })


@app.get("/provider-fields", response_class=HTMLResponse)
def provider_fields(request: Request, provider: str = RULES_ONLY):
    return templates.TemplateResponse(request, "_provider_fields.html", _provider_context(provider))


@app.post("/run", response_class=HTMLResponse)
async def run_board(
    request: Request,
    today: str = Form(...),
    days: int = Form(DEFAULT_STALL_DAYS),
    provider: str = Form(RULES_ONLY),
    model: str = Form(""),
    api_key: str = Form(""),
    csv_file: UploadFile | None = File(None),
):
    def error(msg: str):
        return templates.TemplateResponse(request, "_error.html", {"message": msg})

    try:
        today_d = date.fromisoformat(today)
    except ValueError:
        return error(f"'{today}' is not a valid date.")
    if not 1 <= days <= 60:
        return error("Threshold must be between 1 and 60 days.")

    try:
        if csv_file is not None and csv_file.filename:
            board = load_board_text((await csv_file.read()).decode("utf-8"))
            source = csv_file.filename
        else:
            board, source = load_board(SAMPLE), "sample board (data/board.csv)"
    except (ValueError, UnicodeDecodeError) as e:
        return error(f"Could not read the CSV: {e}")

    cfg = None
    if provider != RULES_ONLY:
        if provider not in PROVIDERS:
            return error(f"Unknown provider '{provider}'.")
        if api_key.strip():  # local single-user tool: key lives in this process only, never stored on disk
            os.environ[PROVIDERS[provider].key_env] = api_key.strip()
        cfg = resolve(provider, model.strip() or None)

    flags = find_stalled(board.active, today_d, days)
    ai = llm.assess(flags, cfg) if cfg and flags else {}
    warning = None
    if cfg and flags and not ai:
        warning = f"{cfg.label} gave no usable answer (check the key or model id). Showing the rules-only ranking."

    run = Run(secrets.token_urlsafe(8), board, rank(flags, ai), cfg if ai else None, today_d, days, source, warning)
    _save(run)
    return templates.TemplateResponse(request, "_results.html", {"run": run})


@app.post("/runs/{run_id}/drafts", response_class=HTMLResponse)
def make_drafts(request: Request, run_id: str, top_n: int = Form(5)):
    run = _get(run_id)
    top = run.ranked[: max(1, min(top_n, len(run.ranked)))]
    run.drafts = drafts_mod.build_drafts(top, run.cfg)
    run.status = {cid: "pending" for cid in run.drafts}
    return templates.TemplateResponse(request, "_drafts.html", {"run": run})


def _set_status(request: Request, run_id: str, cid: str, status: str, text: str | None = None):
    run = _get(run_id)
    if cid not in run.drafts:
        raise HTTPException(404, "Draft not found.")
    if text is not None and text.strip():
        run.drafts[cid] = text.strip()
    run.status[cid] = status
    return templates.TemplateResponse(request, "_draft_card.html",
                                      {"run": run, "r": run.by_id()[cid], "oob_counter": True})


@app.post("/runs/{run_id}/drafts/{cid}/approve", response_class=HTMLResponse)
def approve(request: Request, run_id: str, cid: str, text: str = Form("")):
    return _set_status(request, run_id, cid, "approved", text)


@app.post("/runs/{run_id}/drafts/{cid}/skip", response_class=HTMLResponse)
def skip(request: Request, run_id: str, cid: str, text: str = Form("")):
    return _set_status(request, run_id, cid, "skipped", text)


@app.post("/runs/{run_id}/drafts/{cid}/undo", response_class=HTMLResponse)
def undo(request: Request, run_id: str, cid: str):
    return _set_status(request, run_id, cid, "pending")


@app.get("/runs/{run_id}/approved.md")
def download_approved(run_id: str):
    run = _get(run_id)
    by_id = run.by_id()
    approved = [(by_id[cid], run.drafts[cid]) for cid, s in run.status.items() if s == "approved"]
    md = "# Approved follow-ups (NOT sent; copy into your email or ATS)\n\n" + "".join(
        f"## {r.flag.candidate.name} ({r.flag.candidate.candidate_id}, {r.flag.candidate.role})\n\n{text}\n\n"
        for r, text in approved
    )
    return Response(md, media_type="text/markdown",
                    headers={"Content-Disposition": 'attachment; filename="approved_drafts.md"'})


def main() -> None:
    import argparse

    import uvicorn

    p = argparse.ArgumentParser(description="Stall Alerter web UI")
    p.add_argument("--port", type=int, default=8000)
    args = p.parse_args()
    print(f"Stall Alerter UI: http://127.0.0.1:{args.port}")
    uvicorn.run(app, host="127.0.0.1", port=args.port)  # localhost only: keys can be typed into the page


if __name__ == "__main__":
    main()
