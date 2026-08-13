______________________________________________________________________

Version: 1.0.0
Status: active
Class: internal (repo-only index; not a paste card)
Owner: BioETL Team
Last verified: '2026-08-13'
Source kit: 2026-08-11 07:55 Europe/London

______________________________________________________________________

# Grafana six-prompt audit kit

Read-only audit of shipped BioETL Grafana dashboards: visual language,
panel composition, and data-fill semantics. Not runtime SSOT.

| # | Id | Card | Role |
| --- | --- | --- | --- |
| 0 | `prompt.observability.grafana-six.evidence` | [evidence.md](evidence.md) | Evidence pack |
| 1 | `prompt.observability.grafana-six.visual` | [visual.md](visual.md) | Palette / contrast / type |
| 2 | `prompt.observability.grafana-six.layout` | [layout.md](layout.md) | Composition / IA / sizes |
| 3 | `prompt.observability.grafana-six.data` | [data.md](data.md) | Queries / fill / zero vs empty |
| 4 | `prompt.observability.grafana-six.consolidate` | [consolidate.md](consolidate.md) | Dedupe + prioritize |
| 5 | `prompt.observability.grafana-six.reverify` | [reverify.md](reverify.md) | After-fix independent pass |
| — | `prompt.observability.grafana-six.pack` | [pack.md](pack.md) | Routing card |

Order: **0 once** → **1 ∥ 2 ∥ 3** on the same pack → **4** → (implement) → **5**.
Prompts 1–3 must not substitute for each other.

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ai.prompts render prompt.observability.grafana-six.evidence `
  --param SCOPE=grafana/dashboards --param MONITORING=false --param LANGUAGE=ru
```

Adjacent (write/fix loops, not this kit): `prompt.observability.dashboard-audit-cycle`,
`prompt.audit.cycle.dashboards`, `prompt.audit.cycle.telemetry`.
