"""Stage 5 evaluation runner.

Runs every ready catalog case through:
  - investigator_only (baseline)
  - full (Investigator + Critic)

Each configuration is repeated EVAL_RUNS times (default 3). Report LLM is
skipped to save quota — scoring uses hypothesis + mechanical precheck only.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sentinelflow.eval_score import score_run, summarize_mode  # noqa: E402
from sentinelflow.graph import run_case  # noqa: E402

CATALOG = ROOT / "datasets" / "catalog.json"
EVAL_DIR = ROOT / "docs" / "eval_runs"
DEFAULT_RUNS = 3
MODES = ("investigator_only", "full")


def load_cases() -> list[dict]:
    catalog = json.loads(CATALOG.read_text())
    return [c for c in catalog["cases"] if c.get("ready")]


def run_one(case: dict, mode: str, run_idx: int, write_report: bool) -> dict:
    case_id = case["case_id"]
    path = ROOT / "datasets" / case["input"]
    if not path.exists():
        raise FileNotFoundError(f"missing input: {path}")
    label = f"eval/{mode}/{case_id}/r{run_idx}"
    run_dir = run_case(
        str(path),
        case_id,
        mode=mode,
        write_report=write_report,
        run_label=label,
    )
    result = json.loads((run_dir / "result.json").read_text())
    gt = json.loads((ROOT / "datasets" / case["ground_truth"]).read_text())
    scored = score_run(result, gt)
    scored["run_dir"] = str(run_dir)
    scored["run_index"] = run_idx
    return scored


def write_markdown(summary: dict, out: Path) -> None:
    lines = [
        "# SentinelFlow Stage 5 Evaluation Results",
        "",
        f"Generated: {summary['generated_at']}",
        f"Model: `{summary['model']}`",
        f"Runs per case/config: **{summary['runs_per_config']}**",
        f"Cases: **{summary['case_count']}**",
        "",
        "## Headline metrics",
        "",
        "| Config | Majority classification accuracy | Mean run accuracy | Mean citation existence | Mean mechanical unsupported-claim rate | Unresolved rate |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for mode in MODES:
        h = summary["headline"][mode]
        lines.append(
            f"| {mode} | {h['majority_accuracy']:.1%} | {h['run_accuracy_mean']:.1%} | "
            f"{h['citation_existence_mean']:.1%} | {h['mechanical_unsupported_rate_mean']:.1%} | "
            f"{h['unresolved_rate']:.1%} |"
        )
    lines += [
        "",
        "## Per-case majority outcomes",
        "",
        "| Case | Ground truth | Investigator-only majority | Full majority | IO correct | Full correct |",
        "|---|---|---|---|---|---|",
    ]
    for row in summary["per_case"]:
        lines.append(
            f"| {row['case_id']} | {row['gt']} | {row['investigator_only_majority']} | "
            f"{row['full_majority']} | {row['investigator_only_correct']} | {row['full_correct']} |"
        )
    lines += [
        "",
        "## Notes",
        "",
        "- Metric 2 (full unsupported-claim rate) and Metric 3b (citation relevance) still need",
        "  **human** blinded grading per `docs/evaluation_rubric.md`.",
        "- Mechanical unsupported rate counts only claims that cited fabricated evidence IDs.",
        "- Report agent was skipped during this eval (`write_report=False`) to reduce API use.",
        "",
        f"Raw machine-readable summary: `{out.with_suffix('.json').name}`",
        "",
    ]
    out.write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Stage 5 evaluation")
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS)
    parser.add_argument("--case-id", action="append", help="limit to specific case_id(s)")
    parser.add_argument("--mode", choices=[*MODES, "both"], default="both")
    parser.add_argument("--write-report", action="store_true", help="also run Report LLM")
    parser.add_argument("--sleep", type=float, default=1.0, help="pause between runs (sec)")
    args = parser.parse_args()

    cases = load_cases()
    if args.case_id:
        wanted = set(args.case_id)
        cases = [c for c in cases if c["case_id"] in wanted]
    if not cases:
        print("No cases to run", file=sys.stderr)
        return 1

    modes = list(MODES) if args.mode == "both" else [args.mode]
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    all_scores: list[dict] = []
    failures: list[dict] = []

    total = len(cases) * len(modes) * args.runs
    done = 0
    model = None

    for case in cases:
        for mode in modes:
            for run_idx in range(1, args.runs + 1):
                done += 1
                tag = f"[{done}/{total}] {case['case_id']} {mode} r{run_idx}"
                print(tag, flush=True)
                try:
                    scored = run_one(case, mode, run_idx, write_report=args.write_report)
                    all_scores.append(scored)
                    if model is None:
                        # peek settings from last result path
                        model = "see run artifacts"
                    print(
                        f"  -> pred={scored['pred_classification']} "
                        f"correct={scored['classification_correct']} "
                        f"cite_exist={scored['citation_existence_rate']:.2f}",
                        flush=True,
                    )
                except Exception as e:
                    print(f"  FAIL: {e}", flush=True)
                    failures.append(
                        {
                            "case_id": case["case_id"],
                            "mode": mode,
                            "run_index": run_idx,
                            "error": str(e),
                            "traceback": traceback.format_exc(),
                        }
                    )
                time.sleep(args.sleep)

    # Aggregate
    per_case = []
    headline = {}
    for mode in modes:
        mode_case_summaries = []
        for case in cases:
            cid = case["case_id"]
            scores = [
                s
                for s in all_scores
                if s.get("case_id") == cid and s.get("mode") == mode
            ]
            if not scores:
                continue
            sm = summarize_mode(scores)
            mode_case_summaries.append(sm)
        if mode_case_summaries:
            headline[mode] = {
                "majority_accuracy": sum(
                    1 for s in mode_case_summaries if s.get("majority_correct")
                )
                / len(mode_case_summaries),
                "run_accuracy_mean": sum(
                    s.get("run_accuracy_mean", 0) for s in mode_case_summaries
                )
                / len(mode_case_summaries),
                "citation_existence_mean": sum(
                    s.get("citation_existence_mean", 0) for s in mode_case_summaries
                )
                / len(mode_case_summaries),
                "mechanical_unsupported_rate_mean": sum(
                    s.get("mechanical_unsupported_rate_mean", 0)
                    for s in mode_case_summaries
                )
                / len(mode_case_summaries),
                "unresolved_rate": sum(
                    s.get("unresolved_rate", 0) for s in mode_case_summaries
                )
                / len(mode_case_summaries),
            }

    for case in cases:
        cid = case["case_id"]
        gt = json.loads((ROOT / "datasets" / case["ground_truth"]).read_text())[
            "classification"
        ]
        row = {"case_id": cid, "gt": gt}
        for mode in MODES:
            scores = [
                s
                for s in all_scores
                if s.get("case_id") == cid and s.get("mode") == mode
            ]
            sm = summarize_mode(scores) if scores else {}
            row[f"{mode}_majority"] = sm.get("majority_prediction")
            row[f"{mode}_correct"] = sm.get("majority_correct")
        per_case.append(row)

    # Infer model from a result artifact if present
    if all_scores:
        sample = Path(all_scores[0]["run_dir"]) / "result.json"
        if sample.exists():
            model = json.loads(sample.read_text()).get("model_settings", {}).get(
                "model", model
            )

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "runs_per_config": args.runs,
        "case_count": len(cases),
        "modes": modes,
        "headline": headline,
        "per_case": per_case,
        "run_scores": all_scores,
        "failures": failures,
    }

    json_path = EVAL_DIR / f"summary_{stamp}.json"
    md_path = EVAL_DIR / f"summary_{stamp}.md"
    latest_json = EVAL_DIR / "latest_summary.json"
    latest_md = ROOT / "docs" / "evaluation_results.md"

    json_path.write_text(json.dumps(summary, indent=2))
    latest_json.write_text(json.dumps(summary, indent=2))
    write_markdown(summary, md_path)
    write_markdown(summary, latest_md)

    print(f"\nWrote {json_path}")
    print(f"Wrote {latest_md}")
    print(f"Failures: {len(failures)}")
    return 1 if failures and not all_scores else 0


if __name__ == "__main__":
    raise SystemExit(main())
