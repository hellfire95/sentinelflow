"""Command-line interface.

  python -m sentinelflow.cli parse datasets/agent_inputs/Q2_1.eml
      Deterministic parse only — prints extracted evidence, no LLM needed.

  python -m sentinelflow.cli run datasets/agent_inputs/Q2_1.eml
      Full pipeline: parse -> investigate -> critic loop -> report.
"""

import argparse
import sys
from pathlib import Path

from .pipeline import parse_file, run_case
from .store import EvidenceStore


def _default_case_id(path: str) -> str:
    return Path(path).stem


def cmd_parse(args: argparse.Namespace) -> None:
    case_id = args.case_id or _default_case_id(args.file)
    evidence = parse_file(args.file, case_id)
    for e in evidence:
        print(f"[{e.id}] ({e.category.value}) {e.label}")
        print(f"    value:  {e.value}")
        print(f"    source: {e.source_location}")
    print(f"\n{len(evidence)} evidence items extracted.")
    if args.save:
        store = EvidenceStore()
        from .pipeline import ingest

        ingest(args.file, case_id, store)
        print(f"Saved to evidence store as case '{case_id}'.")


def cmd_run(args: argparse.Namespace) -> None:
    case_id = args.case_id or _default_case_id(args.file)
    mode = "investigator_only" if args.investigator_only else "full"
    run_dir = run_case(
        args.file,
        case_id,
        mode=mode,
        write_report=not args.no_report,
    )
    print(f"Run complete. Artifacts in: {run_dir}")
    print(f"  - {run_dir / 'trace.jsonl'}")
    print(f"  - {run_dir / 'result.json'}")
    print(f"  - {run_dir / 'report.md'}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="sentinelflow")
    sub = parser.add_subparsers(dest="command", required=True)

    p_parse = sub.add_parser("parse", help="deterministic parse only (no LLM)")
    p_parse.add_argument("file")
    p_parse.add_argument("--case-id")
    p_parse.add_argument("--save", action="store_true", help="persist to SQLite store")
    p_parse.set_defaults(func=cmd_parse)

    p_run = sub.add_parser("run", help="full pipeline (requires LLM API key)")
    p_run.add_argument("file")
    p_run.add_argument("--case-id")
    p_run.add_argument(
        "--investigator-only",
        action="store_true",
        help="baseline: skip Critic revision loop",
    )
    p_run.add_argument(
        "--no-report",
        action="store_true",
        help="skip Report LLM (useful for evaluation)",
    )
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    try:
        args.func(args)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
