"""MCP server exposing threat-intel lookup tools.

Run:
  .venv/bin/python mcp_servers/threat_intel_server.py

Tools:
  - lookup_ip_reputation
  - lookup_domain_reputation
  - lookup_file_hash

Uses the same cached client as the SentinelFlow pipeline.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running as a script from repo root.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mcp.server.mcpserver import MCPServer

from sentinelflow.threat_intel import (
    lookup_domain_reputation,
    lookup_file_hash,
    lookup_ip_reputation,
)

mcp = MCPServer("sentinelflow-threat-intel")


@mcp.tool()
def lookup_ip_reputation_tool(ip: str) -> str:
    """Look up reputation for an IPv4 address (cached; VirusTotal if API key set)."""
    return json.dumps(lookup_ip_reputation(ip), indent=2)


@mcp.tool()
def lookup_domain_reputation_tool(domain: str) -> str:
    """Look up reputation for a domain name (cached; VirusTotal if API key set)."""
    return json.dumps(lookup_domain_reputation(domain), indent=2)


@mcp.tool()
def lookup_file_hash_tool(file_hash: str) -> str:
    """Look up reputation for a file SHA-256 hash (cached; VirusTotal if API key set)."""
    return json.dumps(lookup_file_hash(file_hash), indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
