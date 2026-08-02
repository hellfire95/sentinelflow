"""Threat-intel lookups (Stage 7): IP / domain / file-hash reputation."""

from .client import ThreatIntelClient, lookup_domain_reputation, lookup_file_hash, lookup_ip_reputation

__all__ = [
    "ThreatIntelClient",
    "lookup_ip_reputation",
    "lookup_domain_reputation",
    "lookup_file_hash",
]
