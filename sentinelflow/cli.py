"""Command-line interface.

  python -m sentinelflow.cli parse datasets/agent_inputs/Q2_1.eml
  python -m sentinelflow.cli run datasets/agent_inputs/Q2_1.eml
  python -m sentinelflow.cli actions list
  python -m sentinelflow.cli actions decide Q2_1-ACT001 --approve
"""

import argparse
import sys
from pathlib import Path

from .approval import decide_action, list_actions
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
    enrich = None
    if args.threat_intel:
        enrich = True
    if args.no_threat_intel:
        enrich = False
    run_dir = run_case(
        args.file,
        case_id,
        mode=mode,
        write_report=not args.no_report,
        enrich_threat_intel=enrich,
    )
    print(f"Run complete. Artifacts in: {run_dir}")
    print(f"  - {run_dir / 'trace.jsonl'}")
    print(f"  - {run_dir / 'result.json'}")
    print(f"  - {run_dir / 'report.md'}")
    actions_path = run_dir / "actions.json"
    if actions_path.exists():
        print(f"  - {actions_path}")
        print(
            "Pending actions require human approval "
            "(simulated only — nothing is executed):\n"
            f"  .venv/bin/python -m sentinelflow.cli actions list --case-id {case_id}"
        )


def cmd_actions_list(args: argparse.Namespace) -> None:
    store = EvidenceStore()
    actions = list_actions(
        store, case_id=args.case_id, pending_only=args.pending
    )
    if not actions:
        print("No actions found.")
        return
    for a in actions:
        print(f"[{a.action_id}] {a.status.value}  executed={a.executed}")
        print(f"    case: {a.case_id}")
        print(f"    action: {a.description}")
        if a.decided_by:
            print(f"    decided_by: {a.decided_by} at {a.decided_at}")
        if a.note:
            print(f"    note: {a.note}")


def cmd_lookup(args: argparse.Namespace) -> None:
    import json

    from .threat_intel import (
        lookup_domain_reputation,
        lookup_file_hash,
        lookup_ip_reputation,
    )

    if args.ip:
        print(json.dumps(lookup_ip_reputation(args.ip), indent=2))
    elif args.domain:
        print(json.dumps(lookup_domain_reputation(args.domain), indent=2))
    elif args.hash:
        print(json.dumps(lookup_file_hash(args.hash), indent=2))
    else:
        raise RuntimeError("Specify --ip, --domain, or --hash")


def cmd_actions_decide(args: argparse.Namespace) -> None:
    if args.approve == args.reject:
        raise RuntimeError("Specify exactly one of --approve or --reject")
    store = EvidenceStore()
    action = decide_action(
        store,
        args.action_id,
        approve=bool(args.approve),
        decided_by=args.by,
        note=args.note,
    )
    print(
        f"{action.action_id} -> {action.status.value} "
        f"(executed={action.executed}; simulated only)"
    )


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
    p_run.add_argument(
        "--threat-intel",
        action="store_true",
        help="force Stage 7 threat-intel enrichment on",
    )
    p_run.add_argument(
        "--no-threat-intel",
        action="store_true",
        help="disable Stage 7 threat-intel enrichment",
    )
    p_run.set_defaults(func=cmd_run)

    p_lookup = sub.add_parser(
        "lookup",
        help="threat-intel lookup (cached; VirusTotal if VIRUSTOTAL_API_KEY set)",
    )
    p_lookup.add_argument("--ip")
    p_lookup.add_argument("--domain")
    p_lookup.add_argument("--hash", dest="hash")
    p_lookup.set_defaults(func=cmd_lookup)

    p_actions = sub.add_parser(
        "actions",
        help="human approval gateway for recommended actions (simulated)",
    )
    actions_sub = p_actions.add_subparsers(dest="actions_command", required=True)

    p_list = actions_sub.add_parser("list", help="list proposed actions")
    p_list.add_argument("--case-id")
    p_list.add_argument(
        "--pending", action="store_true", help="only show pending actions"
    )
    p_list.set_defaults(func=cmd_actions_list)

    p_decide = actions_sub.add_parser(
        "decide", help="approve or reject a pending action (never executes)"
    )
    p_decide.add_argument("action_id")
    p_decide.add_argument("--approve", action="store_true")
    p_decide.add_argument("--reject", action="store_true")
    p_decide.add_argument("--by", default="human", help="approver name")
    p_decide.add_argument("--note", default=None)
    p_decide.set_defaults(func=cmd_actions_decide)

    args = parser.parse_args()
    try:
        args.func(args)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
