"""Extract IOCs from Evidence and append threat-intel Evidence items."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from ..models import Evidence, EvidenceCategory
from .client import ThreatIntelClient

# No leading zeros (avoids date fragments like 07.29.11.08).
_IP = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)\b"
)
_SHA256 = re.compile(r"\b[a-fA-F0-9]{64}\b")
_DOMAINISH = re.compile(
    r"\b(?:[a-zA-Z0-9-]+\.)+(?:[a-zA-Z]{2,})\b"
)

# Caps keep free-tier usage and agent context small.
MAX_IPS = 5
MAX_DOMAINS = 5
MAX_HASHES = 3

# Skip common noise / private ranges for reputation (still leave in evidence store).
_SKIP_DOMAINS = {
    "example.com",
    "example.org",
    "localhost",
    "localdomain",
    "google.com",
    "gmail.com",
    "gstatic.com",
    "googleapis.com",
    "microsoft.com",
    "outlook.com",
    "protection.outlook.com",
    "office365.com",
    "apple.com",
    "cloudflare.com",
}
_PRIVATE_IP_PREFIXES = ("10.", "192.168.", "127.", "0.")


def _is_private_ip(ip: str) -> bool:
    if ip.startswith(_PRIVATE_IP_PREFIXES) or ip.startswith("172."):
        # 172.16–172.31 is private; coarse check is fine for portfolio scope.
        if ip.startswith("172."):
            try:
                second = int(ip.split(".")[1])
                return 16 <= second <= 31
            except ValueError:
                return False
        return True
    return False


def _plausible_domain(domain: str) -> bool:
    domain = domain.lower().rstrip(".")
    if domain.endswith((".local", ".test", ".invalid")):
        return False
    if any(domain == s or domain.endswith("." + s) for s in _SKIP_DOMAINS):
        return False
    if re.fullmatch(r"\d+(?:\.\d+)+", domain):
        return False
    # Reject auth-header leftovers like "smtp.mailfrom" / "header.from"
    if domain.startswith(("smtp.", "header.", "client.")) and domain.count(".") == 1:
        return False
    labels = domain.split(".")
    if len(labels) < 2:
        return False
    tld = labels[-1]
    if not tld.isalpha() or len(tld) < 2:
        return False
    return True


def extract_iocs(evidence: list[Evidence]) -> dict[str, list[str]]:
    ips: list[str] = []
    domains: list[str] = []
    hashes: list[str] = []

    for e in evidence:
        text = e.value  # value only — labels create false domain hits
        for ip in _IP.findall(text):
            if not _is_private_ip(ip) and ip not in ips:
                ips.append(ip)
        for h in _SHA256.findall(text):
            h = h.lower()
            if h not in hashes:
                hashes.append(h)
        if e.category == EvidenceCategory.URL and "URL" in e.label:
            host = urlparse(e.value).hostname
            if host and _plausible_domain(host) and host.lower() not in domains:
                domains.append(host.lower())
        elif e.category in (
            EvidenceCategory.HEADER,
            EvidenceCategory.AUTHENTICATION,
            EvidenceCategory.NETWORK,
        ):
            for d in _DOMAINISH.findall(text):
                d = d.lower().rstrip(".")
                if _plausible_domain(d) and d not in domains:
                    domains.append(d)

    return {
        "ip": ips[:MAX_IPS],
        "domain": domains[:MAX_DOMAINS],
        "file_hash": hashes[:MAX_HASHES],
    }


def enrich_evidence(
    case_id: str,
    evidence: list[Evidence],
    client: ThreatIntelClient | None = None,
) -> list[Evidence]:
    """Return new threat-intel Evidence items (does not mutate input list)."""
    client = client or ThreatIntelClient()
    iocs = extract_iocs(evidence)
    start = len(evidence)
    added: list[Evidence] = []

    def _next_id() -> str:
        return f"{case_id}-EV{start + len(added) + 1:03d}"

    for ip in iocs["ip"]:
        result = client.lookup_ip_reputation(ip)
        added.append(
            Evidence(
                id=_next_id(),
                case_id=case_id,
                category=EvidenceCategory.THREAT_INTEL,
                label=f"IP reputation: {ip}",
                value=_format(result),
                source_location="threat_intel:lookup_ip_reputation",
            )
        )
    for domain in iocs["domain"]:
        result = client.lookup_domain_reputation(domain)
        added.append(
            Evidence(
                id=_next_id(),
                case_id=case_id,
                category=EvidenceCategory.THREAT_INTEL,
                label=f"Domain reputation: {domain}",
                value=_format(result),
                source_location="threat_intel:lookup_domain_reputation",
            )
        )
    for file_hash in iocs["file_hash"]:
        result = client.lookup_file_hash(file_hash)
        added.append(
            Evidence(
                id=_next_id(),
                case_id=case_id,
                category=EvidenceCategory.THREAT_INTEL,
                label=f"File hash reputation: {file_hash[:12]}…",
                value=_format(result),
                source_location="threat_intel:lookup_file_hash",
            )
        )
    return added


def _format(result: dict) -> str:
    cached = "cached" if result.get("cached") else "live"
    return (
        f"provider={result.get('provider')} status={result.get('status')} "
        f"({cached}) {result.get('summary')}"
    )
