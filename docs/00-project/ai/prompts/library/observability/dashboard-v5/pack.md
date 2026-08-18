---
id: prompt.observability.dashboard-v5.pack
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, any]
params: [TASK, MODE, LANGUAGE, MONITORING, WORK_BRANCH]
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - .codex/skills/observability-dashboard/SKILL.md
  - docs/03-guides/dashboards/contracts/run-explorer-http-catalog.yaml
  - docs/03-guides/dashboards/contracts/selector-contracts.yaml
  - configs/quality/promql_max_over_time_counter_policy.yaml
anti_patterns:
  - Reopening #8944-#8948
  - Starting docker-compose.monitoring.yml unless MONITORING=true
  - Treating unmerged PR heads as origin/main closeout evidence
  - Adding a scripts/ file that grows active_script_count_max
  - Full json.dumps rewrite of grafana/dashboards/*.json
tags: [observability, dashboard, grafana, v5, pack, operator]
summary: Route V5 Grafana residuals — R-A/R-E/R-B landed; R-C PR; R-D/R-F leftover
max_body_lines: 120
---

# BioETL — Dashboard V5 residual pack

Не runtime SSOT. Язык: `{{LANGUAGE}}`. Литералы не переводить.

## Params

| Param | Default |
| --- | --- |
| `TASK` | выбрать одну карточку ниже и довести до closeout |
| `MODE` | `implement` \| `closeout` \| `audit` |
| `LANGUAGE` | `ru` |
| `MONITORING` | `false` |
| `WORK_BRANCH` | `fix/dash-v5-<slug>` (never main) |

## Куда идти

| Нужно | Карточка |
| --- | --- |
| Добить leftover / babysit CI | `prompt.observability.dashboard-v5.implement` |
| Закрыть issue/PR против `origin/main` | `prompt.observability.dashboard-v5.closeout` |
| Light / 200% / leftover NV (R-F) | `prompt.observability.dashboard-v5.audit-rf` |
| Общий Grafana cycle | `prompt.observability.dashboard-audit-cycle` |
| Sequential folder run | `prompt.observability.sequential-run` |

## Уже влито (не повторять продукт)

- **R-A / R-E / R-B** — PR `#8979`: `$pipeline` = Ops HTTP
  `/ops/control-plane/filter-options`; PromQL ID registry;
  `run-explorer-http-catalog.yaml`.
- **R-C** — PR `#8987`: `tests/fixtures/grafana/run_explorer/` (пока не
  `origin/main` — не закрывать как VERIFIED_ALREADY_RESOLVED).

## Запреты

Не открывать `#8944`–`#8948`. Не стартовать monitoring stack, пока
`MONITORING=false`. Не увеличивать бюджеты техдолга. Не править `.env`.
Не commit в `main`. Чужой dirty WIP — отдельный worktree.

## Done when

- [ ] Выбрана ровно одна карточка и выполнен её DoD
- [ ] Evidence: SHA, пути, команды, PR/issue numbers
