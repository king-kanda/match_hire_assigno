"""Stall Alerter web UI (Streamlit). Run: streamlit run app.py

Same engine as the CLI: rules find stalled candidates, an optional LLM adjusts priority (clamped)
and writes reasons and drafts, and a human approves, edits or skips every draft. Nothing is sent.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import streamlit as st

from stall_alerter import drafts as drafts_mod
from stall_alerter import llm
from stall_alerter.load import load_board, load_board_text
from stall_alerter.providers import PROVIDERS, resolve
from stall_alerter.rank import rank
from stall_alerter.rules import DEFAULT_STALL_DAYS, find_stalled

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

SAMPLE = Path(__file__).parent / "data" / "board.csv"
SAMPLE_TODAY = date(2026, 11, 6)
RULES_ONLY = "Rules only (no AI)"

st.set_page_config(page_title="Stall Alerter", layout="wide")
ss = st.session_state

# ---------------- Sidebar: inputs ----------------
with st.sidebar:
    st.header("Board")
    upload = st.file_uploader("Upload a hiring-board CSV", type="csv", help="Leave empty to use the sample board.")
    st.caption("Using the sample board (data/board.csv)" if upload is None else f"Using {upload.name}")
    today = st.date_input("Today", value=SAMPLE_TODAY if upload is None else date.today(),
                          help="The sample board is dated around 2026-11-06.")
    days = st.slider("Stalled after (days without movement)", 1, 14, DEFAULT_STALL_DAYS)

    st.header("AI")
    provider_choice = st.selectbox("Provider", [RULES_ONLY, *PROVIDERS], index=1)
    cfg = None
    if provider_choice != RULES_ONLY:
        info = PROVIDERS[provider_choice]
        model = st.text_input("Model", value=info.default_model)
        if not os.getenv(info.key_env):
            key = st.text_input(f"{info.key_env}", type="password", help="Not saved; used for this session only.")
            if key:
                os.environ[info.key_env] = key
        else:
            st.caption(f"{info.key_env} loaded from environment")
        cfg = resolve(provider_choice, model)

    run = st.button("Find stalled candidates", type="primary", use_container_width=True)

# ---------------- Run the engine ----------------
if run:
    try:
        board = load_board_text(upload.getvalue().decode("utf-8")) if upload else load_board(SAMPLE)
    except (ValueError, UnicodeDecodeError) as e:
        st.error(f"Could not read the CSV: {e}")
        st.stop()
    flags = find_stalled(board.active, today, days)
    ai = {}
    if cfg and flags:
        with st.spinner(f"Asking {cfg.label} to review {len(flags)} stalled candidates..."):
            ai = llm.assess(flags, cfg)
        if not ai:
            st.warning(f"{cfg.label} gave no usable answer (check the key/model). Showing rules-only ranking.")
    ss.board, ss.ranked, ss.cfg = board, rank(flags, ai), (cfg if ai else None)
    ss.today, ss.days = today, days
    ss.drafts, ss.status = {}, {}

st.title("Stall Alerter")
st.caption("Who on the hiring board has gone quiet, who to chase first, and what to do.")

if "ranked" not in ss:
    st.info("Pick a board and a provider in the sidebar, then press **Find stalled candidates**.")
    st.stop()

board, ranked = ss.board, ss.ranked

# ---------------- Summary + ranked list ----------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Open candidates", len(board.active))
c2.metric(f"Stalled ({ss.days}+ days)", len(ranked))
c3.metric("Waiting on us", sum(r.flag.owe_reply for r in ranked))
c4.metric("Data problems", len(board.problems))
st.caption(f"Ranking: {'AI-assisted (' + ss.cfg.label + ')' if ss.cfg else 'rules only'} | today = {ss.today}")

rows = [
    {
        "#": i,
        "Candidate": r.flag.candidate.name,
        "Role": r.flag.candidate.role,
        "Stage": r.flag.candidate.stage,
        "Days quiet": r.flag.days_quiet,
        "Waiting on us": "yes" if r.flag.owe_reply else "",
        "Score": r.final_score,
        "AI adj.": f"{r.adjustment:+d}" if r.adjustment else "",
        "Why": r.reason,
        "Next action": r.next_action,
        "Owner": r.flag.candidate.owner,
    }
    for i, r in enumerate(ranked, 1)
]
st.dataframe(rows, hide_index=True)

if board.problems:
    with st.expander(f"Data problems ({len(board.problems)}): fix these in the board"):
        for cid, msg in board.problems:
            st.write(f"- **{cid}**: {msg}")

# ---------------- Drafts + human approval ----------------
st.divider()
st.subheader("Follow-up drafts")
st.caption("Every draft needs your approval. Nothing is sent: approved messages are exported for you to copy.")

top_n = st.number_input("Draft for the top N", min_value=1, max_value=max(1, len(ranked)), value=min(5, max(1, len(ranked))))
if st.button("Generate drafts"):
    top = ranked[: int(top_n)]
    with st.spinner("Drafting..." if ss.cfg else "Building template drafts..."):
        ss.drafts = drafts_mod.build_drafts(top, ss.cfg)
    ss.status = {cid: "pending" for cid in ss.drafts}
    for cid, text in ss.drafts.items():
        ss[f"draft_{cid}"] = text

by_id = {r.flag.candidate.candidate_id: r for r in ranked}
for cid in ss.drafts:
    r = by_id[cid]
    c = r.flag.candidate
    status = ss.status[cid]
    badge = {"pending": "PENDING", "approved": "APPROVED", "skipped": "SKIPPED"}[status]
    with st.container(border=True):
        st.markdown(f"**{c.name}** - {c.role} | {c.stage} | {r.flag.days_quiet}d quiet | owner {c.owner} | `{badge}`")
        st.caption(f"Next action: {r.next_action}")
        st.text_area("Message (edit freely)", key=f"draft_{cid}", height=130, disabled=status != "pending")
        b1, b2, b3, _ = st.columns([1, 1, 1, 5])
        if status == "pending":
            if b1.button("Approve", key=f"ok_{cid}", type="primary"):
                ss.status[cid] = "approved"
                st.rerun()
            if b2.button("Skip", key=f"skip_{cid}"):
                ss.status[cid] = "skipped"
                st.rerun()
        elif b3.button("Undo", key=f"undo_{cid}"):
            ss.status[cid] = "pending"
            st.rerun()

approved = [(by_id[cid], ss[f"draft_{cid}"]) for cid, s in ss.status.items() if s == "approved"]
if ss.drafts:
    st.write(f"**{len(approved)}** approved, **{sum(s == 'skipped' for s in ss.status.values())}** skipped, "
             f"**{sum(s == 'pending' for s in ss.status.values())}** pending.")
    if approved:
        md = "# Approved follow-ups (NOT sent; copy into your email or ATS)\n\n" + "".join(
            f"## {r.flag.candidate.name} ({r.flag.candidate.candidate_id}, {r.flag.candidate.role})\n\n{text}\n\n"
            for r, text in approved
        )
        st.download_button("Download approved drafts (.md)", md, file_name="approved_drafts.md")
