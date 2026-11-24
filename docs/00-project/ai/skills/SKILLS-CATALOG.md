______________________________________________________________________

Version: 1.2.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-11-18'

______________________________________________________________________

# Каталог локальных skills

Рабочий реестр совпадает с `.codex/skills/`. Канонический runtime-каталог:
[SKILLS-CATALOG.md](../../../../.codex/skills/SKILLS-CATALOG.md).

Опубликованные копии в `local/` с пометкой `Canonical runtime source: none`
не являются runtime skills. Это overlay из `_references/local/`.

## Live skills

| Skill | Когда вызывать | Куда не сворачивать |
| --- | --- | --- |
| `agent-debugging` | Сбой траектории AI-агента | `py-debug-bot` |
| `grilling` | Обязательное уточнение нового запроса перед реализацией | `py-plan-bot` |
| `new-pipeline` | Новый provider/entity pipeline | `py-config-bot` |
| `observability-dashboard` | Grafana dashboard и панели | `observability-prometheus` |
| `observability-prometheus` | Prometheus alert и recording rules | `observability-dashboard` |
| `py-audit-bot` | Аудит без внесения исправления | `py-plan-bot` |
| `py-config-bot` | YAML, схемы, контракты pipeline | `new-pipeline` |
| `py-debug-bot` | Причина падения теста, CI или runtime | `agent-debugging` |
| `py-doc-bot` | Документация и зеркала runtime | `py-debug-bot` |
| `py-plan-bot` | План до правок | `py-audit-bot` |
| `py-test-bot` | Тесты, flakes, coverage | `py-debug-bot` |
| `research-workflow` | Evidence, decisions, specs | `py-plan-bot` |
| `technical-designer-mermaid` | Диаграммы Mermaid | `py-doc-bot` |
| `vcr-record` | HTTP-кассеты VCR | `py-test-bot` |
| `verify-architecture` | Проверки слоёв и импортов | `py-audit-bot` |

## Retired names

Имя ниже не выбирается как skill. Маршрут — текущая колонка.

| Бывшее имя | Текущий маршрут |
| --- | --- |
| `architecture-guardian` | `verify-architecture` |
| `capability-discovery` | этот каталог и runtime tools |
| `collecting-evidence` | `research-workflow` phase `evidence` |
| `create-pr` | политика PR репозитория, не skill |
| `deep-research` | `research-workflow` |
| `documentation-audit` | `py-doc-bot` |
| `documentation-cascade-audit` | `py-doc-bot` mode `broad` |
| `generating-constrained-specs` | `research-workflow` phase `specs` |
| `grafana-dashboard-extension` | `observability-dashboard` |
| `grafana-dashboard-render` | `observability-dashboard` |
| `hierarchical-evidence-orchestration` | `research-workflow` |
| `initializing-ledger` | `research-workflow` phase `initialize` |
| `making-decisions` | `research-workflow` phase `decisions` |
| `nci-analysis` | вне дерева `.codex/skills` |
| `prometheus-alert-rule-editor` | `observability-prometheus` |
| `prometheus-metric-discovery` | `observability-prometheus` |
| `prometheus-query-debugger` | `observability-prometheus` |
| `prometheus-rule-testing` | `observability-prometheus` |
| `py-architecture-debt-bot` | `py-audit-bot` mode `debt` |
| `py-code-bot` | прямой implementation по orchestration, не skill |
| `py-reproducibility-audit` | `py-audit-bot` mode `reproducibility` |
| `py-review-orchestrator` | `py-audit-bot` mode `review` |
| `py-test-swarm` | `py-test-bot` broad campaign |
| `synthesizing-pillars` | `research-workflow` phase `synthesis` |
| `using-git-worktrees` | `scripts/engineering/repo/create_worktree.py` |
| `verify-unit-tests` | `py-test-bot` |

## Published overlays

Эти каталоги лежат в `local/`, потому что их копирует reference overlay.
В `.codex/skills/` их нет: `gh-address-comments`, `gh-fix-ci`, `openai-docs`,
`public/architecture-guardian`.
