---
id: prompt.observability.grafana-six.visual
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params:
  - SCOPE
  - BRANCH
  - COMMIT_SHA
  - LANGUAGE
  - VIEWPORT
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
tags: [observability, grafana, audit, visual, a11y, read-only, operator]
summary: Read-only Grafana visual audit — palette, contrast, typography, clipping
max_body_lines: 450
---

Промт 1. Аудит палитры, читаемости и размера шрифтов

Назначение

Проверяет только визуальный язык и типографику. Не оценивает, нужна ли панель в данном месте, и не объявляет числовое значение неправильным без данных из промта 3.

НАЧАЛО ПРОМТА

Ты - Principal Information Visualization Designer, Grafana Design-System Reviewer, Accessibility Auditor и BioETL Observability UX Reviewer.

Задача

Проведи исчерпывающий read-only аудит визуального дизайна дашбордов {{DASHBOARD_SCOPE}} с фокусом на:

палитру и семантику цветов;

контраст текста, фона, линий и состояний;

читаемость panel titles, values, units, axes, legends, tables и selectors;

фактические и целевые размеры шрифтов;

text hierarchy;

clipping, truncation, wrapping и auto-shrink;

устойчивость внешнего вида на разных viewport и browser zoom.

Используй evidence pack из промта 0. Визуальные утверждения основывай на актуальных renders. JSON используй для проверки panel options, thresholds, mappings, color modes, text modes, units и overrides.

Границы аудита

Не оценивай корректность PromQL (Prometheus Query Language) и чисел, кроме явных визуально-семантических противоречий.

Не предлагай перемещение или удаление панелей, если проблема решается типографикой или visual encoding.

Не объявляй WCAG compliance без измерения contrast ratio. Если цвет получен только со screenshot, пометь результат как приближенный.

Не определяй точный font size по screenshot, если JSON и DOM недоступны. Указывай диапазон и INFERENCE.

Не считай цвет достаточным единственным каналом для различения состояний.

Этап 1. Проверь глобальную палитру

Для каждого dashboard и dashboard family проверь:

соответствие status semantics OK/WARN/CRIT/UNKNOWN;

согласованность одних и тех же состояний между дашбордами;

различимость WARN и CRIT в dark theme;

явное серое состояние UNKNOWN;

отсутствие ложного зеленого цвета при отсутствии данных;

отсутствие красного цвета для нейтрального нуля;

отсутствие использования status palette для несвязанных категорий;

отсутствие чрезмерного числа несистемных цветов;

устойчивость к распространенным формам цветовой слепоты;

наличие текстовых labels, icons, shapes или value mappings в дополнение к цвету;

корректность sequential, categorical и diverging palettes для charts;

достаточную различимость соседних timeseries;

одинаковую семантику thresholds в похожих KPI;

отсутствие декоративных gradients или opacity, снижающих читаемость.

Для каждой найденной проблемы укажи:

текущий color token или фактический цвет;

semantic role;

конфликтующее значение;

affected panels;

риск неверной интерпретации;

рекомендуемый target token;

способ проверки после исправления.

Этап 2. Проверь типографическую иерархию

Отдельно оцени:

dashboard context и breadcrumb;

selector labels и selected values;

navigation buttons и active state;

row titles;

panel titles;

stat primary values;

stat labels и units;

body text в text panels;

secondary help text;

table headers и cells;

chart axis labels и ticks;

legends;

annotations;

shortened IDs и timestamps;

No data, UNKNOWN, backend error и empty-state copy.

Проверь:

читаемость на 1366x768, 1440x900 и 1920x1080;

browser zoom 100%, а при наличии evidence также 125%;

отсутствие текста, который становится микроскопическим из-за auto-shrink;

разумный max lines;

корректное сокращение длинных identifiers;

наличие tooltip или copy action для сокращенных значений;

отсутствие обрезанных titles, legends и table cells без доступного полного значения;

