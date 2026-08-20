---
id: prompt.observability.dashboard-v5.implement
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, any]
params:
  - TASK
  - MODE
  - SCOPE
  - WORK_BRANCH
  - LANGUAGE
  - MONITORING
  - ALLOW_PUSH
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
  - fragments/reports-output.md
  - fragments/shell-portability.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
  - .codex/skills/observability-dashboard/SKILL.md
  - docs/03-guides/dashboards/contracts/run-explorer-http-catalog.yaml
  - docs/03-guides/dashboards/contracts/selector-contracts.yaml
  - configs/quality/promql_max_over_time_counter_policy.yaml
  - grafana/dashboards
anti_patterns:
  - Reopening #8944-#8948
  - Rewriting whole dashboard JSON with json.dumps
  - New scripts/ file that grows active_script_count_max
  - Raising reviewed_expression_count without a new ID row
  - Starting monitoring unless MONITORING=true
  - Implementing R-F as a selector refactor
tags: [observability, dashboard, grafana, v5, implement, operator]
summary: Implement leftover V5 residuals — babysit #8987, optional R-D validator
max_body_lines: 200
---

# BioETL — V5 implement leftover

Доведи **один** leftover. Не runtime SSOT. Язык: `{{LANGUAGE}}`.

## Params

| Param | Default |
| --- | --- |
| `TASK` | babysit `#8987` **or** R-D validator **or** stop |
| `MODE` | `implement` |
| `SCOPE` | `grafana/dashboards` + catalog/fixtures/tests named below |
| `WORK_BRANCH` | `fix/dash-v5-<slug>` (never main) |
| `LANGUAGE` | `ru` |
| `MONITORING` | `false` |
| `ALLOW_PUSH` | `true` (only `fix/*`) |

Windows: `.\.venv-win\Scripts\python.exe`. Чужой dirty WIP — worktree.

## Уже сделано (не переписывать)

| Residual | Evidence |
| --- | --- |
| R-A `$pipeline` HTTP options | PR `#8979`; seven boards; default `unknown` (Overview `All`) |
| R-E PromQL expression IDs | `promql_max_over_time_counter_policy.yaml` `reviewed_expressions` |
| R-B HTTP catalog | `docs/03-guides/dashboards/contracts/run-explorer-http-catalog.yaml` |
| R-C request fixtures | PR `#8987`; generator `tests/integration/_run_explorer_request_fixtures.py` |

## Очередь

1. **Babysit `#8987`** — CI, rebase на `origin/main`, не force-push.
2. **R-D** — только если Inspect 3010/9402/3023 всё ещё показывает
   plugin/request drift после R-A/R-B/R-C. Bounded validator, без
   infrastructure import из interfaces. LOC/CC не расти.
3. **R-F** — не здесь; карточка `prompt.observability.dashboard-v5.audit-rf`.

## Как менять JSON

Хирургически (один variable / один URL). Полный `json.dumps` ломает
порядок панелей и Y first-screen. Каталог и фикстуры — SSOT URL;
дашборд остаётся hand-edited для layout.

Новый generator — под `tests/`, не `scripts/` (`active_script_count_max`
no-growth).

## Тесты (минимум)

- `tests/integration/test_run_explorer_http_catalog.py`
- `tests/integration/test_run_explorer_request_fixtures.py` (если есть в дереве)
- `tests/integration/test_grafana_selector_contract.py`
- `tests/integration/test_dashboard_operator_readability.py`
- first-screen: `noValue` 3010/9402 без `$`

После правок `tests/**` — обновить
`configs/quality/test_telemetry_baseline.yaml` `source_tree_sha256`.

## Done when

- [ ] Один leftover закрыт evidence (PR SHA, команды, тесты)
- [ ] `#8944`–`#8948` не открыты
- [ ] Post-change reported; LFS-budget CI не маскировать как product fail
