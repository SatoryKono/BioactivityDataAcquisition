---
id: prompt.observability.grafana-audit.layout
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params:
  - SCOPE
  - DASHBOARD_PURPOSE
  - USER_ROLES
  - USER_JOURNEYS
  - SERVICE_MAP
  - VIEWPORT
  - OUTPUT_DIR
  - LANGUAGE
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
  - fragments/grafana-audit-contract.md
related_ssot:
  - AGENTS.md
  - grafana/dashboards
  - docs/03-guides/dashboards/design-system.md
  - docs/03-guides/dashboards/verdict-ontology.md
  - .codex/skills/observability-dashboard/SKILL.md
anti_patterns:
  - Reordering panels without mapping them to user questions
  - Proposing query or metric changes in a layout-only audit
  - Treating whitespace or density as taste without task impact
  - Inventing missing panels instead of reporting MISSING capability
tags: [observability, grafana, dashboard, audit, layout, navigation, ia, operator]
summary: Grafana layout audit — composition, hierarchy, variables, drill-down
max_body_lines: 220
---

# Prompt — расположение, композиция и навигация

## Параметры

| Param | Default |
| --- | --- |
| `SCOPE` | `grafana/dashboards` |
| `DASHBOARD_PURPOSE` | `derive-and-mark-gaps` |
| `USER_ROLES` | `SRE,BI,NOC` |
| `USER_JOURNEYS` | `derive-from-contracts` |
| `SERVICE_MAP` | `repo-map-or-gap` |
| `VIEWPORT` | `1366x768` |
| `OUTPUT_DIR` | `reports/audit/grafana/<run_id>/layout` |
| `LANGUAGE` | `ru` |

## Полный текст промта

Ты — information architect и operator-journey reviewer для Grafana.
Проведи read-only layout/composition/navigation audit scope `{{SCOPE}}` на
языке `{{LANGUAGE}}`.

Используй shipped JSON и full-dashboard renders. Учитывай заявленное назначение
`{{DASHBOARD_PURPOSE}}`, roles `{{USER_ROLES}}`, journeys
`{{USER_JOURNEYS}}`, service/data-flow map `{{SERVICE_MAP}}` и first viewport
`{{VIEWPORT}}`. Результаты сохраняй в `{{OUTPUT_DIR}}`.

Не проверяй correctness чисел и не меняй queries. Визуальный contrast относится
к visual prompt. Здесь оценивай, помогает ли структура быстро перейти от
состояния системы к причине и следующему действию.

### 1. Определи page goal и вопросы

Для каждого dashboard:

1. Сформулируй page goal одним предложением.
2. Сформулируй 3–7 обязательных user questions.
3. Укажи primary role и secondary roles.
4. Для каждого вопроса укажи ожидаемое время ответа и нужную evidence scope:
   current, selected range, selected run или forensic detail.

Если purpose/journey отсутствуют в контрактах, выведи `INFERENCE` и GAP, а не
создавай продуктовую цель как факт.

### 2. Построй question-to-panel map

Для каждой panel/row/tab укажи:

- `question_answered` или `ORPHAN`;
- evidence scope;
- importance: critical/supporting/detail;
- first viewport: fully visible/partial/below fold;
- входящий и исходящий drill-down;
- дублирует ли она уже существующую analytic function.

Для обязательного вопроса без panel/link укажи `MISSING`. Не предлагай название
несуществующей метрики: опиши недостающую decision capability.

### 3. Проверь first viewport

Проверь, что верхняя часть отвечает в логическом порядке:

1. Есть ли проблема сейчас?
2. Где проблема или какой домен затронут?
3. Каково первое безопасное действие?

Критический verdict не должен зависеть только от hover, collapsed row или
scroll. Current status не должен конкурировать одинаковым visual weight с
selected-range counter, collection-state chip или forensic ID.

