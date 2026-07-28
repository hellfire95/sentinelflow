"""Report agent: turns APPROVED findings into a readable incident report.
Introduces no new facts; the structured JSON report is assembled in code, the
LLM only writes the narrative. All IOCs are defanged at output time."""

from ..defang import defang
from ..models import Evidence, Hypothesis
from ..trace import Tracer
from .llm import LLMClient

SYSTEM = """You are the Report writer in a security incident analysis system.
You receive an APPROVED hypothesis and the evidence it cites. Write a clear,
professional incident report in Markdown.

Hard rules:
- Introduce NO new facts, indicators, or conclusions. Everything in the
  report must come from the hypothesis or the cited evidence provided.
- Reference evidence IDs inline (e.g. "[Q2_1-EV003]") so every statement is
  traceable.
- Structure: Executive Summary, Findings (one per claim), Contradictory
  Evidence, MITRE ATT&CK Mapping, Recommended Actions (mark clearly as
  PENDING HUMAN APPROVAL), Confidence & Limitations.
- Keep it factual and free of speculation."""


def write_report(
    client: LLMClient,
    hypothesis: Hypothesis,
    cited_evidence: dict[str, Evidence],
    tracer: Tracer,
) -> str:
    evidence_lines = "\n".join(
        f"[{e.id}] ({e.category.value}) {e.label}: {e.value}"
        for e in cited_evidence.values()
    )
    user = (
        f"APPROVED HYPOTHESIS:\n{hypothesis.model_dump_json(indent=2)}\n\n"
        f"CITED EVIDENCE:\n{evidence_lines}\n\n"
        "Write the incident report."
    )
    tracer.event("llm_call", step="report", **client.settings())
    narrative = client.complete(SYSTEM, user)
    tracer.event("llm_output", step="report", chars=len(narrative))
    return defang(narrative)