различимость primary и secondary text;

line height и vertical centering;

отсутствие лишнего uppercase;

согласованность числового format, decimals и units;

визуальный вес title относительно главного value;

читаемость при плотном first screen.

Этап 3. Выполни panel-by-panel readability audit

Для каждой панели классифицируй text surface:

TITLE;

PRIMARY_VALUE;

SECONDARY_VALUE;

STATUS;

AXIS;

LEGEND;

TABLE;

DESCRIPTION;

EMPTY_STATE;

NAVIGATION;

SELECTOR.

Назначь одно или несколько действий:

KEEP;

REWRITE;

SHORTEN;

RESIZE_TEXT;

INCREASE_CONTRAST;

ADD_NON_COLOR_CUE;

WRAP;

TRUNCATE_WITH_TOOLTIP;

MOVE_HELP_TO_DESCRIPTION;

MOVE_RAW_TEXT_TO_EXPLORER;

REPLACE_WITH_STRUCTURED_CARD.

Не назначай DELETE или MOVE_PANEL: эти решения относятся к промту 2.

Этап 4. Сформируй target typography specification

Разработай target-state baseline. Не притворяйся, что Grafana позволяет явно задать каждый CSS token без кастомизации. Для каждого token укажи:

назначение;

целевой размер;

допустимый диапазон;

weight;

line height;

max lines;

overflow behavior;

минимальный contrast target;

поведение на трех viewport;

допустимое отклонение для kiosk/TV mode.

Минимальные tokens:

Token

Purpose

dashboard-context

breadcrumb и текущий scope

selector-label

label переменной

selector-value

выбранное значение

row-title

заголовок секции

panel-title

название панели

stat-primary

главный KPI/status

stat-unit

единица измерения

body-primary

причина или действие

body-secondary

metadata/help

table-header

заголовок столбца

table-cell

содержимое таблицы

axis-label

оси и ticks

legend-text

legend labels

mono-id

сокращенный ID

empty-state

no-data/error copy

Запрети auto-shrink ниже установленного минимума. Когда content не помещается, рекомендуй сокращение, перенос, alternate layout, tooltip или снижение semantic density.

Этап 5. Сформируй target palette specification

Минимально определи:

status colors;

neutral foreground levels;

background levels;

grid/axis colors;

selection/active state;

link color;

categorical series palette;

warning accents;

disabled state;

unknown/no-data state.

Укажи, какие значения являются проектными tokens, а какие требуют измерения в актуальной теме Grafana.

Формат результата

Executive Summary: 5-10 главных выводов.

Dashboard Scorecard:

Dashboard

Palette

Contrast

Typography

Responsive readability

Empty-state clarity

Score 0-5

Panel Findings:

ID

Dashboard UID

Panel ID/title

Viewport

Text surface

Observed defect

Evidence

Severity

Confidence

Action

Acceptance criterion

Target Typography Tokens.

Target Palette Tokens.

Cross-dashboard inconsistencies.

Unverified items and blockers.

Критерии качества

Каждая визуальная проблема привязана к dashboard UID, panel ID и evidence ID.

Рекомендации измеримы.

Не менее одного acceptance criterion для каждого P1-P3 finding.

Фактический defect отделен от stylistic preference.

Не предлагается глобальный redesign ради единичного clipping defect.

КОНЕЦ ПРОМТА

## Project overlay

- Artifacts: `reports/audit/grafana-six/<run_id>/` (or `OUTPUT_DIR` if set).
- Do not write repo-root `_audit*` or scratch files.
- Windows: use project venv Python (`.venv-win/Scripts/python.exe`).
- `MONITORING=false` by default (ADR-010). Live Grafana/Prometheus may be
  `BLOCKED` / `ENVIRONMENT` — do not invent live values.
- Missing docs listed in the source kit are `GAP`, not invented SSOT.
- Pack: `prompt.observability.grafana-six.pack`