Зафиксируй fold line в pixels/grid rows и перечисли факты выше fold. Оцени
time-to-first-insight с целевым диапазоном 5–10 секунд только как task metric,
а не как субъективное впечатление.

### 4. Проверь порядок и grouping

Проверь последовательность:

`overview/current verdict → symptom/driver → service/component decomposition →
detail/forensics → runbook or adjacent dashboard`.

Сопоставь её с `{{SERVICE_MAP}}`. Проверь:

- related metrics физически сгруппированы;
- current/range/run scopes явно разделены;
- сравниваемые panels используют сопоставимые units/scales/window;
- одинаковый размер действительно означает одинаковую важность;
- крупные panels оправданы data density или task importance;
- sparse tall rows, cramped rows и competing equal-weight cards;
- redundant panels и одна metric в разных visualizations без новой функции;
- rows/tabs уменьшают load, а не скрывают обязательный signal;
- detail panels отвечают «почему», а не повторяют summary.

### 5. Проверь geometry

Для Classic JSON восстанови top-level rectangles из `gridPos.x/y/w/h` на
24-column grid. Найди:

- overlap;
- unexplained vertical gaps;
- inconsistent widths/alignment;
- panel height, не соответствующий content volume;
- internal scroll, clipping и hidden actions;
- repeated panels, выходящие за ожидаемый band;
- row expansion collision;
- first-screen content, вытесненный chrome/variables.

Покажи evidence как panel IDs + rectangles + screenshot/render. JSON geometry
без фактического clipping не доказывает render defect, но может доказать overlap.

### 6. Проверь variables и context

Проверь:

- variables расположены по dependency и частоте изменения;
- parent variable предшествует dependent variable;
- single/multi/All/empty states понятны;
- default values не создают ложный healthy/empty state;
- title/description отражают active scope;
- dashboard/panel/data links сохраняют применимые time range и variables;
- unsupported variables не протекают в target dashboard;
- есть back-navigation и путь к runbook/Explore/detail;
- median/maximum diagnostic click depth приемлемы для critical journey.

Не считай прямой link полезным, пока не проверены target UID/URL и сохранение
контекста.

### 7. Предложи минимальный re-layout

Не меняя queries и data semantics, предложи целевую схему:

- row/band order;
- panel ID → target `x/y/w/h` или relative position;
- panels to group/collapse/resize;
- duplicate/orphan handling;
- variables order;
- links/back-navigation.

Каждый move должен ссылаться на user question и ожидаемый эффект. Если
MISSING capability требует новой query/metric, вынеси её в отдельный
cross-contour dependency без проектирования данных.

Проверь, что proposed rectangles не перекрываются и не создают gaps.

### 8. Findings и метрики

Верни таблицы:

1. `user question → panel/link → coverage → evidence`;
2. `panel → question_answered/ORPHAN → scope → fold status`;
3. `layout finding → impact → severity → fix → acceptance`;
4. `current layout → proposed layout → migration step`.

Посчитай:

- Task Coverage;
- Critical Signal First-Viewport Coverage;
- Orphan Panel Count;
- Duplicate Analytic Function Count;
- Drill-down Coverage;
- Median/Maximum Diagnostic Click Depth;
- top-level Overlap/Gap Count.

Создай `layout-report.md`, `question-panel-map.csv`, `layout-findings.json` и
`proposed-layout.json` в `{{OUTPUT_DIR}}`.

### Acceptance

`PASS` только если все critical questions покрыты, first viewport содержит
current verdict и first action, top-level overlap равен нулю, critical
drill-down сохраняет context, а key insight не доступен только через hover.
Иначе `PASS_WITH_RESIDUALS`, `FAIL` или `BLOCKED` с точным blocker.

### Definition of done

- каждая существующая panel имеет question classification;
- каждый обязательный вопрос имеет coverage verdict;
- re-layout не меняет queries;
- geometry проверена на 24-column grid и render evidence;
- recommendations имеют измеримые acceptance tests.
