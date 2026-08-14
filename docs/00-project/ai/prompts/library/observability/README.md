______________________________________________________________________

Version: 1.2.0
Status: active
Class: internal (repo-only index; not a paste card)
Owner: BioETL Team
Last verified: '2026-08-14'

______________________________________________________________________

# Observability prompt folder

Operator-paste cards for BioETL Grafana / dashboard audits.
Not runtime SSOT. Precedence: `.codex/skills/observability-dashboard/` →
`AGENTS.md` → this folder.

Default for any card here: `MONITORING=false`, `LANGUAGE=ru`,
`ALLOW_ISSUE_WRITE=false`. Start `docker-compose.monitoring.yml` only when
the operator sets `MONITORING=true` and a live render is required.

## Sequential run (this folder)

Operator-paste orchestrator: `prompt.observability.sequential-run` (v1.1).
Run **once per checkout SHA**. Reuse one evidence pack. Do not invent
panels, UIDs, metrics, or live values. Dedupe against **closed** issues and
open fix PRs; do not open a third PR for the same root cause.

| Step | Card | Role | Skip when |
| ---: | --- | --- | --- |
| 0 | Shared inventory | `grafana/dashboards/*.json` + contracts | — |
| 1 | `prompt.observability.grafana-audit.master` | Evidence + unified backlog | — |
| 2 | `prompt.observability.grafana-audit.visual` | Palette / contrast / type | — |
| 3 | `prompt.observability.grafana-audit.layout` | Composition / IA / first screen | — |
| 4 | `prompt.observability.grafana-audit.data-integrity` | Lineage / queries / zero vs empty | live query optional |
| 5 | `prompt.observability.bi-dashboard-acceptance` | Visual / layout / data acceptance | — |
| 6 | `prompt.observability.dashboard-panel-audit` | 5 named phases, `CYCLE_COUNT=1` | — |
| 7 | `prompt.observability.dashboard-audit-cycle` | `N=1`, contours `density,fill,pipeline` | write loops not authorized |
| 8 | `prompt.observability.grafana-audit.regression` | Baseline vs candidate | **no candidate change** |
| 9 | Final issue sweep | Close/BLOCKED vs `origin/main` | — |

`grafana-six/*` is **deprecated**. If an operator still pastes those cards,
map them and do **not** double-count findings:

| Deprecated | Successor |
| --- | --- |
| `grafana-six.evidence` | grafana-audit.master (evidence section) |
| `grafana-six.visual` | grafana-audit.visual |
| `grafana-six.layout` | grafana-audit.layout |
| `grafana-six.data` | grafana-audit.data-integrity |
| `grafana-six.consolidate` | grafana-audit.master backlog |
| `grafana-six.reverify` | grafana-audit.regression |
| `grafana-six.pack` | this README + grafana-audit.master |

## Artifacts

```text
reports/audit/observability-seq/<utc>-obs-seq-<shortsha>/
  00-inventory.md
  01-grafana-audit-master.md
  …
  findings.json
  report.md
```

Per-card mirrors may also land under `reports/audit/grafana/` or
`reports/audit/grafana-panels/` when a card names that path.

## Guardrails

- Shipped JSON is structure SSOT. Screenshots do not prove data correctness.
- Distinguish: correct zero · expected empty · selector error · query error ·
  backend error · stale telemetry.
- Mark `FACT` / `INFERENCE` / `GAP` / `CONTRADICTION`.
- Live UI without `MONITORING=true` → `Not Verifiable`, not a dashboard defect.
- Do not raise debt budgets. Do not edit `.env`. Do not commit to `main`.
