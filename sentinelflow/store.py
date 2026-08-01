"""Thin SQLite persistence layer for cases, evidence, and action approvals."""

import sqlite3

from .config import DB_PATH
from .models import (
    ActionStatus,
    Case,
    CaseStatus,
    Evidence,
    EvidenceCategory,
    ProposedAction,
)

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
CREATE TABLE IF NOT EXISTS actions (
    action_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    decided_by TEXT,
    decided_at TEXT,
    note TEXT,
    executed INTEGER NOT NULL DEFAULT 0
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

    def save_actions(self, actions: list[ProposedAction]) -> None:
        self.conn.executemany(
            "INSERT OR REPLACE INTO actions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    a.action_id,
                    a.case_id,
                    a.description,
                    a.status.value,
                    a.decided_by,
                    a.decided_at.isoformat() if a.decided_at else None,
                    a.note,
                    1 if a.executed else 0,
                )
                for a in actions
            ],
        )
        self.conn.commit()

    def get_action(self, action_id: str) -> ProposedAction | None:
        row = self.conn.execute(
            "SELECT action_id, case_id, description, status, decided_by, "
            "decided_at, note, executed FROM actions WHERE action_id = ?",
            (action_id,),
        ).fetchone()
        if not row:
            return None
        return _row_to_action(row)

    def get_actions(
        self,
        case_id: str | None = None,
        *,
        pending_only: bool = False,
    ) -> list[ProposedAction]:
        sql = (
            "SELECT action_id, case_id, description, status, decided_by, "
            "decided_at, note, executed FROM actions WHERE 1=1"
        )
        params: list = []
        if case_id:
            sql += " AND case_id = ?"
            params.append(case_id)
        if pending_only:
            sql += " AND status = ?"
            params.append(ActionStatus.PENDING.value)
        sql += " ORDER BY action_id"
        rows = self.conn.execute(sql, params).fetchall()
        return [_row_to_action(r) for r in rows]

    def update_action(self, action: ProposedAction) -> None:
        self.conn.execute(
            "UPDATE actions SET status=?, decided_by=?, decided_at=?, note=?, "
            "executed=? WHERE action_id=?",
            (
                action.status.value,
                action.decided_by,
                action.decided_at.isoformat() if action.decided_at else None,
                action.note,
                1 if action.executed else 0,
                action.action_id,
            ),
        )
        self.conn.commit()


def _row_to_action(row) -> ProposedAction:
    from datetime import datetime

    decided_at = datetime.fromisoformat(row[5]) if row[5] else None
    return ProposedAction(
        action_id=row[0],
        case_id=row[1],
        description=row[2],
        status=ActionStatus(row[3]),
        decided_by=row[4],
        decided_at=decided_at,
        note=row[6],
        executed=bool(row[7]),
    )
