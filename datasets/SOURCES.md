# External sample sources (Stage 4+)

Public network captures are **not** stored in git (size + licensing).
Download locally into `datasets/agent_inputs/` when expanding the eval set.

## malware-traffic-analysis.net

1. Browse a recent blog post with a PCAP exercise.
2. Download the zip, extract the `.pcap` / `.pcapng`.
3. Copy into `datasets/agent_inputs/` as e.g. `mta_public_1.pcap`.
4. Write `datasets/ground_truth/mta_public_N.json` from the post’s documented answers / your analysis.
5. Register the case in `catalog.json`.

Always credit the source in the ground-truth `notes` field.

### SharkFest 2019 US labs (added)

Source: https://malware-traffic-analysis.net/2019/sharkfest/

| local name | original zip | password (on that page) |
|---|---|---|
| `mta_public_1.pcap` | `sf19us-MTA-lab-01.pcap.zip` | `2019_workshop` |
| `mta_public_2.pcap` | `sf19us-MTA-lab-02.pcap.zip` | `2019_workshop` |
| `mta_public_3.pcap` | `sf19us-MTA-lab-03.pcap.zip` | `2019_workshop` |

Other MTA posts use the site-wide password scheme on the [about page](https://www.malware-traffic-analysis.net/about.html) (`infected_YYYYMMDD`).

## Local coursework captures

Keep GET-flood / Qakbot / other personal lab pcaps outside git if large; point `catalog.json` at the local path and keep ground truth in-repo.
