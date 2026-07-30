# SentinelFlow

Evidence-grounded multi-agent cybersecurity investigation system. Raw security
evidence (phishing emails, network telemetry) goes in; a traceable incident
report comes out — every claim cites specific extracted evidence, and a Critic
agent challenges claims that don't hold up.

**Core design decision:** deterministic work (parsing) is done in plain code;
the LLM only ever sees clean, structured, already-extracted evidence.

## Pipeline

```
.eml / .pcap / eve.json
   │  deterministic parsers (no LLM)
   ▼
Evidence objects (stable IDs) → SQLite store
   │
   ▼
Investigator ── hypothesis with evidence-cited claims
   │
   ▼
Mechanical precheck (code): do all cited evidence IDs exist?
   │
   ▼
Critic ── judges whether cited evidence actually supports each claim
   │
 approve ──────────────► Report agent (no new facts, defanged IOCs)
   │
 revise (max 2) ──► Investigator revises
   │
 still rejected ──► UNRESOLVED: human review required (first-class outcome)
```

Orchestration is a LangGraph state machine (`sentinelflow/graph.py`): same
steps as above, with explicit nodes, a capped revision loop, and
`graph_transition` events in the run trace. Parsers and agents are unchanged.

Supported inputs: `.eml` (email), `.pcap`/`.pcapng` (via tshark), Suricata
`eve.json`. Adding a new input type only requires a new parser — the agents
are evidence-type-agnostic.

## Setup

```bash
# Requires: Python 3.11+, tshark (brew install wireshark)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # then add GEMINI_API_KEY (or another provider key)
```

## Usage

```bash
# Deterministic parse only — no API key needed
.venv/bin/python -m sentinelflow.cli parse datasets/agent_inputs/Q2_1.eml
.venv/bin/python -m sentinelflow.cli parse datasets/agent_inputs/Q3.pcap
.venv/bin/python -m sentinelflow.cli parse datasets/agent_inputs/sample_eve.json

# Full pipeline — requires an LLM API key
.venv/bin/python -m sentinelflow.cli run datasets/agent_inputs/Q2_1.eml
.venv/bin/python -m sentinelflow.cli run datasets/agent_inputs/Q3.pcap
```

Run artifacts land in `runs/<case_id>/<timestamp>/`: `trace.jsonl` (every
agent call and verdict), `result.json` (structured outcome), `report.md`
(readable report, IOCs defanged).

Pcaps are gitignored (too large). Keep a local copy of evaluation captures;
public samples can come from malware-traffic-analysis.net.

## Reproducibility

Model and temperature are pinned in `sentinelflow/config.py` and recorded in
every trace. Evaluation rubric (frozen before first outputs) is in
`docs/evaluation_rubric.md`. Ground truth lives in `datasets/ground_truth/`
and never enters agent context.
