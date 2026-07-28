"""Critic agent: challenges the Investigator's claims.

The mechanical ID-existence check has already run in code (precheck.py); the
raw values of all cited evidence are injected here, so the Critic's job
narrows to the semantic question: does this evidence actually support this
claim?"""

from ..models import Critique, Evidence, Hypothesis, PrecheckResult
from ..trace import Tracer
from .llm import LLMClient

SYSTEM = """You are the Critic in a security incident analysis system. Your
whole job is to challenge the Investigator's hypothesis against the actual
evidence. You are shown each claim alongside the verbatim values of the
evidence it cites.

For each claim, ask: does the cited evidence actually support this statement,
or does the claim overreach, misread the evidence, or assert something the
evidence does not say?

Also consider:
- Are there missing considerations (evidence pointing the other way that the
  Investigator ignored, alternative benign explanations)?
- Is the classification justified by the supported claims taken together?
- Is the confidence level appropriate given the strength of the evidence?

Verdicts:
- "approve" if all claims are supported and the classification follows.
- "revise" if any claim is unsupported or the classification/confidence does
  not follow from the evidence.

Be rigorous but fair: do not invent objections. If the hypothesis is sound,
approve it."""


def _format_claims_with_evidence(
    hypothesis: Hypothesis, cited: dict[str, Evidence]
) -> str:
    blocks = []
    for idx, claim in enumerate(hypothesis.claims):
        lines = [f"CLAIM {idx}: {claim.statement}"]
        for eid in claim.evidence_ids:
            if eid in cited:
                e = cited[eid]
                lines.append(f"  cites [{eid}] {e.label}: {e.value}")
            else:
                lines.append(f"  cites [{eid}] *** FABRICATED — no such evidence ***")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def critique(
    client: LLMClient,
    hypothesis: Hypothesis,
    cited_evidence: dict[str, Evidence],
    precheck: PrecheckResult,
    tracer: Tracer,
) -> Critique:
    precheck_note = (
        "A mechanical pre-check found these cited evidence IDs DO NOT EXIST: "
        f"{', '.join(precheck.fabricated_evidence_ids)}. Claims citing them "
        "cannot be considered supported.\n\n"
        if not precheck.passed
        else ""
    )
    user = (
        f"{precheck_note}"
        f"HYPOTHESIS SUMMARY: {hypothesis.summary}\n"
        f"CLASSIFICATION: {hypothesis.classification.value} "
        f"(confidence: {hypothesis.confidence.value})\n\n"
        f"CLAIMS WITH THEIR CITED EVIDENCE:\n"
        f"{_format_claims_with_evidence(hypothesis, cited_evidence)}\n\n"
        f"CONTRADICTORY EVIDENCE ACKNOWLEDGED BY INVESTIGATOR: "
        f"{hypothesis.contradictory_evidence_ids or 'none'}\n\n"
        f"ATT&CK TECHNIQUES CLAIMED: "
        f"{[t.technique_id for t in hypothesis.attack_techniques] or 'none'}\n\n"
        "Review and return your critique."
    )
    return client.structured(SYSTEM, user, Critique, tracer, step="critic_review")
