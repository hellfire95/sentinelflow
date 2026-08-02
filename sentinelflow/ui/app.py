"""SentinelFlow Stage 8 — epic manuscript UI.

Launch from repo root:
  .venv/bin/streamlit run sentinelflow/ui/app.py
"""

from __future__ import annotations

import html
import json
import sys
import tempfile
import time
from pathlib import Path

import streamlit as st

# Allow `streamlit run sentinelflow/ui/app.py` from repo root.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sentinelflow.approval import decide_action, list_actions
from sentinelflow.pipeline import run_case
from sentinelflow.store import EvidenceStore
from sentinelflow.ui.theme import hero_html, inject, path_html, section_html

STEPS_ORDER = ["parse", "enrich", "investigate", "critic", "report", "approve"]

SAMPLE_CASES = [
    {
        "key": "q2_1",
        "label": "Phishing email",
        "path": ROOT / "datasets/agent_inputs/Q2_1.eml",
        "hint": "Classic lure with links & auth fails",
    },
    {
        "key": "bank",
        "label": "Bank lure",
        "path": ROOT / "datasets/agent_inputs/phishing_bank_lure.eml",
        "hint": "Credential-harvest style mail",
    },
    {
        "key": "benign",
        "label": "Benign mail",
        "path": ROOT / "datasets/agent_inputs/benign_legit_mail.eml",
        "hint": "Should lean not-phishing",
    },
    {
        "key": "eve",
        "label": "Suricata eve",
        "path": ROOT / "datasets/agent_inputs/sample_eve.json",
        "hint": "Network alerts as evidence",
    },
]


class _UploadProxy:
    """Minimal stand-in for st.UploadedFile from a local sample path."""

    def __init__(self, path: Path):
        self.name = path.name
        self._bytes = path.read_bytes()

    def getvalue(self) -> bytes:
        return self._bytes


