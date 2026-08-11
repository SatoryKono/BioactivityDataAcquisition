---
id: prompt.fragment.bi-check-schema
version: 1.0.0
status: active
class: fragment
owner: BioETL Team
summary: BI dashboard check result schema and priority mapping
---

## BI check schema

Use for acceptance checks (visual / layout / data). Separate from engineering
panel defect classes in `prompt.observability.dashboard-panel-audit`.

### Epistemic labels

- **FACT** — directly observed or measured
- **INFERENCE** — conclusion from facts
- **ASSUMPTION** — gap filled without evidence (must not become FAIL alone)

### Check object (`checks.json`)

```json
{
  "check_id": "BI-V-Q-01",
  "block": "visual|layout|data",
  "depth": "quick|detailed|auto",
  "status": "pass|warn|fail|na",
  "score_1_5": 3,
  "priority": "high|medium|low",
  "bioetl_priority": "P0|P1|P2|P3",
  "fact": "observable statement",
  "evidence": ["path or measurement"],
  "measured_value": "e.g. 2.85:1",
  "threshold_or_rule": "e.g. WCAG AA 4.5:1",
  "affected_users": ["analyst", "manager", "executive"],
  "impact": "decision or accessibility risk",
  "recommendation": "smallest safe fix",
  "confidence": 0.9,
  "epistemic": "FACT"
}
```

### ID convention (unified)

| Contour | Quick | Detailed | Auto |
| --- | --- | --- | --- |
| Visual | `BI-V-Q-##` | `BI-V-D-##` | `BI-V-A-##` |
| Layout | `BI-L-Q-##` | `BI-L-D-##` | `BI-L-A-##` |
| Data | `BI-D-Q-##` | `BI-D-D-##` | `BI-D-A-##` |

Legacy kit IDs (`VQ-01`, `V-01`, …) map into this namespace when normalizing.

### Priority map → BioETL

| Kit priority | Typical BioETL | When |
| --- | --- | --- |
| high | P0–P1 | KPI wrong, period/filter, freshness, units, RLS, key a11y content |
| medium | P2 | layout overload, hierarchy, non-key consistency |
| low | P3 | decorative chrome, minor style |

### score_1_5 → surface_score

| score_1_5 | Meaning | surface_score |
| ---: | --- | ---: |
| 5 | clean pass | 3 |
| 4 | minor, no wrong decision risk | 3 or 2 |
| 3 | noticeable UX hit, main task OK | 2 |
| 2 | material misread risk | 1 |
| 1 | critical decision risk / unusable | 0 |

### Hard rules

1. Do **not** mark a KPI/value **fail** from screenshot alone — need SQL/API/
   datasource query / semantic-layer evidence (or `na` / low confidence).
2. Aesthetic preference without readability, task, standard, or error risk →
   not a defect.
3. Without browser/UI: contrast/zoom/DOM checks → `na` or `Not Verifiable`,
   not fail.
4. Never put secrets or raw credentials in evidence/screenshots/reports.
