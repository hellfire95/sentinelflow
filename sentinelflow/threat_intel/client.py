"""Public lookup API used by enrichment and the MCP server."""

from __future__ import annotations

from typing import Any

from .cache import IntelCache
from .providers import get_provider
from .rate_limit import RateLimiter

# VirusTotal free tier: 4 requests/minute, 500/day.
_limiter = RateLimiter(max_calls=4, per_seconds=60.0)
_cache = IntelCache()


class ThreatIntelClient:
    def __init__(self, cache: IntelCache | None = None, limiter: RateLimiter | None = None):
        self.cache = cache or _cache
        self.limiter = limiter or _limiter
        self.provider = get_provider()

    def _lookup(self, ioc_type: str, value: str, fetch) -> dict[str, Any]:
        value = value.strip()
        cached = self.cache.get(ioc_type, value)
        if cached is not None:
            return cached
        # Offline provider does not hit the network — no rate-limit wait needed.
        if getattr(self.provider, "name", "") != "offline":
            self.limiter.wait()
        result = fetch(value)
        self.cache.put(ioc_type, value, result)
        result = dict(result)
        result["cached"] = False
        return result

    def lookup_ip_reputation(self, ip: str) -> dict[str, Any]:
        return self._lookup("ip", ip, self.provider.lookup_ip)

    def lookup_domain_reputation(self, domain: str) -> dict[str, Any]:
        return self._lookup("domain", domain, self.provider.lookup_domain)

    def lookup_file_hash(self, file_hash: str) -> dict[str, Any]:
        return self._lookup("file_hash", file_hash, self.provider.lookup_hash)


_default = ThreatIntelClient()


def lookup_ip_reputation(ip: str) -> dict[str, Any]:
    return _default.lookup_ip_reputation(ip)


def lookup_domain_reputation(domain: str) -> dict[str, Any]:
    return _default.lookup_domain_reputation(domain)


def lookup_file_hash(file_hash: str) -> dict[str, Any]:
    return _default.lookup_file_hash(file_hash)
