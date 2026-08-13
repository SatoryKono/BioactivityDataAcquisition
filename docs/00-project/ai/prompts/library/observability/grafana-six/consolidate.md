---
id: prompt.observability.grafana-six.consolidate
version: 1.0.1
status: deprecated
class: operator-paste
owner: BioETL Team
successor: prompt.observability.grafana-audit.master
runtimes: [grok, codex, any]
params:
  - SCOPE
  - BRANCH
  - COMMIT_SHA
  - LANGUAGE
  - OUTPUT_DIR
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
  - fragments/audit-scale.md
  - fragments/finding-schema.md
  - fragments/bi-check-schema.md
  - fragments/unknown-params.md
  - fragments/reports-output.md
  - fragments/shell-portability.md
  - fragments/grafana-six-contract.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - grafana/dashboards
  - grafana/README.md
  - grafana/provisioning
  - docs/03-guides/dashboards/design-system.md
  - docs/03-guides/dashboards/dashboard-inventory.md
  - docs/03-guides/dashboards/dashboard-v2-usage.md
  - docs/03-guides/dashboards/contracts/dashboard-inventory.yaml
  - docs/03-guides/dashboards/contracts/selector-contracts.yaml
  - .codex/skills/observability-dashboard/SKILL.md
anti_patterns:
  - Inventing metric names, UIDs, or panel IDs
  - Treating No data as a defect without scope proof
  - Starting docker-compose.monitoring.yml unless MONITORING=true
  - Mixing render-environment blockers with dashboard defects
  - Opening GitHub issues from a read-only evidence pass
  - Substituting visual findings for data semantics or vice versa
tags: [observability, grafana, audit, consolidate, read-only, operator]
summary: Consolidate Grafana visual/layout/data audits — dedupe and prioritize
max_body_lines: 450
---

Промт 4. Консолидация трех аудитов

Назначение

Объединяет результаты визуального, композиционного и data-semantic аудитов. Удаляет дубли и превращает набор наблюдений в подтвержденный, приоритизированный реестр. Иначе один дефект UNKNOWN легко превращается в три «независимые» проблемы, что выглядит внушительно и бесполезно.

НАЧАЛО ПРОМТА

Ты - Principal Dashboard Audit Lead, Evidence Synthesizer и BioETL Architecture Reviewer.

Входы

Используй:

evidence pack из промта 0;

отчет visual/typography audit из промта 1;

отчет layout/panel composition audit из промта 2;

отчет panel data correctness audit из промта 3.

Задача

Сформируй единый подтвержденный реестр проблем. Не проводи новый широкий аудит, кроме точечных проверок для разрешения противоречий.

Этап 1. Нормализуй findings

Для каждого finding извлеки:

source audit;

dashboard UID;

panel ID или row;

observed behavior;

expected contract;

evidence IDs;

severity;

confidence;

root cause;

recommendation;

acceptance criterion.

Приведи термины к общей таксономии:

VISUAL_SEMANTICS;

TYPOGRAPHY;

LAYOUT;

INFORMATION_ARCHITECTURE;

NAVIGATION;

QUERY;

VARIABLE_SCOPE;

TRANSFORMATION;

DATASOURCE;

RUNTIME_EMISSION;

OBSERVABILITY_CONTRACT;

DOCUMENTATION_DRIFT;

ENVIRONMENT_BLOCKER.

Этап 2. Удали дубли

Считай findings дублями, если совпадают:

root cause;

affected panel(s);

observed behavior;

remediation boundary.

Не объединяй findings только потому, что у них одинаковый симптом. Например, No data может быть вызван query defect, invalid selector или backend failure.

Для объединенного finding сохрани ссылки на все source audits и evidence.

Этап 3. Разреши противоречия

Если отчеты расходятся:

Приоритет имеет live data evidence для data semantics.

Актуальный render имеет приоритет для visual facts.

Dashboard JSON имеет приоритет для структуры/configuration.

Нормативный YAML contract имеет приоритет для заявленного policy.

Documentation mirror используется для выявления drift, а не для отмены факта из JSON.

Если противоречие нельзя разрешить, не выбирай удобную версию. Создай GAP с конкретной требуемой проверкой.

Этап 4. Пересчитай серьезность

Учитывай:

вероятность неверного operator decision;

положение above/below fold;

охват dashboards/panels;

частоту сценария;

обнаруживаемость ошибки;

наличие безопасного workaround;

обратимость действия;

confidence evidence.

Не повышай severity из-за количества повторений одного finding в разных отчетах.

Этап 5. Определи root cause и change boundary

Для каждой проблемы укажи наиболее вероятный владелец исправления:

dashboard JSON;

dashboard contract YAML;

Prometheus recording rule;

Grafana provisioning;

HTTP datasource/backend;

observability metric definition/emitter;

application orchestration;

documentation;

test/QA tooling.

Проверь, что предлагаемая граница не нарушает BioETL layer direction. Dashboard remediation не должна тащить business logic в infrastructure или domain I/O.

Этап 6. Сформируй приоритетный backlog

Назначь IDs DASH-AUD-001, DASH-AUD-002, ...

Для каждого элемента укажи:

title;

severity;

affected dashboards/panels;

problem statement;

operator impact;

evidence;

root cause;

minimal remediation;

files likely affected;

dependencies;

acceptance criteria;

verification commands;

risk of regression;

confidence.

Не создавай GitHub Issues. Подготовь issue-ready descriptions только как отдельный раздел, если это явно включено во входные требования.

Этап 7. Сформируй план волн

Минимальные waves:

Wave 0: P0/P1 misleading data и false operational verdicts.

Wave 1: first-screen layout, status semantics, zero/no-data/error distinction.

Wave 2: typography, density, duplicate panels, navigation friction.

Wave 3: documentation drift, test gaps, preventive automation.

Для каждой wave укажи последовательность и проверки. Изменения одного dashboard JSON можно выполнять отдельно, но shared contracts и tests должны обновляться согласованно.

Формат результата

Executive Summary.

Audit Coverage and Limitations.

Dashboard Heatmap:

Dashboard

Visual

Layout

Data correctness

Highest severity

Confirmed findings

Cross-dashboard Root Causes.

Confirmed Registry:

ID

Category

Dashboard/panel

Problem

Evidence

Severity

Confidence

Root cause

Minimal remediation

Rejected or Unconfirmed Findings.

Prioritized Remediation Waves.

Regression Test Matrix.

Open Evidence Gaps.

Критерии качества

В реестре нет дублей.

Каждая проблема подтверждена evidence.

Severity отражает operator risk, а не эстетические предпочтения.

Root cause не подменяется симптомом.

Для каждого P0-P2 есть измеримый acceptance criterion.

Рекомендации сохраняют low-cardinality observability policy и архитектурные границы BioETL.

КОНЕЦ ПРОМТА

## Project overlay

- Artifacts: `reports/audit/grafana-six/<run_id>/` (or `OUTPUT_DIR` if set).
- Do not write repo-root `_audit*` or scratch files.
- Windows: use project venv Python (`.venv-win/Scripts/python.exe`).
- `MONITORING=false` by default (ADR-010). Live Grafana/Prometheus may be
  `BLOCKED` / `ENVIRONMENT` — do not invent live values.
- Missing docs listed in the source kit are `GAP`, not invented SSOT.
- Pack: `prompt.observability.grafana-six.pack`
