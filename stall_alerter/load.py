"""Load and validate the hiring-board CSV."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

REQUIRED_COLUMNS = [
    "candidate_id",
    "name",
    "role",
    "stage",
    "stage_entered_date",
    "last_contact_date",
    "last_contact_by",
    "owner",
    "notes",
]
OPEN_STAGES = ["Applied", "Screening", "Interview", "Final", "Offer"]
CLOSED_STAGES = ["Hired", "Rejected"]


@dataclass
class Candidate:
    candidate_id: str
    name: str
    role: str
    stage: str
    stage_entered: date
    last_contact: date | None
    last_contact_by: str | None  # "us" | "them" | None
    owner: str
    notes: str


@dataclass
class Board:
    active: list[Candidate] = field(default_factory=list)
    closed_count: int = 0
    problems: list[tuple[str, str]] = field(default_factory=list)  # (candidate_id, message)


def _parse_date(value: str) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    return date.fromisoformat(value)


def load_board(path: str | Path) -> Board:
    """Read the CSV. Bad rows are reported in `problems`, never silently dropped."""
    board = Board()
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"CSV is missing required columns: {', '.join(missing)}")

        for line_no, row in enumerate(reader, start=2):
            cid = (row["candidate_id"] or "").strip() or f"line {line_no}"
            stage = (row["stage"] or "").strip()

            if stage in CLOSED_STAGES:
                board.closed_count += 1
                continue
            if stage not in OPEN_STAGES:
                board.problems.append((cid, f"unknown stage '{stage}'"))
                continue

            try:
                stage_entered = _parse_date(row["stage_entered_date"])
                last_contact = _parse_date(row["last_contact_date"])
            except ValueError as e:
                board.problems.append((cid, f"bad date ({e})"))
                continue
            if stage_entered is None:
                board.problems.append((cid, "missing stage_entered_date"))
                continue

            by = (row["last_contact_by"] or "").strip().lower() or None
            if by not in (None, "us", "them"):
                board.problems.append((cid, f"last_contact_by must be 'us' or 'them', got '{by}'"))
                continue

            board.active.append(
                Candidate(
                    candidate_id=cid,
                    name=row["name"].strip(),
                    role=row["role"].strip(),
                    stage=stage,
                    stage_entered=stage_entered,
                    last_contact=last_contact,
                    last_contact_by=by,
                    owner=row["owner"].strip(),
                    notes=(row["notes"] or "").strip(),
                )
            )
    return board
