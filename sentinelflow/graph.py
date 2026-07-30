"""LangGraph orchestration (Stage 3).

Thin wrappers around the existing parsers/agents/precheck. Same control flow
as pipeline.run_case, expressed as a state machine so the revision loop and
transitions are explicit and logged.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from . import config
from .agents import critic as critic_agent
from .agents import investigator as investigator_agent
from .agents import report as report_agent
from .agents.llm import LLMClient
from .models import (
    CaseStatus,
    Critique,
    CritiqueVerdict,
    Evidence,
    Hypothesis,
    PrecheckResult,
)
from .pipeline import _collect_cited_ids, ingest
from .precheck import precheck_citations
from .store import EvidenceStore
from .trace import Tracer


class GraphState(TypedDict, total=False):
    """Shared bag that flows between nodes. Only case data — no LLM client."""

    case_id: str
    source_path: str
    evidence: list[Evidence]
    hypothesis: Hypothesis | None
    critique: Critique | None
    critiques: list[Critique]
    precheck: PrecheckResult | None
    revision_count: int
    approved: bool
    status: str
    report: str | None


class _Runtime:
    """Holds objects that are not part of graph state (client, tracer, store)."""

    def __init__(
        self,
        case_id: str,
        source_path: str,
        *,
        write_report: bool = True,
        mode: str = "full",
        trace_id: str | None = None,
    ):
        self.case_id = case_id  # logical id used in Evidence IDs
        self.source_path = source_path
        self.write_report = write_report
        self.mode = mode
        self.store = EvidenceStore()
        self.tracer = Tracer(config.RUNS_DIR, trace_id or case_id)
        self.client = LLMClient()


def _transition(rt: _Runtime, node: str, **extra) -> None:
    rt.tracer.event("graph_transition", node=node, **extra)


def _parse_case(state: GraphState, rt: _Runtime) -> dict:
    _transition(rt, "parse_case")
    case = ingest(rt.source_path, rt.case_id, rt.store)
    evidence = rt.store.get_evidence(rt.case_id)
    rt.tracer.event("parsed", evidence_count=len(evidence))
    rt.store.update_status(rt.case_id, CaseStatus.INVESTIGATING)
    return {
        "case_id": case.case_id,
        "source_path": rt.source_path,
        "evidence": evidence,
        "critiques": [],
        "revision_count": 0,
        "approved": False,
        "status": CaseStatus.INVESTIGATING.value,
        "hypothesis": None,
        "critique": None,
        "precheck": None,
        "report": None,
    }


def _investigate(state: GraphState, rt: _Runtime) -> dict:
    _transition(rt, "investigate")
    hypothesis = investigator_agent.investigate(rt.client, state["evidence"], rt.tracer)
    return {"hypothesis": hypothesis}


def _critic_review(state: GraphState, rt: _Runtime) -> dict:
    """Mechanical precheck + Critic in one node (same pairing as the old loop)."""
    _transition(rt, "critic_review", revision=state.get("revision_count", 0))
    hypothesis = state["hypothesis"]
    assert hypothesis is not None
    valid_ids = rt.store.evidence_ids(rt.case_id)
    precheck = precheck_citations(hypothesis, valid_ids)
    rt.tracer.event(
        "precheck",
        revision=state.get("revision_count", 0),
        passed=precheck.passed,
        fabricated=precheck.fabricated_evidence_ids,
    )
    cited = rt.store.get_evidence_by_ids(rt.case_id, _collect_cited_ids(hypothesis))
    critique = critic_agent.critique(rt.client, hypothesis, cited, precheck, rt.tracer)
    critiques = list(state.get("critiques") or [])
    critiques.append(critique)
    approved = critique.verdict == CritiqueVerdict.APPROVE and precheck.passed
    rt.tracer.event(
        "critic_verdict",
        revision=state.get("revision_count", 0),
        verdict=critique.verdict.value,
        approved=approved,
    )
    return {
        "precheck": precheck,
        "critique": critique,
        "critiques": critiques,
        "approved": approved,
    }


def _revise(state: GraphState, rt: _Runtime) -> dict:
    _transition(rt, "revise", revision=state.get("revision_count", 0) + 1)
    hypothesis = state["hypothesis"]
    critique = state["critique"]
    assert hypothesis is not None and critique is not None
    revised = investigator_agent.revise(
        rt.client, state["evidence"], hypothesis, critique, rt.tracer
    )
    return {
        "hypothesis": revised,
        "revision_count": state.get("revision_count", 0) + 1,
    }


def _generate_report(state: GraphState, rt: _Runtime) -> dict:
    _transition(rt, "generate_report", write_report=rt.write_report)
    hypothesis = state["hypothesis"]
    assert hypothesis is not None
    if rt.write_report:
        cited = rt.store.get_evidence_by_ids(rt.case_id, _collect_cited_ids(hypothesis))
        narrative = report_agent.write_report(rt.client, hypothesis, cited, rt.tracer)
    else:
        narrative = (
            "# Report skipped (eval mode)\n\n"
            f"Classification: {hypothesis.classification.value} "
            f"({hypothesis.confidence.value})\n\n{hypothesis.summary}\n"
        )
        rt.tracer.event("report_skipped", reason="write_report=False")
    rt.store.update_status(rt.case_id, CaseStatus.REPORTED)
    rt.tracer.event("report_written", skipped=not rt.write_report)
    return {
        "report": narrative,
        "status": CaseStatus.REPORTED.value,
        "approved": True,
    }


def _mark_unresolved(state: GraphState, rt: _Runtime) -> dict:
    _transition(rt, "mark_unresolved")
    note = (
        "# UNRESOLVED — HUMAN REVIEW REQUIRED\n\n"
        f"The Critic did not approve the hypothesis after "
        f"{config.MAX_REVISIONS} revisions. See result.json for the final "
        "hypothesis and all critiques.\n"
    )
    rt.store.update_status(rt.case_id, CaseStatus.UNRESOLVED)
    return {
        "report": note,
        "status": CaseStatus.UNRESOLVED.value,
        "approved": False,
    }


def _after_critic(state: GraphState) -> Literal["generate_report", "revise", "mark_unresolved"]:
    if state.get("approved"):
        return "generate_report"
    if state.get("revision_count", 0) < config.MAX_REVISIONS:
        return "revise"
    return "mark_unresolved"


def _finalize_baseline(state: GraphState, rt: _Runtime) -> dict:
    """Investigator-only exit: mechanical precheck only, no Critic LLM."""
    _transition(rt, "finalize_baseline")
    hypothesis = state["hypothesis"]
    assert hypothesis is not None
    valid_ids = rt.store.evidence_ids(rt.case_id)
    precheck = precheck_citations(hypothesis, valid_ids)
    rt.tracer.event(
        "precheck",
        revision=0,
        passed=precheck.passed,
        fabricated=precheck.fabricated_evidence_ids,
        mode="investigator_only",
    )
    note = (
        "# Investigator-only baseline\n\n"
        "Critic skipped. Hypothesis below is the first Investigator output.\n"
    )
    rt.store.update_status(rt.case_id, CaseStatus.APPROVED)
    return {
        "precheck": precheck,
        "approved": precheck.passed,
        "report": note,
        "status": CaseStatus.APPROVED.value,
    }


def build_graph(rt: _Runtime, mode: str = "full"):
    g = StateGraph(GraphState)
    g.add_node("parse_case", lambda s: _parse_case(s, rt))
    g.add_node("investigate", lambda s: _investigate(s, rt))
    g.add_edge(START, "parse_case")
    g.add_edge("parse_case", "investigate")

    if mode == "investigator_only":
        g.add_node("finalize_baseline", lambda s: _finalize_baseline(s, rt))
        g.add_edge("investigate", "finalize_baseline")
        g.add_edge("finalize_baseline", END)
        return g.compile()

    g.add_node("critic_review", lambda s: _critic_review(s, rt))
    g.add_node("revise", lambda s: _revise(s, rt))
    g.add_node("generate_report", lambda s: _generate_report(s, rt))
    g.add_node("mark_unresolved", lambda s: _mark_unresolved(s, rt))
    g.add_edge("investigate", "critic_review")
    g.add_conditional_edges(
        "critic_review",
        _after_critic,
        {
            "generate_report": "generate_report",
            "revise": "revise",
            "mark_unresolved": "mark_unresolved",
        },
    )
    g.add_edge("revise", "critic_review")
    g.add_edge("generate_report", END)
    g.add_edge("mark_unresolved", END)
    return g.compile()


def run_case(
    path: str,
    case_id: str,
    *,
    mode: str = "full",
    write_report: bool = True,
    run_label: str | None = None,
) -> Path:
    """Run a case through LangGraph.

    mode: "full" (Investigator+Critic) or "investigator_only" (baseline).
    write_report: if False, skip the Report LLM (eval scoring only needs hypothesis).
    run_label: optional tracer folder suffix, e.g. eval/full/Q2_1/r1
    """
    if mode not in ("full", "investigator_only"):
        raise RuntimeError(f"Unknown mode '{mode}'")

    trace_id = run_label or case_id
    rt = _Runtime(
        case_id,
        path,
        write_report=write_report,
        mode=mode,
        trace_id=trace_id,
    )
    rt.tracer.event(
        "run_start",
        case_id=case_id,
        source=path,
        mode=mode,
        write_report=write_report,
        orchestrator="langgraph",
        **rt.client.settings(),
    )

    app = build_graph(rt, mode=mode)
    final: GraphState = app.invoke(
        {
            "case_id": case_id,
            "source_path": path,
            "revision_count": 0,
            "approved": False,
            "critiques": [],
        }
    )

    hypothesis = final.get("hypothesis")
    critiques = final.get("critiques") or []
    status = final.get("status", CaseStatus.UNRESOLVED.value)
    precheck = final.get("precheck")
    rt.tracer.event(
        "resolution",
        status=status,
        revisions=final.get("revision_count", 0),
        mode=mode,
        orchestrator="langgraph",
    )

    result = {
        "case_id": case_id,
        "source_files": [path],
        "status": status,
        "mode": mode,
        "model_settings": rt.client.settings(),
        "orchestrator": "langgraph",
        "revisions": final.get("revision_count", 0),
        "precheck": precheck.model_dump() if precheck else None,
        "hypothesis": hypothesis.model_dump() if hypothesis else None,
        "critiques": [c.model_dump() for c in critiques],
    }
    rt.tracer.write_artifact("result.json", json.dumps(result, indent=2, default=str))
    rt.tracer.write_artifact("report.md", final.get("report") or "")
    rt.tracer.event("run_end")
    run_dir = rt.tracer.run_dir
    rt.tracer.close()
    return run_dir
