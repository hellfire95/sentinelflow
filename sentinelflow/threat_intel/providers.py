"""Reputation providers: VirusTotal (optional) + offline fallback."""

from __future__ import annotations

import os
from typing import Any

import httpx

VT_BASE = "https://www.virustotal.com/api/v3"


def _vt_key() -> str | None:
    return os.environ.get("VIRUSTOTAL_API_KEY") or os.environ.get("VT_API_KEY")


class OfflineProvider:
    """Used when no VirusTotal key is set. Deterministic, no network."""

    name = "offline"

    def lookup_ip(self, ip: str) -> dict[str, Any]:
        return {
            "provider": self.name,
            "ioc_type": "ip",
            "ioc": ip,
            "status": "unavailable",
            "summary": "No VIRUSTOTAL_API_KEY set; reputation lookup skipped.",
            "malicious": None,
            "suspicious": None,
            "harmless": None,
        }

    def lookup_domain(self, domain: str) -> dict[str, Any]:
        return {
            "provider": self.name,
            "ioc_type": "domain",
            "ioc": domain,
            "status": "unavailable",
            "summary": "No VIRUSTOTAL_API_KEY set; reputation lookup skipped.",
            "malicious": None,
            "suspicious": None,
            "harmless": None,
        }

    def lookup_hash(self, file_hash: str) -> dict[str, Any]:
        return {
            "provider": self.name,
            "ioc_type": "file_hash",
            "ioc": file_hash,
            "status": "unavailable",
            "summary": "No VIRUSTOTAL_API_KEY set; reputation lookup skipped.",
            "malicious": None,
            "suspicious": None,
            "harmless": None,
        }


class VirusTotalProvider:
    name = "virustotal"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _get(self, path: str) -> dict[str, Any]:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{VT_BASE}{path}",
                headers={"x-apikey": self.api_key},
            )
            if resp.status_code == 404:
                return {"status": "not_found"}
            resp.raise_for_status()
            return resp.json()

    def _stats(self, data: dict[str, Any]) -> dict[str, Any]:
        attrs = (data.get("data") or {}).get("attributes") or {}
        stats = attrs.get("last_analysis_stats") or {}
        malicious = int(stats.get("malicious") or 0)
        suspicious = int(stats.get("suspicious") or 0)
        harmless = int(stats.get("harmless") or 0)
        undetected = int(stats.get("undetected") or 0)
        return {
            "status": "ok",
            "malicious": malicious,
            "suspicious": suspicious,
            "harmless": harmless,
            "undetected": undetected,
            "summary": (
                f"VT last_analysis_stats: malicious={malicious}, "
                f"suspicious={suspicious}, harmless={harmless}, undetected={undetected}"
            ),
        }

    def lookup_ip(self, ip: str) -> dict[str, Any]:
        raw = self._get(f"/ip_addresses/{ip}")
        if raw.get("status") == "not_found":
            return {
                "provider": self.name,
                "ioc_type": "ip",
                "ioc": ip,
                "status": "not_found",
                "summary": "VirusTotal has no report for this IP.",
                "malicious": 0,
                "suspicious": 0,
                "harmless": 0,
            }
        out = self._stats(raw)
        out.update({"provider": self.name, "ioc_type": "ip", "ioc": ip})
        return out

    def lookup_domain(self, domain: str) -> dict[str, Any]:
        raw = self._get(f"/domains/{domain}")
        if raw.get("status") == "not_found":
            return {
                "provider": self.name,
                "ioc_type": "domain",
                "ioc": domain,
                "status": "not_found",
                "summary": "VirusTotal has no report for this domain.",
                "malicious": 0,
                "suspicious": 0,
                "harmless": 0,
            }
        out = self._stats(raw)
        out.update({"provider": self.name, "ioc_type": "domain", "ioc": domain})
        return out

    def lookup_hash(self, file_hash: str) -> dict[str, Any]:
        raw = self._get(f"/files/{file_hash}")
        if raw.get("status") == "not_found":
            return {
                "provider": self.name,
                "ioc_type": "file_hash",
                "ioc": file_hash,
                "status": "not_found",
                "summary": "VirusTotal has no report for this file hash.",
                "malicious": 0,
                "suspicious": 0,
                "harmless": 0,
            }
        out = self._stats(raw)
        out.update({"provider": self.name, "ioc_type": "file_hash", "ioc": file_hash})
        return out


def get_provider():
    key = _vt_key()
    if key:
        return VirusTotalProvider(key)
    return OfflineProvider()
