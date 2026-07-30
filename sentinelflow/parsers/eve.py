"""Deterministic Suricata eve.json parser. No LLM involvement.

eve.json is a file of JSON objects, one per line, describing IDS events.
We extract alert events aggregated by signature (a raw alert list can hold
thousands of duplicate hits), plus a summary of event types seen.
"""

import json
from collections import Counter, defaultdict

from ..models import Evidence, EvidenceCategory
from .common import EvidenceBuilder

MAX_SIGNATURES = 25


def parse_eve(path: str, case_id: str) -> list[Evidence]:
    b = EvidenceBuilder(case_id)
    event_types: Counter = Counter()
    alerts: dict[str, dict] = defaultdict(
        lambda: {"count": 0, "severity": None, "category": "", "pairs": Counter()}
    )

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            event_types[event.get("event_type", "unknown")] += 1
            if event.get("event_type") != "alert":
                continue
            alert = event.get("alert", {})
            sig = alert.get("signature", "(unnamed signature)")
            a = alerts[sig]
            a["count"] += 1
            a["severity"] = alert.get("severity", a["severity"])
            a["category"] = alert.get("category", a["category"])
            src, dst = event.get("src_ip", "?"), event.get("dest_ip", "?")
            a["pairs"][f"{src} -> {dst}"] += 1

    b.add(
        EvidenceCategory.NETWORK,
        "IDS event summary",
        ", ".join(f"{t}: {c}" for t, c in event_types.most_common()) or "no events",
        "eve:event_type",
    )
    ranked = sorted(alerts.items(), key=lambda kv: (kv[1]["severity"] or 99, -kv[1]["count"]))
    for sig, a in ranked[:MAX_SIGNATURES]:
        top_pairs = "; ".join(f"{p} ({c}x)" for p, c in a["pairs"].most_common(3))
        b.add(
            EvidenceCategory.NETWORK,
            "IDS alert signature",
            f"'{sig}' fired {a['count']}x (severity {a['severity']}, "
            f"category '{a['category']}'). Top src->dst: {top_pairs}",
            "eve:alert",
        )
    if len(alerts) > MAX_SIGNATURES:
        b.add(
            EvidenceCategory.NETWORK,
            "IDS alert extraction truncated",
            f"{len(alerts) - MAX_SIGNATURES} further signatures omitted (cap {MAX_SIGNATURES})",
            "derived:cap",
        )
    return b.items
