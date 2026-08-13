______________________________________________________________________

Version: 1.0.0
Status: active
Class: internal (repo-only index; not a paste card)
Owner: BioETL Team
Last verified: '2026-08-13'
Source basis: operator-supplied Grafana audit brief dated 2026-08-13

______________________________________________________________________

# Grafana dashboard audit — five-prompt set

Five complete read-only prompt cards for a source-backed dashboard audit.
Use the master card for an end-to-end pass or a specialist card when the
evidence pack and scope are already fixed.

| Order | Id | Role |
| ---: | --- | --- |
| 1 | `prompt.observability.grafana-audit.master` | inventory, evidence, unified P0–P3 backlog and scorecard |
| 2 | `prompt.observability.grafana-audit.visual` | palette, WCAG contrast, typography and visual encoding |
| 3 | `prompt.observability.grafana-audit.layout` | composition, first viewport, variables and drill-down |
| 4 | `prompt.observability.grafana-audit.data-integrity` | complete lineage, exact queries, invariants and reconciliation |
| 5 | `prompt.observability.grafana-audit.regression` | baseline/candidate retest and release decision |

All cards include `fragments/grafana-audit-contract.md`. The master may route
to cards 2–4, but it remains a complete standalone prompt. Regression runs only
after a candidate change exists.

Default artifacts:

```text
reports/audit/grafana/<run_id>/
  evidence/
  report.md
  findings.json
  scorecard.json
  lineage.json
  regression.json
```

Example:

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ai.prompts render `
  prompt.observability.grafana-audit.master `
  --param SCOPE=grafana/dashboards `
  --param MONITORING=false `
  --param LANGUAGE=ru
```

Write/fix loops remain separate:
`prompt.observability.dashboard-audit-cycle` and
`prompt.observability.dashboard-panel-audit`.
