"""Mechanical scoring helpers for Stage 5 evaluation.

Human-judged parts of Metric 2 / 3b are left as placeholders — see
docs/evaluation_rubric.md. This module scores what code can score fairly.
"""

from __future__ import annotations

from collections import Counter
from typing import Any


def score_run(result: dict[str, Any], ground_truth: dict[str, Any]) -> dict[str, Any]:
    """Score one run's result.json against a ground-truth file."""
    gt_class = ground_truth.get("classification")
    hyp = result.get("hypothesis") or {}
    pred = hyp.get("classification")
    claims = hyp.get("claims") or []
    precheck = result.get("precheck") or {}
    fabricated = list(precheck.get("fabricated_evidence_ids") or [])

    cited: list[str] = []
    for claim in claims:
        cited.extend(claim.get("evidence_ids") or [])
    for tech in hyp.get("attack_techniques") or []:
        cited.extend(tech.get("evidence_ids") or [])
    cited.extend(hyp.get("contradictory_evidence_ids") or [])

    total_citations = len(cited)
    fabricated_set = set(fabricated)
    existing = sum(1 for c in cited if c not in fabricated_set)
    citation_existence = (existing / total_citations) if total_citations else 1.0

    claims_with_fabricated = list(precheck.get("claims_with_fabricated_ids") or [])
    mechanical_unsupported = len(claims_with_fabricated)
    claim_count = len(claims)
    mechanical_unsupported_rate = (
        mechanical_unsupported / claim_count if claim_count else 0.0
    )

    return {
        "case_id": result.get("case_id"),
        "mode": result.get("mode"),
        "status": result.get("status"),
        "gt_classification": gt_class,
        "pred_classification": pred,
        "classification_correct": pred == gt_class,
        "claim_count": claim_count,
        "citation_count": total_citations,
        "citation_existence_rate": citation_existence,
        "fabricated_evidence_ids": fabricated,
        "mechanical_unsupported_claims": mechanical_unsupported,
        "mechanical_unsupported_rate": mechanical_unsupported_rate,
        "revisions": result.get("revisions", 0),
        "unresolved": result.get("status") == "unresolved_human_review_required",
        # Human-judged metrics — fill later from blinded review:
        "unsupported_claim_rate_human": None,
        "citation_relevance_rate_human": None,
    }


def majority_label(labels: list[str | None]) -> str | None:
    labels = [l for l in labels if l]
    if not labels:
        return None
    return Counter(labels).most_common(1)[0][0]


def summarize_mode(case_scores: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate 3 (or N) runs for one case under one mode."""
    if not case_scores:
        return {}
    preds = [s.get("pred_classification") for s in case_scores]
    majority = majority_label(preds)
    gt = case_scores[0].get("gt_classification")
    correct_flags = [bool(s.get("classification_correct")) for s in case_scores]
    return {
        "case_id": case_scores[0].get("case_id"),
        "mode": case_scores[0].get("mode"),
        "gt_classification": gt,
        "run_predictions": preds,
        "majority_prediction": majority,
        "majority_correct": majority == gt,
        "run_accuracy_mean": sum(correct_flags) / len(correct_flags),
        "citation_existence_mean": sum(
            s.get("citation_existence_rate", 0) for s in case_scores
        )
        / len(case_scores),
        "mechanical_unsupported_rate_mean": sum(
            s.get("mechanical_unsupported_rate", 0) for s in case_scores
        )
        / len(case_scores),
        "unresolved_rate": sum(1 for s in case_scores if s.get("unresolved"))
        / len(case_scores),
        "runs": len(case_scores),
    }
