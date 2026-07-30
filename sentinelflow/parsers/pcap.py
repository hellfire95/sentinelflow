"""Deterministic pcap parser built on tshark. No LLM involvement.

Design constraint (see project plan): a pcap can hold hundreds of thousands
of packets, so we never emit per-packet evidence. We extract a FIXED set of
aggregated summaries, each capped, so the evidence store stays small enough
for agent context regardless of capture size:

  1. Capture metadata (packet count, size, time span)
  2. DNS queries        (top N unique names by count)
  3. HTTP requests      (top N method+host aggregates, with rate stats)
  4. TLS SNI hostnames  (top N unique server names)
  5. ICMP type counts   (floods show up here)
  6. Top conversations  (top N endpoint pairs by bytes)
"""

import subprocess
from collections import Counter, defaultdict

from ..models import Evidence, EvidenceCategory
from .common import EvidenceBuilder

MAX_DNS = 20
MAX_HTTP = 15
MAX_SNI = 20
MAX_CONVERSATIONS = 10


def _tshark(path: str, args: list[str]) -> list[str]:
    result = subprocess.run(
        ["tshark", "-r", path, *args],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(f"tshark failed: {result.stderr.strip()[:200]}")
    return [line for line in result.stdout.splitlines() if line.strip()]


def _fields(path: str, display_filter: str, fields: list[str]) -> list[list[str]]:
    args = ["-Y", display_filter, "-T", "fields"]
    for f in fields:
        args += ["-e", f]
    args += ["-E", "separator=|"]
    return [line.split("|") for line in _tshark(path, args)]


def parse_pcap(path: str, case_id: str) -> list[Evidence]:
    b = EvidenceBuilder(case_id)
    _capture_summary(path, b)
    _dns_queries(path, b)
    _http_requests(path, b)
    _tls_sni(path, b)
    _icmp_summary(path, b)
    _top_conversations(path, b)
    return b.items


def _capture_summary(path: str, b: EvidenceBuilder) -> None:
    rows = _fields(path, "frame", ["frame.time_epoch", "frame.len"])
    times = [float(r[0]) for r in rows if r and r[0]]
    total_bytes = sum(int(r[1]) for r in rows if len(r) > 1 and r[1])
    b.add(
        EvidenceCategory.NETWORK,
        "Capture summary",
        f"{len(rows)} packets, {total_bytes} bytes, "
        f"epoch time range {min(times):.0f}..{max(times):.0f} "
        f"({max(times) - min(times):.0f}s span; a very large span suggests "
        f"merged captures)",
        "pcap:frame",
    )


def _dns_queries(path: str, b: EvidenceBuilder) -> None:
    rows = _fields(path, "dns.flags.response == 0", ["dns.qry.name"])
    names = Counter()
    for r in rows:
        for name in r[0].split(","):
            if name:
                names[name.lower()] += 1
    b.add(
        EvidenceCategory.NETWORK,
        "DNS query volume",
        f"{sum(names.values())} DNS queries for {len(names)} unique names",
        "pcap:dns",
    )
    for name, count in names.most_common(MAX_DNS):
        b.add(
            EvidenceCategory.NETWORK,
            "DNS query",
            f"{name} (queried {count}x)",
            "pcap:dns.qry.name",
        )
    if len(names) > MAX_DNS:
        b.add(
            EvidenceCategory.NETWORK,
            "DNS extraction truncated",
            f"{len(names) - MAX_DNS} further unique names omitted (cap {MAX_DNS})",
            "derived:cap",
        )


def _http_requests(path: str, b: EvidenceBuilder) -> None:
    rows = _fields(
        path,
        "http.request",
        [
            "frame.time_epoch",
            "ip.src",
            "http.request.method",
            "http.host",
            "http.request.uri",
            "http.user_agent",
        ],
    )
    groups: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"count": 0, "times": [], "uris": Counter(), "agents": set(), "srcs": set()}
    )
    for r in rows:
        if len(r) < 6:
            continue
        time_epoch, src, method, host, uri, agent = r[:6]
        g = groups[(method or "?", host or "?")]
        g["count"] += 1
        if time_epoch:
            g["times"].append(float(time_epoch))
        if uri:
            g["uris"][uri] += 1
        if agent:
            g["agents"].add(agent)
        if src:
            g["srcs"].add(src)

    b.add(
        EvidenceCategory.NETWORK,
        "HTTP request volume",
        f"{len(rows)} HTTP requests to {len(groups)} unique method+host pairs",
        "pcap:http",
    )
    ranked = sorted(groups.items(), key=lambda kv: -kv[1]["count"])
    for (method, host), g in ranked[:MAX_HTTP]:
        span = max(g["times"]) - min(g["times"]) if len(g["times"]) > 1 else 0.0
        rate = f", {g['count'] / span:.1f} req/s over {span:.0f}s" if span > 0 else ""
        top_uris = "; ".join(f"{u} ({c}x)" for u, c in g["uris"].most_common(3))
        agents = "; ".join(sorted(g["agents"])[:2]) or "(none)"
        b.add(
            EvidenceCategory.NETWORK,
            "HTTP request aggregate",
            f"{g['count']}x {method} to host '{host}' from {len(g['srcs'])} "
            f"source IP(s) {sorted(g['srcs'])[:3]}{rate}. "
            f"Top URIs: {top_uris}. User-Agent(s): {agents}",
            "pcap:http.request",
        )


