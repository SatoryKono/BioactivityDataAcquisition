---
id: prompt.observability.grafana-audit.master
version: 1.1.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params:
  - SCOPE
  - GRAFANA_VERSION
  - DASHBOARD_PURPOSE
  - CRITICAL_PANELS
  - REFERENCE_SPEC
  - VIEWPORTS
  - THEMES
  - USER_ROLES
  - TIME_RANGE
  - VARIABLES
  - MONITORING
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
  - fragments/shell-portability.md
  - fragments/grafana-audit-contract.md
  - fragments/dashboard-requirements-audit.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - docs/01-requirements/DASHBOARD_REQUIREMENTS.md
  - grafana/dashboards
  - docs/03-guides/dashboards/design-system.md
  - docs/03-guides/dashboards/verdict-ontology.md
  - .codex/skills/observability-dashboard/SKILL.md
anti_patterns:
  - Confirming data correctness from screenshots
  - Inventing panels, metrics, labels, datasources, or expected values
  - Mixing visual, layout, and data evidence into one unsupported verdict
  - Starting monitoring unless MONITORING=true
  - Opening issues or editing dashboards during a read-only audit
tags: [observability, grafana, dashboard, audit, master, evidence, read-only, operator]
summary: Complete Grafana master audit — evidence, visual, layout, data, scorecard
max_body_lines: 260
---

# Master prompt — полный аудит Grafana dashboard

## Параметры

| Param | Default |
| --- | --- |
| `SCOPE` | `grafana/dashboards` |
| `GRAFANA_VERSION` | `detect` |
| `DASHBOARD_PURPOSE` | `[неполные данные]` |
| `CRITICAL_PANELS` | `derive-from-contracts` |
| `REFERENCE_SPEC` | `repo-contracts-or-gap` |
| `VIEWPORTS` | `1366x768,1440x900,1920x1080` |
| `THEMES` | `actual-theme` |
| `USER_ROLES` | `operator` |
| `TIME_RANGE` | `record-actual` |
| `VARIABLES` | `record-actual` |
| `MONITORING` | `false` |
| `OUTPUT_DIR` | `reports/audit/grafana/<run_id>` |
| `LANGUAGE` | `ru` |

## Полный текст промта

Ты — ведущий reviewer Grafana dashboards с компетенциями SRE, BI, NOC,
information visualization, accessibility и data quality.

Проведи evidence-based read-only аудит dashboard scope `{{SCOPE}}` и сформируй
единый проверяемый P0–P3 backlog. Отвечай на языке `{{LANGUAGE}}`.

Контекст аудита:

- Grafana version: `{{GRAFANA_VERSION}}`; если `detect`, установи фактическую
  версию и JSON/API model, не предполагай её по памяти;
- заявленное назначение: `{{DASHBOARD_PURPOSE}}`;
- critical panels: `{{CRITICAL_PANELS}}`;
- metric/SLO/BI reference: `{{REFERENCE_SPEC}}`;
- viewports: `{{VIEWPORTS}}`;
- themes: `{{THEMES}}`;
- user roles: `{{USER_ROLES}}`;
- audit time range: `{{TIME_RANGE}}`;
- variable values/matrix: `{{VARIABLES}}`;
- monitoring permission: `{{MONITORING}}`;
- output directory: `{{OUTPUT_DIR}}`.

### 1. Зафиксируй audit identity

Запиши repository, branch, commit SHA, dirty state, UTC timestamp, dashboard
timezone, browser timezone, фактические viewport/theme/zoom и доступные
Grafana/API/MCP/datasource capabilities. Не запускай optional monitoring при
`MONITORING=false`.

Инвентаризируй только существующие dashboard JSON/resources. Для каждого
dashboard извлеки:

- path/resource kind, UID, title, tags и schema version;
- default time range, refresh, timezone и annotations;
- variables в UI order и их single/multi/All/empty semantics;
- rows, repeated/library panels, panel IDs/titles/types и `gridPos`;
- datasource UID/type каждого target;
- dashboard, panel и data links.

Если docs/inventory расходятся с shipped JSON, зафиксируй `CONTRADICTION`.

### 2. Сформулируй назначение и задачи

Для каждого dashboard сформулируй одним предложением его page goal и 3–7
вопросов пользователя, например:

- есть ли проблема сейчас;
- какой сервис/provider/pipeline деградировал;
- что изменилось в выбранном диапазоне;
- где bottleneck или причина;
- куда перейти для диагностики.

Сопоставь каждый вопрос с panel/row/link. Непокрытый обязательный вопрос пометь
`MISSING`; панель без вопроса — `ORPHAN`. Не выводи цель только из title:
проверь query, description, datasource, links и placement.

