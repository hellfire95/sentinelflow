"""Smoke-test: parse every agent_inputs file and check ground-truth coverage."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sentinelflow.pipeline import parse_file  # noqa: E402

INPUTS = ROOT / "datasets" / "agent_inputs"
GT = ROOT / "datasets" / "ground_truth"
CATALOG = ROOT / "datasets" / "catalog.json"


def main() -> int:
    catalog = json.loads(CATALOG.read_text())
    failures = 0

    for case in catalog["cases"]:
        if not case.get("ready"):
            continue
        case_id = case["case_id"]
        input_path = ROOT / "datasets" / case["input"]
        gt_path = ROOT / "datasets" / case["ground_truth"]
        print(f"== {case_id} ==")
        if not input_path.exists():
            # pcaps may be gitignored / missing locally
            print(f"  SKIP missing input: {input_path.name}")
            continue
        if not gt_path.exists():
            print(f"  FAIL missing ground truth: {gt_path.name}")
            failures += 1
            continue
        gt = json.loads(gt_path.read_text())
        if gt.get("classification", "").startswith("TODO") or "TODO" in str(gt.get("classification", "")):
            print("  FAIL ground truth still has TODO classification")
            failures += 1
            continue
        try:
            evidence = parse_file(str(input_path), case_id)
        except Exception as e:
            print(f"  FAIL parse error: {e}")
            failures += 1
            continue
        print(f"  OK parse -> {len(evidence)} evidence; GT class={gt['classification']}")

    if failures:
        print(f"\n{failures} failure(s)")
        return 1
    print("\nAll ready cases passed smoke checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
