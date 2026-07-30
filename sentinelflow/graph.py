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

    def __init__(self, case_id: str, source_path: str):
        self.case_id = case_id
        self.source_path = source_path
        self.store = EvidenceStore()
        self.tracer = Tracer(config.RUNS_DIR, case_id)
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
    _transition(rt, "generate_report")
    hypothesis = state["hypothesis"]
    assert hypothesis is not None
    cited = rt.store.get_evidence_by_ids(rt.case_id, _collect_cited_ids(hypothesis))
    narrative = report_agent.write_report(rt.client, hypothesis, cited, rt.tracer)
    rt.store.update_status(rt.case_id, CaseStatus.REPORTED)
    rt.tracer.event("report_written")
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


def build_graph(rt: _Runtime):
    g = StateGraph(GraphState)
    g.add_node("parse_case", lambda s: _parse_case(s, rt))
    g.add_node("investigate", lambda s: _investigate(s, rt))
    g.add_node("critic_review", lambda s: _critic_review(s, rt))
    g.add_node("revise", lambda s: _revise(s, rt))
    g.add_node("generate_report", lambda s: _generate_report(s, rt))
    g.add_node("mark_unresolved", lambda s: _mark_unresolved(s, rt))

    g.add_edge(START, "parse_case")
    g.add_edge("parse_case", "investigate")
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


def run_case(path: str, case_id: str) -> Path:
    """Entry point used by the CLI — same signature as the old pipeline loop."""
    rt = _Runtime(case_id, path)
    rt.tracer.event("run_start", case_id=case_id, source=path, orchestrator="langgraph", **rt.client.settings())

    app = build_graph(rt)
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
    rt.tracer.event(
        "resolution",
        status=status,
        revisions=final.get("revision_count", 0),
        orchestrator="langgraph",
    )

    result = {
        "case_id": case_id,
        "source_files": [path],
        "status": status,
        "model_settings": rt.client.settings(),
        "orchestrator": "langgraph",
        "revisions": final.get("revision_count", 0),
        "hypothesis": hypothesis.model_dump() if hypothesis else None,
        "critiques": [c.model_dump() for c in critiques],
    }
    rt.tracer.write_artifact("result.json", json.dumps(result, indent=2, default=str))
    rt.tracer.write_artifact("report.md", final.get("report") or "")
    rt.tracer.event("run_end")
    run_dir = rt.tracer.run_dir
    rt.tracer.close()
    return run_dir