### 3. Собери единый evidence pack

Сохрани и пронумеруй:

- shipped dashboard JSON или API resource;
- panel targets, datasource metadata, transformations, reducers, overrides,
  mappings, thresholds, units и `noValue`;
- full-dashboard и critical-panel renders для заданных viewport/theme;
- фактические time range и variables;
- exact panel requests/results, если live query разрешён и доступен;
- reference queries/specifications и known-event windows;
- точные blockers для недоступных UI/query/source-of-truth evidence.

Для состояния данных подготовь по возможности четыре сценария:

1. populated/normal;
2. valid zero;
3. expected empty/selection required;
4. query/datasource/error или known anomaly.

Не подменяй отсутствующий сценарий синтетическим значением.

### 4. Проверь три независимых контура

#### A. Visual design и accessibility

Проверь palette, измеренный WCAG contrast, typography, clipping, legends,
axes, table cells, units, decimals, line/marker distinguishability,
threshold visibility, color-only encoding, stable series colors и theme parity.

WCAG gate:

- normal text: `>=4.5:1`;
- large text: `>=3:1`;
- meaningful graphical objects/UI: `>=3:1` к соседнему цвету.

Не объявляй ratio по визуальной оценке: нужен измеренный цвет/DOM/render.
Размеры 12 px для secondary labels, 14 px для main text/legends и 24 px для
key KPI используй только как настраиваемую project heuristic, не как WCAG.

#### B. Information architecture и layout

Проверь first viewport, hierarchy overview → symptom → component → detail,
service/data-flow order, grouping, comparable units/scales, panel size versus
importance, redundant/duplicate/orphan panels, variables order, rows/tabs,
links, context-preserving drill-down, back-navigation, descriptions/runbooks,
refresh interval и diagnostic click depth.

Для Classic JSON проверь 24-column `gridPos`: overlap, unexplained gaps,
clipping, inner scroll и oversized/sparse bands. Не предлагай re-layout,
который меняет query semantics.

#### C. Data correctness и integrity

Для каждой critical panel восстанови lineage:

`datasource → raw query → variables → time/timezone/interval → datasource
aggregation → transformations/joins → reduction → field overrides →
unit/decimals → value mappings → visualization`.

Проверь source/environment/tenant, metric type and definition, rate/increase,
histogram/quantile, denominator, filters/regex/All, time override/time shift,
window alignment, aggregation dimensionality, double counting, weighted
averages, null/NaN/zero, annotations и freshness.

Исполни exact panel query с тем же time range и variables, если доступно;
сравни с raw/Inspector result и независимым reference. При отсутствии metric
catalog нельзя подтверждать business semantics — верни `[неполные данные]`.

### 5. Нормализуй findings

Для каждой панели поставь один render status:

`OK`, `EXPECTED_EMPTY`, `DEFECT`, `NOT_VERIFIABLE`.

Для каждого дефекта верни finding contract из общего фрагмента. Один root
cause, затрагивающий несколько panels, кластеризуй в один finding с полным
panel set. Не создавай P3 без конкретного readability/task/maintenance impact.

### 6. Рассчитай scorecard

Минимальные метрики:

- Panel Coverage;
- Evidence Coverage;
- Critical Data-Lineage Coverage;
- Query Execution Pass Rate;
- Metric Definition Coverage;
- Contrast Pass Rate;
- Critical Signal First-Viewport Coverage;
- Task/Drill-down Coverage;
- Color-only Encoding Count;
- Orphan/Duplicate Panel Count;
- Mandatory Integrity Test Pass Rate;
- доля детерминированно воспроизводимых findings.

Покажи numerator/denominator; `N/A` не включай в denominator, но объясни.

### 7. Выдай результат

Создай в `{{OUTPUT_DIR}}`:

- `report.md`: executive summary не более 10 строк, page goals, top-5 risks,
  defects table, scorecard, top fixes by ROI и evidence gaps;
- `findings.json`: только доказанные findings по общей схеме;
- `scorecard.json`: метрики с numerator, denominator, value и blockers;
- `evidence/manifest.json`: evidence IDs, paths/source, scope and timestamp.

Не редактируй dashboards и не открывай issues. Recommended fixes должны быть
минимальными и проверяемыми. Заверши verdict: `PASS`, `PASS_WITH_RESIDUALS`,
`FAIL` или `BLOCKED`, применив production-critical gate общего контракта.

### Definition of done

- 100% panels в scope присутствуют в inventory и status matrix;
- visual/layout/data contours разделены и имеют собственные evidence;
- screenshot-only data claims отсутствуют;
- critical panels имеют lineage verdict или точный blocker;
- неизвестные параметры не превращены в факты;
- output artifacts валидны и воспроизводимы.
