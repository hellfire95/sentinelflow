# SentinelFlow Evaluation Rubric

**Written before any system outputs were generated** (Stage 1), and frozen.
Changes to this rubric after evaluation runs begin must be logged at the
bottom of this file with a reason.

## Configurations compared

- **Baseline:** Investigator only (its first hypothesis is final).
- **Full:** Investigator + Critic revision loop (approved or unresolved).

Each case is run **3 times per configuration** with the pinned model and
temperature recorded in the trace. Report per-case majority outcome and
across-run variance.

## Metric 1 — Classification accuracy

The hypothesis `classification` matches the ground-truth classification for
the case (exact match on the enum: phishing, malware_delivery, spam, benign,
suspicious_inconclusive).

- Ground truth lives in `datasets/ground_truth/<case_id>.json`, never enters
  agent context.
- `suspicious_inconclusive` is correct only if the ground truth says so;
  hedging on a clear-cut case counts as wrong.
- For unresolved cases (Critic never approved), score the final hypothesis
  but report unresolved rate separately.

## Metric 2 — Unsupported-claim rate

Fraction of claims (across all cases in a configuration) judged unsupported.

A claim is **unsupported** if any of:
1. It cites an evidence ID that does not exist (mechanical check).
2. The cited evidence, read verbatim, does not state or directly entail the
   claim's statement (human-judged).
3. The claim asserts a fact present in no cited evidence.

A claim is **supported** if a reasonable analyst, shown only the cited
evidence values, would agree the statement follows. Interpretive framing
("this mismatch is consistent with spoofing") is supported if the underlying
fact is cited; categorical assertions ("this IP is a known C2 server") are
unsupported unless evidence states it.

Judge: the project author, blind to which configuration produced the claim
(shuffle claims before grading).

## Metric 3 — Evidence citation validity

Two separately reported parts:

- **3a. Citation existence (mechanical):** fraction of cited evidence IDs
  that exist in the case's evidence store. Computed by code (`precheck.py`),
  no judgment.
- **3b. Citation relevance (judged):** for existing citations, fraction where
  the cited evidence is actually relevant to the claim it is attached to
  (not merely real but unrelated). Human-judged, same blinding as Metric 2.

## Explicitly out of scope

- Confidence calibration claims (sample too small; confidence is a routing
  signal only).
- ATT&CK technique precision/recall — reported qualitatively per case, not
  as a headline metric.

## Change log

- (none yet)
