# SentinelFlow

Evidence-grounded multi-agent cybersecurity investigation system. Raw security
evidence (phishing emails, network telemetry) goes in; a traceable incident
report comes out — every claim cites specific extracted evidence, and a Critic
agent challenges claims that don't hold up.

**Core design decision:** deterministic work (parsing) is done in plain code;
the LLM only ever sees clean, structured, already-extracted evidence.

## Pipeline (Stage 1: email vertical slice)

```
.eml file
   │  deterministic parser (no LLM)
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

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # then add OPENAI_API_KEY or ANTHROPIC_API_KEY
```

## Usage

```bash
# Deterministic parse only — no API key needed
.venv/bin/python -m sentinelflow.cli parse datasets/agent_inputs/Q2_1.eml

# Full pipeline — requires an LLM API key
.venv/bin/python -m sentinelflow.cli run datasets/agent_inputs/Q2_1.eml
```

Run artifacts land in `runs/<case_id>/<timestamp>/`: `trace.jsonl` (every
agent call and verdict), `result.json` (structured outcome), `report.md`
(readable report, IOCs defanged).

## Reproducibility

Model and temperature are pinned in `sentinelflow/config.py` and recorded in
every trace. Evaluation rubric (frozen before first outputs) is in
`docs/evaluation_rubric.md`. Ground truth lives in `datasets/ground_truth/`
and never enters agent context.
