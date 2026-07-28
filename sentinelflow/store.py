"""Thin SQLite persistence layer for cases and evidence."""

import sqlite3

from .config import DB_PATH
from .models import Case, CaseStatus, Evidence, EvidenceCategory

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    source_files TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    category TEXT NOT NULL,
    label TEXT NOT NULL,
    value TEXT NOT NULL,
    source_location TEXT NOT NULL
);
"""


class EvidenceStore:
    def __init__(self, db_path: str = DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.executescript(_SCHEMA)

    def save_case(self, case: Case) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO cases VALUES (?, ?, ?, ?)",
            (
                case.case_id,
                ",".join(case.source_files),
                case.status.value,
                case.created_at.isoformat(),
            ),
        )
        self.conn.commit()

    def update_status(self, case_id: str, status: CaseStatus) -> None:
        self.conn.execute(
            "UPDATE cases SET status = ? WHERE case_id = ?", (status.value, case_id)
        )
        self.conn.commit()

    def save_evidence(self, items: list[Evidence]) -> None:
        self.conn.executemany(
            "INSERT OR REPLACE INTO evidence VALUES (?, ?, ?, ?, ?, ?)",
            [
                (e.id, e.case_id, e.category.value, e.label, e.value, e.source_location)
                for e in items
            ],
        )
        self.conn.commit()

    def get_evidence(self, case_id: str) -> list[Evidence]:
        rows = self.conn.execute(
            "SELECT id, case_id, category, label, value, source_location "
            "FROM evidence WHERE case_id = ? ORDER BY id",
            (case_id,),
        ).fetchall()
        return [
            Evidence(
                id=r[0],
                case_id=r[1],
                category=EvidenceCategory(r[2]),
                label=r[3],
                value=r[4],
                source_location=r[5],
            )
            for r in rows
        ]

    def get_evidence_by_ids(self, case_id: str, ids: list[str]) -> dict[str, Evidence]:
        all_evidence = {e.id: e for e in self.get_evidence(case_id)}
        return {i: all_evidence[i] for i in ids if i in all_evidence}

    def evidence_ids(self, case_id: str) -> set[str]:
        rows = self.conn.execute(
            "SELECT id FROM evidence WHERE case_id = ?", (case_id,)
        ).fetchall()
        return {r[0] for r in rows}