def _init_state() -> None:
    defaults = {
        "run_dir": None,
        "case_id": None,
        "result": None,
        "report_md": None,
        "path_active": None,
        "path_done": set(),
        "path_failed": None,
        "error": None,
        "analyst": "arun",
        "sample_key": None,
        "threat_intel": True,
        "investigator_only": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _load_result(run_dir: Path) -> dict:
    path = run_dir / "result.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _load_report(run_dir: Path) -> str | None:
    path = run_dir / "report.md"
    if path.exists():
        return path.read_text()
    return None


def _mark_complete() -> None:
    st.session_state.path_active = None
    st.session_state.path_done = set(STEPS_ORDER)
    st.session_state.path_failed = None


def _resolve_upload(upload):
    if upload is not None:
        return upload
    key = st.session_state.get("sample_key")
    if not key:
        return None
    for sample in SAMPLE_CASES:
        if sample["key"] == key and sample["path"].exists():
            return _UploadProxy(sample["path"])
    return None


def _run_investigation(
    upload,
    case_id: str,
    *,
    investigator_only: bool,
    threat_intel: bool,
) -> None:
    st.session_state.error = None
    st.session_state.path_failed = None
    st.session_state.path_done = set()
    st.session_state.path_active = "parse"
    st.session_state.result = None
    st.session_state.report_md = None
    st.session_state.run_dir = None

    suffix = Path(upload.name).suffix or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(upload.getvalue())
        tmp_path = tmp.name

    progress = st.empty()
    status = st.empty()

    def tick(step: str, label: str, *, pause: float = 0.35) -> None:
        idx = STEPS_ORDER.index(step)
        st.session_state.path_done = set(STEPS_ORDER[:idx])
        st.session_state.path_active = step
        progress.markdown(
            path_html(
                active=st.session_state.path_active,
                done=st.session_state.path_done,
                failed=st.session_state.path_failed,
            ),
            unsafe_allow_html=True,
        )
        status.markdown(
            f'<p class="sf-loading">{html.escape(label)}</p>',
            unsafe_allow_html=True,
        )
        if pause:
            time.sleep(pause)

    try:
        tick("parse", "Reading the manuscript of evidence…")
        if threat_intel:
            tick("enrich", "Consulting the omens of threat intel…")
        else:
            st.session_state.path_done = {"parse"}
            st.session_state.path_active = "investigate"

        tick("investigate", "The Investigator weighs the field…", pause=0.25)
        if not investigator_only:
            tick("critic", "The Critic prepares the challenge…", pause=0.25)
        tick("report", "The court deliberates — invoking the agents…", pause=0.2)

        mode = "investigator_only" if investigator_only else "full"
        run_dir = run_case(
            tmp_path,
            case_id,
            mode=mode,
            write_report=True,
            enrich_threat_intel=threat_intel,
        )
        st.session_state.run_dir = str(run_dir)
        st.session_state.case_id = case_id
        st.session_state.result = _load_result(run_dir)
        st.session_state.report_md = _load_report(run_dir)

        # Light remaining steps after the run completes.
        if not investigator_only:
            tick("critic", "Critic has spoken…", pause=0.2)
        tick("report", "Chronicle sealed…", pause=0.2)
        tick("approve", "Awaiting your royal decree…", pause=0.25)
        _mark_complete()
        progress.markdown(
            path_html(done=st.session_state.path_done),
            unsafe_allow_html=True,
        )
        status.markdown(
            '<p class="sf-loading" style="animation:none;color:#d4af37;">'
            "The chronicle is complete.</p>",
            unsafe_allow_html=True,
        )
    except Exception as exc:  # noqa: BLE001 — surface to UI
        st.session_state.path_failed = st.session_state.path_active or "parse"
        st.session_state.error = str(exc)
        progress.markdown(
            path_html(
                active=None,
                done=st.session_state.path_done,
                failed=st.session_state.path_failed,
            ),
            unsafe_allow_html=True,
        )
        status.empty()
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except OSError:
            pass


def _render_outcome(result: dict) -> None:
    status = html.escape(str(result.get("status", "unknown")))
    hyp = result.get("hypothesis") or {}
    classification = html.escape(str(hyp.get("classification", "—")).replace("_", " "))
    confidence = html.escape(str(hyp.get("confidence", "—")))
    summary = html.escape(str(hyp.get("summary") or ""))

    seal_cls = "sf-seal"
    if "unresolved" in status:
        seal_cls += " vermillion"
    elif "awaiting" in status or "approval" in status:
        seal_cls += ""
    else:
        seal_cls += " sage"

    st.markdown(
        f"""
<div class="sf-verdict">
  <p class="sf-v-label">Sealed outcome</p>
  <span class="{seal_cls}">{status.replace("_", " ")}</span>
  <p class="sf-v-class">{classification}</p>
  <p class="sf-v-meta">Confidence · {confidence}</p>
  <p class="sf-v-summary">{summary}</p>
</div>
""",
        unsafe_allow_html=True,
    )

    claims = hyp.get("claims") or []
    if claims:
        st.markdown(
            section_html("Claims of the Field", "Each assertion bound to evidence IDs"),
            unsafe_allow_html=True,
        )
        blocks = ['<div class="sf-panel">']
        for c in claims:
            statement = html.escape(str(c.get("statement", "")))
            ids = html.escape(", ".join(c.get("evidence_ids") or []))
            blocks.append(
                f'<div class="sf-claim">{statement}'
                f'<div class="sf-cite">{ids}</div></div>'
            )
        blocks.append("</div>")
        st.markdown("".join(blocks), unsafe_allow_html=True)

    techniques = hyp.get("attack_techniques") or []
    if techniques:
        with st.expander("MITRE ATT&CK techniques", expanded=False):
            for t in techniques:
                tid = t.get("technique_id", "")
                name = t.get("name", "")
                ids = ", ".join(t.get("evidence_ids") or [])
                st.markdown(f"**{tid}** — {name}  \n`{ids}`")


def _render_actions(case_id: str, analyst: str) -> None:
    store = EvidenceStore()
    actions = list_actions(store, case_id=case_id)
    if not actions:
        st.markdown(
            '<div class="sf-panel"><p style="margin:0;color:#cbb991;">'
            "No recommended actions were proposed for this case.</p></div>",
            unsafe_allow_html=True,
        )
        return

    pending = [a for a in actions if a.status.value == "pending"]
    decided = [a for a in actions if a.status.value != "pending"]

    if pending:
        st.caption("Simulated only — approve/reject is recorded; nothing is executed.")
        for a in pending:
            st.markdown(
                f"""
<div class="sf-panel">
  <span class="sf-seal">Pending decree · {html.escape(a.action_id)}</span>
  <p style="margin:0.8rem 0 0;line-height:1.5;">{html.escape(a.description)}</p>
</div>
""",
                unsafe_allow_html=True,
            )
            c1, c2, _ = st.columns([1, 1, 2])
            with c1:
                if st.button(
                    "Approve",
                    key=f"approve_{a.action_id}",
                    type="primary",
                    use_container_width=True,
                    help="Seal this action as approved (simulated)",
                ):
                    decide_action(
                        store, a.action_id, approve=True, decided_by=analyst
                    )
                    st.toast(f"Approved {a.action_id} — decree recorded", icon="✅")
                    st.rerun()
            with c2:
                if st.button(
                    "Reject",
                    key=f"reject_{a.action_id}",
                    use_container_width=True,
                    help="Reject this action (simulated)",
                ):
                    decide_action(
                        store, a.action_id, approve=False, decided_by=analyst
                    )
                    st.toast(f"Rejected {a.action_id} — decree recorded", icon="⛔")
                    st.rerun()

    if decided:
        with st.expander("Prior decrees", expanded=not pending):
            for a in decided:
                note = f" — {a.note}" if a.note else ""
                st.markdown(
                    f"**{a.action_id}** · `{a.status.value}` by "
                    f"{a.decided_by or '—'}{note}  \n{a.description}"
                )


def _render_sample_chips() -> None:
    st.markdown(
        '<p class="sf-chip-hint">Or try a sample scroll</p>',
        unsafe_allow_html=True,
    )
    cols = st.columns(len(SAMPLE_CASES))
    for col, sample in zip(cols, SAMPLE_CASES, strict=True):
        with col:
            selected = st.session_state.sample_key == sample["key"]
            label = f"✓ {sample['label']}" if selected else sample["label"]
            if st.button(
                label,
                key=f"sample_{sample['key']}",
                use_container_width=True,
                help=sample["hint"],
                disabled=not sample["path"].exists(),
            ):
                st.session_state.sample_key = sample["key"]
                st.toast(f"Sample loaded: {sample['label']}", icon="📜")
                st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="SentinelFlow · The Field of Evidence",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    inject()
    _init_state()

    st.markdown(hero_html(), unsafe_allow_html=True)

    st.markdown(
        section_html(
            "Offer the Evidence",
            "Upload a scroll, or choose a sample case below",
        ),
        unsafe_allow_html=True,
    )

    upload = st.file_uploader(
        "Case file",
        type=["eml", "pcap", "pcapng", "json"],
        label_visibility="collapsed",
        help="Upload .eml, .pcap/.pcapng, or Suricata eve.json",
    )
    if upload is not None:
        st.session_state.sample_key = None

    _render_sample_chips()

    active = _resolve_upload(upload)
    if active is not None and upload is None:
        st.caption(f"Using sample: `{active.name}`")

    c1, c2 = st.columns(2)
    with c1:
        default_case = Path(active.name).stem if active else "case"
        case_id = st.text_input("Case name", value=default_case)
    with c2:
        st.session_state.analyst = st.text_input(
            "Analyst seal (name)",
            value=st.session_state.analyst,
        )

    with st.expander("Advanced omens (optional)", expanded=False):
        st.session_state.threat_intel = st.checkbox(
            "Consult threat-intel omens",
            value=st.session_state.threat_intel,
            help="Stage 7 enrichment — IP/domain/hash lookups (cached)",
        )
        st.session_state.investigator_only = st.checkbox(
            "Investigator alone (no Critic)",
            value=st.session_state.investigator_only,
            help="Baseline mode — skip Critic revision loop",
        )

    st.markdown(
        path_html(
            active=st.session_state.path_active,
            done=st.session_state.path_done,
            failed=st.session_state.path_failed,
        ),
        unsafe_allow_html=True,
    )

    run = st.button(
        "Begin the Inquiry",
        type="primary",
        use_container_width=True,
        disabled=active is None,
        help="Run parse → enrich → investigate → critic → report",
    )
    if run and active:
        _run_investigation(
            active,
            case_id.strip() or Path(active.name).stem,
            investigator_only=st.session_state.investigator_only,
            threat_intel=st.session_state.threat_intel,
        )

    if st.session_state.error:
        st.error(st.session_state.error)

    result = st.session_state.result
    if result:
        st.markdown(
            section_html("Chronicle of the Case", "Outcome sealed by evidence"),
            unsafe_allow_html=True,
        )
        _render_outcome(result)

        report = st.session_state.report_md
        if report:
            st.markdown(
                section_html("Incident Report", "Defanged IOCs · human-readable"),
                unsafe_allow_html=True,
            )
            st.markdown('<div class="sf-panel">', unsafe_allow_html=True)
            st.markdown(report)
            st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.run_dir:
            st.caption(f"Artifacts: `{st.session_state.run_dir}`")

        st.markdown(
            section_html(
                "Royal Decrees",
                "Approve or reject recommended actions — simulated only",
            ),
            unsafe_allow_html=True,
        )
        _render_actions(st.session_state.case_id, st.session_state.analyst)

    # Browse pending actions across cases (Stage 6 gate, always available)
    st.markdown(
        section_html("Open Decrees", "Pending actions awaiting your seal"),
        unsafe_allow_html=True,
    )
    store = EvidenceStore()
    open_actions = list_actions(store, pending_only=True)
    # Prefer showing case-specific decrees above; here show others + leftovers
    others = [
        a
        for a in open_actions
        if not (st.session_state.case_id and a.case_id == st.session_state.case_id)
    ]
    if not open_actions:
        st.markdown(
            '<div class="sf-panel"><p style="margin:0;color:#cbb991;">'
            "The docket is clear. No pending actions.</p></div>",
            unsafe_allow_html=True,
        )
    elif not others and st.session_state.result:
        st.markdown(
            '<div class="sf-panel"><p style="margin:0;color:#cbb991;">'
            "Pending decrees for this case are listed under Royal Decrees above."
            "</p></div>",
            unsafe_allow_html=True,
        )
    else:
        for a in others:
            st.markdown(
                f"""
<div class="sf-panel">
  <span class="sf-seal">Case {html.escape(a.case_id)} · {html.escape(a.action_id)}</span>
  <p style="margin:0.8rem 0 0;">{html.escape(a.description)}</p>
</div>
""",
                unsafe_allow_html=True,
            )
            b1, b2 = st.columns(2)
            with b1:
                if st.button(
                    f"Approve {a.action_id}",
                    key=f"open_approve_{a.action_id}",
                    type="primary",
                    use_container_width=True,
                    help="Seal approved (simulated)",
                ):
                    decide_action(
                        store,
                        a.action_id,
                        approve=True,
                        decided_by=st.session_state.analyst,
                    )
                    st.toast(f"Approved {a.action_id}", icon="✅")
                    st.rerun()
            with b2:
                if st.button(
                    f"Reject {a.action_id}",
                    key=f"open_reject_{a.action_id}",
                    use_container_width=True,
                    help="Seal rejected (simulated)",
                ):
                    decide_action(
                        store,
                        a.action_id,
                        approve=False,
                        decided_by=st.session_state.analyst,
                    )
                    st.toast(f"Rejected {a.action_id}", icon="⛔")
                    st.rerun()

    st.markdown(
        '<div class="sf-footer">SentinelFlow · Evidence before action · '
        "Simulated decrees only</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
