---
id: prompt.observability.dashboard-v5.closeout
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, any]
params: [TASK, MODE, SCOPE, LANGUAGE, ALLOW_CLOSE, ALLOW_MERGE]
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
related_ssot:
  - AGENTS.md
  - docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
  - docs/00-project/ai/prompts/library/closeout/grok-closeout.md
  - .codex/skills/observability-dashboard/SKILL.md
  - docs/03-guides/dashboards/contracts/run-explorer-http-catalog.yaml
  - configs/quality/promql_max_over_time_counter_policy.yaml
anti_patterns:
  - Closing against an unmerged PR head as if it were origin/main
  - Reopening #8944-#8948 to "finish" V5
  - VERIFIED_ALREADY_RESOLVED without a live SHA pin
  - Treating LFS-budget red jobs as product regressions
tags: [observability, dashboard, grafana, v5, closeout, operator]
summary: Close V5 residual issues/PRs with origin/main evidence only
max_body_lines: 160
---

# BioETL — V5 closeout

Закрой leftover **только** против `origin/main`. Язык: `{{LANGUAGE}}`.
Канонический closeout-каркас: `prompt.closeout.grok`.

## Params

| Param | Default |
| --- | --- |
| `TASK` | close `#8987` and/or confirm `#8979` on `origin/main` |
| `MODE` | `closeout` |
| `SCOPE` | PRs `#8979` `#8987`; residuals R-A…R-F |
| `LANGUAGE` | `ru` |
| `ALLOW_CLOSE` | `false` until evidence is on `origin/main` |
| `ALLOW_MERGE` | `false` |

## Проверка на `origin/main`

| Claim | Как доказать |
| --- | --- |
| R-A | seven `grafana/dashboards/bioetl-*.json`: `$pipeline` datasource `BioETL Ops HTTP`, URL `filter-options?dimension=pipeline` |
| R-E | `reviewed_expression_count == len(reviewed_expressions)` |
| R-B | catalog YAML exists; `test_run_explorer_http_catalog.py` green |
| R-C | fixtures under `tests/fixtures/grafana/run_explorer/` **on main** |
| R-D / R-F | leftover, не close как resolved |

Не открывать `#8944`–`#8948`. Skill: `bioetl-closeout`.

## Вердикты

`FIXED` / `VERIFIED_ALREADY_RESOLVED` / `WONT_FIX` / `BLOCKED`.
`BLOCKED` допустим для LFS budget и для R-F без `MONITORING=true`.

## Done when

- [ ] Каждый claim с SHA `origin/main` + команда/тест
- [ ] Unmerged `#8987` не закрыт как landed
- [ ] Комментарий в issue/PR без секретов
