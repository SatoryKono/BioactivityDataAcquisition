---
id: prompt.observability.grafana-six.pack
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [any]
params: [SCOPE, BRANCH, COMMIT_SHA, LANGUAGE, MONITORING, OUTPUT_DIR]
includes:
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/git-safety.md
  - fragments/grafana-six-contract.md
related_ssot:
  - docs/00-project/ai/prompts/library/observability/grafana-six/README.md
  - grafana/dashboards
  - docs/03-guides/dashboards/design-system.md
  - .codex/skills/observability-dashboard/SKILL.md
anti_patterns:
  - Running 1-3 before a shared evidence pack
  - Letting one contour invent findings for another
  - Starting monitoring unless MONITORING=true
tags: [observability, grafana, audit, pack, read-only, operator]
summary: Pack routing for the six-prompt read-only Grafana dashboard audit
max_body_lines: 80
---

# Grafana six-prompt audit pack

Read-only. Shared contract: `fragments/grafana-six-contract.md`.
Default `MONITORING=false`. Artifacts: `reports/audit/grafana-six/<run_id>/`.

| # | Card | When |
| --- | --- | --- |
| 0 | `prompt.observability.grafana-six.evidence` | first; freeze SHA, scopes, renders |
| 1 | `prompt.observability.grafana-six.visual` | after 0; palette / type / contrast |
| 2 | `prompt.observability.grafana-six.layout` | after 0; IA / sizes / navigation |
| 3 | `prompt.observability.grafana-six.data` | after 0; queries / zero vs no-data |
| 4 | `prompt.observability.grafana-six.consolidate` | after 1+2+3 |
| 5 | `prompt.observability.grafana-six.reverify` | after implementation, independent agent |

1–3 may run in parallel **only** on the same evidence pack from 0.

Do not use this pack to open issues or edit dashboard JSON. For fix loops use
`prompt.observability.dashboard-audit-cycle` / `prompt.audit.cycle.dashboards`.
For metric feed (instrumentation → rules) use `prompt.audit.cycle.telemetry`.
