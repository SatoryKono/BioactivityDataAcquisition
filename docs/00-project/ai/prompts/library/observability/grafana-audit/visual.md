---
id: prompt.observability.grafana-audit.visual
version: 1.1.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params:
  - SCOPE
  - SCREENSHOTS
  - VIEWPORTS
  - THEMES
  - TYPOGRAPHY_POLICY
  - CRITICAL_STATES
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
  - fragments/dashboard-requirements-audit.md
related_ssot:
  - AGENTS.md
  - docs/01-requirements/DASHBOARD_REQUIREMENTS.md
  - grafana/dashboards
  - docs/03-guides/dashboards/design-system.md
  - docs/03-guides/dashboards/verdict-ontology.md
  - .codex/skills/observability-dashboard/SKILL.md
anti_patterns:
  - Estimating WCAG ratios by eye
  - Treating project font heuristics as WCAG requirements
  - Calling a style preference a defect without task or readability impact
  - Confirming data correctness from visual appearance
tags: [observability, grafana, dashboard, audit, visual, wcag, typography, operator]
summary: Grafana visual audit — palette, WCAG contrast, typography, encoding
max_body_lines: 230
---

# Prompt — палитра, контраст, типографика и visual encoding

## Параметры

| Param | Default |
| --- | --- |
| `SCOPE` | `grafana/dashboards` |
| `SCREENSHOTS` | `discover-or-gap` |
| `VIEWPORTS` | `1366x768,1440x900,1920x1080` |
| `THEMES` | `actual-theme` |
| `TYPOGRAPHY_POLICY` | `repo-policy-or-12-14-24-heuristic` |
| `CRITICAL_STATES` | `derive-from-verdict-ontology` |
| `OUTPUT_DIR` | `reports/audit/grafana/<run_id>/visual` |
| `LANGUAGE` | `ru` |

## Полный текст промта

Ты — эксперт по information visualization, Grafana design systems и
accessibility. Проведи read-only visual accessibility audit scope `{{SCOPE}}`.
Отвечай на языке `{{LANGUAGE}}`.

Используй dashboard JSON/field configuration вместе с renders
`{{SCREENSHOTS}}`. Проверяй viewports `{{VIEWPORTS}}`, themes `{{THEMES}}`,
typography policy `{{TYPOGRAPHY_POLICY}}` и critical states
`{{CRITICAL_STATES}}`. Результаты сохраняй в `{{OUTPUT_DIR}}`.

Не оценивай, нужна ли панель в текущем месте — это layout contour. Не
подтверждай правильность чисел или query semantics — это data-integrity
contour. Если фактический render/DOM недоступен, JSON-only observations помечай
`NOT_VERIFIABLE`, когда они зависят от browser rendering.

### 1. Зафиксируй render context

Для каждого screenshot/render запиши:

- dashboard UID и commit/resource version;
- scenario/time range/variables;
- viewport, device scale factor, browser zoom и theme;
- full page или panel crop;
- evidence path и SHA-256, если tooling поддерживает manifest;
- наличие browser/Grafana chrome, kiosk mode и collapsed rows.

Не сравнивай screenshots с разными variables/time range как theme или viewport
parity evidence.

### 2. Проверь текстовые элементы

Для каждой панели проверь:

- title и description cue;
- Stat/Gauge value, unit, decimals и prefix/suffix;
- axes, ticks, labels и annotation text;
- legends и связь legend item с series;
- table headers/cells, wrapped IDs/paths и action columns;
- variable controls, links и critical UI labels;
- tooltip только как дополнительный, а не единственный источник критической
  информации.

Ищи clipping, truncation, ellipsis, overlap, auto-shrink, слишком плотный
line-height, потерю текста при 125% zoom и перенос, разрушающий смысл.

Измеряй contrast по фактическим foreground/background colors:

- normal text: `>=4.5:1`;
- large text: `>=3:1`;
- значимые icons, focus indicators, chart lines, markers, thresholds и UI
  boundaries: `>=3:1` к соседнему цвету.

