"""Orchestration for the Stage 1 vertical slice, in plain Python.

Flow: parse -> investigate -> [precheck -> critic -> (approve | revise)] -> report
The loop is capped; if the Critic still rejects after MAX_REVISIONS revisions
the case exits as UNRESOLVED and requires human review — it never silently
falls through to a report. (LangGraph port happens in Stage 3.)
"""

import json
from pathlib import Path

from . import config
from .agents import critic as critic_agent
from .agents import investigator as investigator_agent
from .agents import report as report_agent
from .agents.llm import LLMClient
from .models import Case, CaseStatus, Critique, CritiqueVerdict, Hypothesis
from .parsers.eml import parse_eml
from .parsers.eve import parse_eve
from .parsers.pcap import parse_pcap
from .precheck import precheck_citations
from .store import EvidenceStore
from .trace import Tracer

# The agents are evidence-type-agnostic; adding an input type only means
# registering a new deterministic parser here.
PARSERS = {
    ".eml": parse_eml,
    ".pcap": parse_pcap,
    ".pcapng": parse_pcap,
    ".json": parse_eve,
}


def parse_file(path: str, case_id: str):
    suffix = Path(path).suffix.lower()
    if suffix not in PARSERS:
        raise RuntimeError(
            f"Unsupported file type '{suffix}'. Supported: {', '.join(PARSERS)}"
        )
    return PARSERS[suffix](path, case_id)


def ingest(path: str, case_id: str, store: EvidenceStore) -> Case:
    case = Case(case_id=case_id, source_files=[path])
    evidence = parse_file(path, case_id)
    store.save_case(case)
    store.save_evidence(evidence)
    return case


def _collect_cited_ids(hypothesis: Hypothesis) -> list[str]:
    ids: list[str] = []
    for claim in hypothesis.claims:
        ids.extend(claim.evidence_ids)
    for technique in hypothesis.attack_techniques:
        ids.extend(technique.evidence_ids)
    ids.extend(hypothesis.contradictory_evidence_ids)
    return sorted(set(ids))


def run_case(path: str, case_id: str) -> Path:
    store = EvidenceStore()
    tracer = Tracer(config.RUNS_DIR, case_id)
    client = LLMClient()
    tracer.event("run_start", case_id=case_id, source=path, **client.settings())

    case = ingest(path, case_id, store)
    evidence = store.get_evidence(case_id)
    valid_ids = store.evidence_ids(case_id)
    tracer.event("parsed", evidence_count=len(evidence))
    store.update_status(case_id, CaseStatus.INVESTIGATING)

    hypothesis = investigator_agent.investigate(client, evidence, tracer)

    critiques: list[Critique] = []
    approved = False
    for revision in range(config.MAX_REVISIONS + 1):
        precheck = precheck_citations(hypothesis, valid_ids)
        tracer.event(
            "precheck",
            revision=revision,
            passed=precheck.passed,
            fabricated=precheck.fabricated_evidence_ids,
        )
        cited = store.get_evidence_by_ids(case_id, _collect_cited_ids(hypothesis))
        critique = critic_agent.critique(client, hypothesis, cited, precheck, tracer)
        critiques.append(critique)
        tracer.event("critic_verdict", revision=revision, verdict=critique.verdict.value)

        # A verdict of approve with fabricated IDs still fails: precheck is law.
        if critique.verdict == CritiqueVerdict.APPROVE and precheck.passed:
            approved = True
            break
        if revision == config.MAX_REVISIONS:
            break
        hypothesis = investigator_agent.revise(client, evidence, hypothesis, critique, tracer)

    final_status = CaseStatus.APPROVED if approved else CaseStatus.UNRESOLVED
    store.update_status(case_id, final_status)
    tracer.event("resolution", status=final_status.value, revisions=len(critiques) - 1)

    result = {
        "case_id": case_id,
        "source_files": case.source_files,
        "status": final_status.value,
        "model_settings": client.settings(),
        "revisions": len(critiques) - 1,
        "hypothesis": hypothesis.model_dump(),
        "critiques": [c.model_dump() for c in critiques],
    }
    tracer.write_artifact("result.json", json.dumps(result, indent=2, default=str))

    if approved:
        cited = store.get_evidence_by_ids(case_id, _collect_cited_ids(hypothesis))
        narrative = report_agent.write_report(client, hypothesis, cited, tracer)
        tracer.write_artifact("report.md", narrative)
        store.update_status(case_id, CaseStatus.REPORTED)
        tracer.event("report_written")
    else:
        tracer.write_artifact(
            "report.md",
            "# UNRESOLVED — HUMAN REVIEW REQUIRED\n\n"
            f"The Critic did not approve the hypothesis after "
            f"{config.MAX_REVISIONS} revisions. See result.json for the final "
            "hypothesis and all critiques.\n",
        )

    tracer.event("run_end")
    run_dir = tracer.run_dir
    tracer.close()
    return run_dir
