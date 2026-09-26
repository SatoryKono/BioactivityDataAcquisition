---
id: prompt.fragment.finding-schema
version: 1.2.0
status: active
class: fragment
owner: BioETL Team
summary: Finding fields + findings.json contract including requirement_id (REQ-*/DASH-*)
---

## Finding schema

Each finding **must** include:

| Field | Rule |
| --- | --- |
| `id` | Stable short id (e.g. `DOCS-012`) |
| `requirement_id` | Existing `REQ-*` from REQUIREMENTS.md / traceability CSV, or `DASH-*` for presentation, or `GAP` |
| `path` | Existing file; prefer `path:line` or line range |
| `observation` | One factual claim |
| `method` | Command, test, or inspection method |
| `expected` | Expected state |
| `actual` | Observed state |
| `impact` | User/runtime/security/ops impact |
| `confidence` | Band `high` \| `medium` \| `low`; optional float `confidence_score` in 0..1 |
| `status` | `PROVEN` \| `NOT_PROVEN` |
| `priority` | `P0` \| `P1` \| `P2` \| `P3` |
| `severity` | Critical / High / Medium / Low (map from priority) |
| `remediation` | Concrete next step |
| `effort` | `S` \| `M` \| `L` \| `XL` when known |
| `automation` | Prevention (CI/hook/test) or `n/a` |
| `automated_fix_possible` | boolean; does **not** authorize applying a fix |

Rules:

- No file-level proof → `NOT_PROVEN` (do not open a GitHub issue).
- Do not invent stack, SLA, coverage targets, or threat models; mark unknown.
- Prefer current checkout + `origin/main` over memory or stale reports.
- Never put secret values in findings, issues, PR bodies, or logs.

## findings.json (machine-readable)

Write UTF-8 JSON array (or `{"findings":[...]}`) under the domain report dir.
Recommended object shape:

```json
{
  "id": "AREA-001",
  "requirement_id": "REQ-ARCH-001",
  "priority": "P1",
  "severity": "High",
  "confidence": "high",
  "confidence_score": 0.9,
  "status": "PROVEN",
  "category": "string",
  "evidence": [
    {
      "path": "path/to/file",
      "line": 42,
      "command": "safe diagnostic command",
      "observation": "what was observed"
    }
  ],
  "expected": "desired or documented state",
  "actual": "observed state",
  "impact": "specific impact",
  "root_cause": "known root cause or unspecified",
  "remediation": "smallest safe remediation",
  "effort": "S",
  "dependencies": [],
  "validation": ["exact command or assertion"],
  "automated_fix_possible": false
}
```

Companion human report: `report.md` (executive summary, surface_score, top gaps).