Если anti-aliasing/transparency/gradient не позволяют определить ratio из JSON,
извлеки rendered pixels/DOM style или пометь GAP. Не пиши «примерно проходит».

### 3. Проверь color semantics

Для status/threshold/alert cues проверь:

- цвет не является единственным способом передачи значения;
- рядом есть label, icon, marker, line style, textual state или другая
  различимая форма;
- red/green и соседние hues остаются различимыми в grayscale и при common
  color-vision deficiencies;
- одна серия сохраняет стабильный цвет между panels или различие объяснено;
- Classic palette не меняет смысл из-за порядка fields; при необходимости
  series color привязан к устойчивому имени;
- threshold palette имеет одинаковое значение на аналогичных panels;
- UNKNOWN/INCOMPLETE/error не выглядят как OK.

Посчитай `Color-only Encoding Count`; отдельно выдели critical cues.

### 4. Проверь графику

Для timeseries, bars, heatmaps, gauges, state timelines и tables проверь:

- line width, marker visibility и opacity;
- соседние series и overlapping fills;
- dominant gradients/background/grid;
- threshold regions, закрывающие data;
- stacking, скрывающий отдельные значения или делающий сравнение ложным;
- y-axis scale, zero baseline и dual-axis визуальную неоднозначность;
- слишком много series для available plot area;
- legend placement, ordering, truncation и scanability;
- selected state/hover/focus не является единственным читаемым состоянием.

Принцип минимизации chartjunk применяй как эвристику. Не удаляй grid, labels,
markers или redundant cues, если они нужны для ориентации или accessibility.

### 5. Проверь typography hierarchy

Сопоставь фактические размеры с `{{TYPOGRAPHY_POLICY}}`. Если repo policy не
задана, используй только проектную стартовую эвристику:

- axis/tick/secondary labels `>=12 px`;
- main text и legends предпочтительно `>=14 px`;
- key KPI `>=24 px`.

Явно называй её project heuristic, не WCAG requirement. Проверь визуальный
порядок: page goal → current verdict/KPI → explaining chart → secondary label.
Одинаковая типографическая масса не должна создавать ложную равную важность.

### 6. Проверь responsive/theme parity

Для каждого supported viewport/theme проверь:

- first-screen critical facts остаются видимыми;
- no clipped title/value/legend/table action;
- text spacing/zoom не приводит к потере content/function;
- panel chrome не съедает значимую долю plot area;
- light/dark theme не меняет semantic hierarchy;
- alert/unknown/selected/focus states остаются различимыми.

Если поддерживается только одна тема или viewport, не invent requirement:
зафиксируй фактическую support matrix и GAP.

### 7. Findings и acceptance

Для каждого элемента верни:

`dashboard | panel_id | element | evidence | measured_value | criterion |
severity | confidence | fix | acceptance_test`.

Примеры измеримых acceptance tests:

- `line/background contrast >=3:1`;
- `normal text contrast >=4.5:1`;
- status читается в grayscale и содержит text label;
- title/value не clipped на минимальном supported viewport при 100% и 125%;
- series-to-color mapping одинаков на перечисленных panels.

Посчитай:

- Contrast Pass Rate;
- Critical Contrast Pass Rate;
- Color-only Encoding Count;
- Illegible/Clipped Text Count;
- Critical Signal Distinguishability;
- Theme/Viewport Parity.

Создай `visual-report.md`, `visual-checks.json` и `visual-findings.json` в
`{{OUTPUT_DIR}}`. Заверши `PASS`, `PASS_WITH_RESIDUALS`, `FAIL` или `BLOCKED`.

### Definition of done

- каждая panel в scope имеет visual status;
- каждый числовой contrast verdict измерен;
- critical color-only cues отсутствуют либо оформлены findings;
- project heuristics отделены от внешних нормативов;
- screenshot-only data claims отсутствуют.