def _tls_sni(path: str, b: EvidenceBuilder) -> None:
    rows = _fields(
        path,
        "tls.handshake.type == 1 && tls.handshake.extensions_server_name",
        ["tls.handshake.extensions_server_name"],
    )
    names = Counter(r[0].lower() for r in rows if r and r[0])
    b.add(
        EvidenceCategory.NETWORK,
        "TLS SNI volume",
        f"{sum(names.values())} TLS client hellos naming {len(names)} unique hosts",
        "pcap:tls",
    )
    for name, count in names.most_common(MAX_SNI):
        b.add(
            EvidenceCategory.NETWORK,
            "TLS SNI hostname",
            f"{name} ({count} handshakes)",
            "pcap:tls.handshake.extensions_server_name",
        )
    if len(names) > MAX_SNI:
        b.add(
            EvidenceCategory.NETWORK,
            "TLS SNI extraction truncated",
            f"{len(names) - MAX_SNI} further unique hosts omitted (cap {MAX_SNI})",
            "derived:cap",
        )


def _icmp_summary(path: str, b: EvidenceBuilder) -> None:
    rows = _fields(path, "icmp", ["icmp.type", "ip.src", "ip.dst"])
    if not rows:
        return
    type_names = {"0": "echo reply", "3": "dest unreachable", "8": "echo request", "11": "time exceeded"}
    types = Counter(r[0] for r in rows if r and r[0])
    # tshark can emit comma-joined IPs on some encapsulations; take the first.
    pairs = Counter(
        f"{r[1].split(',')[0]} -> {r[2].split(',')[0]}"
        for r in rows
        if len(r) > 2 and r[1] and r[2]
    )
    breakdown = ", ".join(
        f"type {t} ({type_names.get(t, 'other')}): {c}x" for t, c in types.most_common()
    )
    top_pairs = "; ".join(f"{p} ({c}x)" for p, c in pairs.most_common(3))
    b.add(
        EvidenceCategory.NETWORK,
        "ICMP summary",
        f"{len(rows)} ICMP packets. {breakdown}. Top src->dst pairs: {top_pairs}",
        "pcap:icmp",
    )


def _top_conversations(path: str, b: EvidenceBuilder) -> None:
    rows = _fields(path, "ip", ["ip.src", "ip.dst", "frame.len"])
    convs: Counter = Counter()
    packets: Counter = Counter()
    for r in rows:
        if len(r) < 3 or not (r[0] and r[1]):
            continue
        pair = " <-> ".join(sorted([r[0], r[1]]))
        convs[pair] += int(r[2] or 0)
        packets[pair] += 1
    for pair, nbytes in convs.most_common(MAX_CONVERSATIONS):
        b.add(
            EvidenceCategory.NETWORK,
            "Top conversation by bytes",
            f"{pair}: {packets[pair]} packets, {nbytes} bytes",
            "pcap:ip",
        )
