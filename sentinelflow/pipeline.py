"""Shared parse/ingest helpers + run entry point.

Stage 3: run_case delegates to the LangGraph state machine in graph.py.
Parsers and agents are unchanged; only the conductor moved.
"""

from pathlib import Path

from .models import Case, Hypothesis
from .parsers.eml import parse_eml
from .parsers.eve import parse_eve
from .parsers.pcap import parse_pcap
from .store import EvidenceStore

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


def run_case(path: str, case_id: str, **kwargs) -> Path:
    """Run a case through the LangGraph orchestrator."""
    from .graph import run_case as run_via_graph

    return run_via_graph(path, case_id, **kwargs)
