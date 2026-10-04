---
id: prompt.fragment.finding-schema
version: 1.3.0
status: active
class: fragment
owner: BioETL Team
summary: Finding schema v1.3 — root-cause identity, freshness, disproof, review traceability
---

## Finding schema

Each finding **must** include:

| Field | Rule |
| --- | --- |
| `id` | Stable short id, e.g. `DOCS-012` |
| `root_cause_id` | Stable causal cluster id shared across prompt domains |
| `requirement_id` | Existing `REQ-*` / `DASH-*`, or `GAP` |
| `path` | Existing file; prefer `path:line` or range |
| `observation` | One factual, falsifiable claim |
| `method` | Command, test, artifact, or inspection method |
| `expected` | Expected state |
| `actual` | Observed state |
| `impact` | User/runtime/security/ops impact |
| `confidence` | `high \| medium \| low`; optional `confidence_score` 0..1 |
| `status` | `PROVEN \| NOT_PROVEN` |
| `review_verdict` | Optional: `CONFIRMED \| DOWNGRADED \| REJECTED \| NOT_VERIFIABLE` |
| `evidence_freshness` | `CURRENT \| STALE \| UNBOUND` |
| `priority` | `P0 \| P1 \| P2 \| P3` |
| `severity` | Critical / High / Medium / Low, mapped from priority |
| `attempted_disproof` | Falsifier/counterexample checked and result |
| `exception_ref` | Valid exception/waiver reference or `null` |
| `remediation` | Smallest safe next step |
| `effort` | `S \| M \| L \| XL` when known |
| `automation` | Prevention CI/hook/test or `n/a` |
| `automated_fix_possible` | boolean; never authorizes applying a fix |

Rules:

- No current file/command/runtime proof -> `NOT_PROVEN`.
- `STALE`/`UNBOUND` evidence may guide investigation but cannot by itself
  prove a current defect.
- P0/P1/P2 `PROVEN` findings require recorded attempted disproof.
- A valid exception must satisfy the evidence-contract exception/suppression
  contract.
- Do not invent stack, SLA, coverage targets, or threat models; mark unknown.
- Prefer current checkout + `origin/main` over memory or stale reports.
- Never put secret values in findings, issues, PR bodies, logs, or artifacts.

## findings.json (machine-readable)

Write UTF-8 JSON array (or `{"findings":[...]}`) under the domain report dir.
Recommended object shape:

```json
{
  "id": "AREA-001",
  "root_cause_id": "rc-8d15f9c9",
  "requirement_id": "REQ-ARCH-001",
  "priority": "P1",
  "severity": "High",
  "confidence": "high",
  "confidence_score": 0.93,
  "status": "PROVEN",
  "review_verdict": null,
  "evidence_freshness": "CURRENT",
  "category": "string",
  "evidence": [
    {
      "path": "path/to/file",
      "line": 42,
      "command": "safe diagnostic command",
      "source_revision": "<sha>",
      "observed_at": "2026-10-04T00:00:00Z",
      "observation": "what was observed"
    }
  ],
  "expected": "desired or documented state",
  "actual": "observed state",
  "impact": "specific impact",
  "root_cause": "minimal causal explanation",
  "attempted_disproof": "compatibility seam checked; claim still reproduces",
  "exception_ref": null,
  "remediation": "smallest safe remediation",
  "effort": "S",
  "dependencies": [],
  "validation": ["exact command or assertion"],
  "automated_fix_possible": false
}
```

Companion human report: `report.md` (executive summary, surface_score, top
gaps). Independent reviewers keep rejected/downgraded hypotheses in a
reconciliation ledger rather than deleting them.
