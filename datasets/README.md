# Evaluation dataset (Stage 4)

Agent-visible inputs live in `agent_inputs/`.  
Answer keys live in `ground_truth/` and **must never** be passed to agents.

## Case catalog

| case_id | type | input | ground truth | status |
|---|---|---|---|---|
| Q2_1 | email | `Q2_1.eml` | `Q2_1.json` | ready |
| Q2_2 | email | `Q2_2.eml` | `Q2_2.json` | ready |
| Q3 | network | `Q3.pcap` (local; gitignored) | `Q3.json` | ready |
| sample_eve | ids | `sample_eve.json` | `sample_eve.json` | ready |
| benign_newsletter | email | `benign_newsletter.eml` | `benign_newsletter.json` | ready |
| benign_legit_mail | email | `benign_legit_mail.eml` | `benign_legit_mail.json` | ready |
| spam_promo | email | `spam_promo.eml` | `spam_promo.json` | ready |
| phishing_bank_lure | email | `phishing_bank_lure.eml` | `phishing_bank_lure.json` | ready |
| suspicious_vendor_mismatch | email | `suspicious_vendor_mismatch.eml` | `suspicious_vendor_mismatch.json` | ready |
| mta_public_1 | network | `mta_public_1.pcap` (local) | `mta_public_1.json` | ready |
| mta_public_2 | network | `mta_public_2.pcap` (local) | `mta_public_2.json` | ready |
| mta_public_3 | network | `mta_public_3.pcap` (local) | `mta_public_3.json` | ready |

Ready now: **12** cases (includes **2 benign**). Target: 10–15 — met.

## Ground-truth schema

- `case_id`, `source_file`, `classification`
- `key_indicators`, `attack_techniques`, `notes`

## Notes

- Large pcaps are gitignored; keep a local copy for reproduction.
- Public captures: follow `SOURCES.md` and credit malware-traffic-analysis.net.
