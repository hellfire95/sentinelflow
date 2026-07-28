"""Investigator agent: forms an evidence-cited hypothesis from structured
evidence. Never sees the raw source file."""

from ..models import Critique, Evidence, Hypothesis
from ..trace import Tracer
from .llm import LLMClient

SYSTEM = """You are the Investigator in a security incident analysis system.
You receive structured evidence extracted deterministically from a source file
(e.g. an email). You never see the raw file.

Rules:
- Every claim you make MUST cite one or more evidence IDs from the list you
  are given. Never invent evidence IDs. Never assert facts that are not in
  the evidence.
- Break your reasoning into small, individually checkable claims.
- List evidence that CONTRADICTS your classification under
  contradictory_evidence_ids. An honest analyst reports both sides.
- Confidence is a routing signal: use "low" if a human should review before
  trusting the classification.
- Map to MITRE ATT&CK techniques only where evidence supports them, citing
  the supporting evidence IDs.
- "benign" is a valid answer. Do not manufacture suspicion where the evidence
  does not support it.
- recommended_actions are suggestions only; they will require human approval
  and are never executed automatically."""


def _format_evidence(evidence: list[Evidence]) -> str:
    lines = []
    for e in evidence:
        lines.append(f"[{e.id}] ({e.category.value}) {e.label}: {e.value}")
    return "\n".join(lines)


def investigate(client: LLMClient, evidence: list[Evidence], tracer: Tracer) -> Hypothesis:
    user = (
        "Analyse the following evidence and produce your hypothesis.\n\n"
        f"EVIDENCE:\n{_format_evidence(evidence)}"
    )
    return client.structured(SYSTEM, user, Hypothesis, tracer, step="investigate")


def revise(
    client: LLMClient,
    evidence: list[Evidence],
    previous: Hypothesis,
    critique: Critique,
    tracer: Tracer,
) -> Hypothesis:
    user = (
        "Your previous hypothesis was reviewed by a critic and requires revision.\n\n"
        f"EVIDENCE:\n{_format_evidence(evidence)}\n\n"
        f"YOUR PREVIOUS HYPOTHESIS:\n{previous.model_dump_json(indent=2)}\n\n"
        f"CRITIQUE:\n{critique.model_dump_json(indent=2)}\n\n"
        "Address every point in the critique. Remove or re-ground unsupported "
        "claims. Do not simply restate the previous hypothesis."
    )
    return client.structured(SYSTEM, user, Hypothesis, tracer, step="revise")
