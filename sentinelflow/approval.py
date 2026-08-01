"""Human approval gateway for recommended actions.

Simulated only: approve/reject is recorded in SQLite and artifacts.
Nothing is ever executed against a real firewall, mailbox, or account system.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .models import ActionStatus, CaseStatus, Hypothesis, ProposedAction
from .store import EvidenceStore


def seed_actions_from_hypothesis(
    store: EvidenceStore,
    case_id: str,
    hypothesis: Hypothesis,
) -> list[ProposedAction]:
    """Turn recommended_actions into pending ProposedAction records."""
    actions: list[ProposedAction] = []
    for i, description in enumerate(hypothesis.recommended_actions or [], start=1):
        text = description.strip()
        if not text:
            continue
        actions.append(
            ProposedAction(
                action_id=f"{case_id}-ACT{i:03d}",
                case_id=case_id,
                description=text,
                status=ActionStatus.PENDING,
            )
        )
    if actions:
        store.save_actions(actions)
        store.update_status(case_id, CaseStatus.AWAITING_APPROVAL)
    return actions


def list_actions(
    store: EvidenceStore,
    case_id: str | None = None,
    *,
    pending_only: bool = False,
) -> list[ProposedAction]:
    return store.get_actions(case_id=case_id, pending_only=pending_only)


def decide_action(
    store: EvidenceStore,
    action_id: str,
    *,
    approve: bool,
    decided_by: str = "human",
    note: str | None = None,
) -> ProposedAction:
    """Record an approve/reject decision. Never executes the action."""
    action = store.get_action(action_id)
    if action is None:
        raise RuntimeError(f"Unknown action_id '{action_id}'")
    if action.status != ActionStatus.PENDING:
        raise RuntimeError(
            f"Action {action_id} already decided ({action.status.value})"
        )
    action.status = ActionStatus.APPROVED if approve else ActionStatus.REJECTED
    action.decided_by = decided_by
    action.decided_at = datetime.now(timezone.utc)
    action.note = note
    action.executed = False  # hard rule: simulated only
    store.update_action(action)

    pending = store.get_actions(case_id=action.case_id, pending_only=True)
    if not pending:
        store.update_status(action.case_id, CaseStatus.ACTIONS_REVIEWED)
    return action


def write_actions_artifact(run_dir: Path, actions: list[ProposedAction]) -> Path:
    import json

    path = run_dir / "actions.json"
    path.write_text(
        json.dumps([a.model_dump(mode="json") for a in actions], indent=2, default=str)
    )
    return path
