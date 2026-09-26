---
id: prompt.fragment.audit-scale
version: 1.2.0
status: active
class: fragment
owner: BioETL Team
summary: Unified surface quality score 0-3, optional 0-5/1-5 maps, priority P0-P3
---

## Audit scale

### Surface score (higher = better control maturity)

| Score | Quality | Meaning |
| --- | --- | --- |
| 3 | good | Checks reproducible; material risks closed; automation present |
| 2 | acceptable | Core mechanism correct; local non-critical gaps |
| 1 | weak | Material gaps, manual stages, drift, or weak enforcement |
| 0 | unacceptable | Mechanism missing, systemically broken, or direct risk |

Use **one** `surface_score` (0–3) per audited surface/domain in summaries and
closeout. Do **not** put the same 0–3 number on individual findings without
labeling it `control_maturity` and repeating this legend.

### Optional dimension scorecard (0–5)

Some campaign kits rate dimensions (completeness, freshness, …) on **0–5**.
If you use that scorecard, also emit `surface_score` via:

| Dimension avg (0–5) | surface_score |
| --- | ---: |
| ≥ 4.5 | 3 |
| ≥ 3.0 | 2 |
| ≥ 1.5 | 1 |
| &lt; 1.5 | 0 |

Or map a single dimension: `surface_score = min(3, floor(dim * 3 / 5))`.
Always state which mapping you used.

### BI check score_1_5 (1–5, higher = better)

Used by BI dashboard acceptance checks (`fragments/bi-check-schema.md`):

| score_1_5 | surface_score (typical) |
| ---: | ---: |
| 5 | 3 |
| 4 | 3 or 2 |
| 3 | 2 |
| 2 | 1 |
| 1 | 0 |

Kit priorities `high|medium|low` map to P0–P3 per bi-check-schema (not 1:1 with
score). A wrong KPI can be score 1 + priority high even if the layout looks fine.

### Priority (lower number = worse)

| Priority | Meaning | Typical criteria |
| --- | --- | --- |
| P0 | blocking | Compromise, data loss, RCE, secret leak, dangerous deploy, critically wrong instruction |
| P1 | high | High defect/incident probability, release integrity break, critical path uncontrolled |
| P2 | medium | Material maintenance cost, instability, architecture/docs drift |
| P3 | low | Local hygiene, convenience, formatting, low-risk optimization |

### Severity mapping (BioETL closeout / issues)

| Priority | BioETL severity |
| --- | --- |
| P0 | Critical |
| P1 | High |
| P2 | Medium |
| P3 | Low |

In JSON findings, prefer field name **`priority`** for P0–P3. If a kit uses
`"severity": "P0"`, treat it as priority and still set BioETL `severity`.
