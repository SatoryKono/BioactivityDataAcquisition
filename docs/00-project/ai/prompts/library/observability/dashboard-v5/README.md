______________________________________________________________________

Version: 1.0.0
Status: active
Class: internal (repo-only index; not a paste card)
Owner: BioETL Team
Last verified: '2026-08-18'

______________________________________________________________________

# Dashboard V5 residual pack

Operator-paste cards for the Manus V4 → V5 Grafana leftover program.
Not runtime SSOT. Precedence: `.codex/skills/observability-dashboard/` →
`AGENTS.md` → these cards.

Do **not** reopen `#8944`–`#8948` or `#8927` / `#8937` without a fresh
reproduction against current `origin/main`.

## Cards

| Id | File | When to paste |
| --- | --- | --- |
| `prompt.observability.dashboard-v5.pack` | [pack.md](pack.md) | Route one residual |
| `prompt.observability.dashboard-v5.implement` | [implement.md](implement.md) | Finish leftover R-D / babysit #8987 |
| `prompt.observability.dashboard-v5.closeout` | [closeout.md](closeout.md) | Close with evidence vs `origin/main` |
| `prompt.observability.dashboard-v5.audit-rf` | [audit-rf.md](audit-rf.md) | R-F visual / light / 200% cycle |

Render a full inlined paste (fragments included):

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ai.prompts render prompt.observability.dashboard-v5.implement `
  --param MODE=implement --param LANGUAGE=ru --param MONITORING=false
```

## Landed vs leftover (pin on `origin/main`)

| Residual | Disposition |
| --- | --- |
| R-A `$pipeline` HTTP filter-options | Landed PR #8979 |
| R-E PromQL `reviewed_expressions` IDs | Landed PR #8979 |
| R-B Run Explorer HTTP catalog | Landed PR #8979 |
| R-C selector→request fixtures | PR #8987 (do not treat unmerged head as `origin/main`) |
| R-D bounded datasource validator | Optional; only if Inspect still shows plugin/request drift |
| R-F light / 200% / leftover NV | New audit cycle; requires `MONITORING=true` |

## Defaults

`MONITORING=false` except `audit-rf` (`true`), `LANGUAGE=ru`, `ALLOW_ISSUE_WRITE=false`,
`ALLOW_PUSH=true` only on `fix/*`, never `main`.
