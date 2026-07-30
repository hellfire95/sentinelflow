# Evaluation dataset (Stage 4)

Agent-visible inputs live in `agent_inputs/`.  
Answer keys live in `ground_truth/` and **must never** be passed to agents.

## Case catalog

| case_id | type | input file | ground truth | status |
|---|---|---|---|---|
| Q2_1 | email | `agent_inputs/Q2_1.eml` | `ground_truth/Q2_1.json` | present (fill GT) |
| Q2_2 | email | `agent_inputs/Q2_2.eml` | `ground_truth/Q2_2.json` | present (fill GT) |
| Q3 | network | `agent_inputs/Q3.pcap` (local; gitignored) | `ground_truth/Q3.json` | present (fill GT) |
| sample_eve | ids | `agent_inputs/sample_eve.json` | `ground_truth/sample_eve.json` | sample / synthetic |
| benign_newsletter | email | TBD | TBD | planned |
| benign_legit_mail | email | TBD | TBD | planned |
| mta_public_1 | network | TBD (malware-traffic-analysis.net) | TBD | planned |
| mta_public_2 | network | TBD | TBD | planned |
| mta_public_3 | network | TBD | TBD | planned |

Target: **10–15 cases**, including **≥2 benign**.

## Ground-truth schema

Each `ground_truth/<case_id>.json` should include:

- `case_id`, `source_file`, `classification` (enum)
- `key_indicators` (list of strings)
- `attack_techniques` (ATT&CK IDs / names)
- `notes` (author analysis; never shown to agents)

## Notes

- Large pcaps are gitignored; keep a local copy for reproduction.
- Public captures: attribute malware-traffic-analysis.net when used.
