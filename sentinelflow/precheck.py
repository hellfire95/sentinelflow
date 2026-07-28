"""Mechanical citation validation. Pure code, no LLM: does every evidence ID
the Investigator cited actually exist in the store?"""

from .models import Hypothesis, PrecheckResult


def precheck_citations(hypothesis: Hypothesis, valid_ids: set[str]) -> PrecheckResult:
    fabricated: list[str] = []
    bad_claims: list[int] = []

    for idx, claim in enumerate(hypothesis.claims):
        missing = [i for i in claim.evidence_ids if i not in valid_ids]
        if missing:
            fabricated.extend(missing)
            bad_claims.append(idx)

    for technique in hypothesis.attack_techniques:
        fabricated.extend(i for i in technique.evidence_ids if i not in valid_ids)
    fabricated.extend(i for i in hypothesis.contradictory_evidence_ids if i not in valid_ids)

    return PrecheckResult(
        fabricated_evidence_ids=sorted(set(fabricated)),
        claims_with_fabricated_ids=bad_claims,
    )
