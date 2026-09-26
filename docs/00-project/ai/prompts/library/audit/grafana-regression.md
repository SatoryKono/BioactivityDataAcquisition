---
id: prompt.observability.grafana-audit.regression
version: 1.1.0
status: active
class: operator-paste
owner: BioETL Team
runtimes:
- grok
- codex
- any
params:
- BASELINE_REF
- CANDIDATE_REF
- SCOPE
- BASELINE_REPORT
- FIXED_WINDOWS
- VARIABLE_MATRIX
- VIEWPORTS
- THEMES
- REFERENCE_SPEC
- MONITORING
- OUTPUT_DIR
- LANGUAGE
includes:
- fragments/git-safety.md
- fragments/debt-budget-ban.md
- fragments/env-guardrail.md
- fragments/evidence-contract-v3.md
- fragments/language-ru.md
- fragments/audit-scale.md
- fragments/finding-schema.md
related_ssot:
- AGENTS.md
- docs/01-requirements/DASHBOARD_REQUIREMENTS.md
- grafana/dashboards
- docs/03-guides/dashboards/design-system.md
- docs/03-guides/dashboards/verdict-ontology.md
- .codex/skills/observability-dashboard/SKILL.md
anti_patterns:
- Comparing moving now-relative windows between baseline and candidate
- Accepting a visual fix that silently changes data semantics
- Retesting only the edited JSON fragment instead of affected behavior
- Marking CANNOT_VERIFY as FIXED
- Ignoring new regressions outside the original finding list
tags:
- observability
- grafana
- dashboard
- audit
- regression
- acceptance
- release
- operator
summary: Grafana regression acceptance — baseline retest, new regressions, release
  gate
max_body_lines: 240
---
# Prompt — regression acceptance после исправлений

## Параметры

| Param | Default |
| --- | --- |
| `BASELINE_REF` | `required` |
| `CANDIDATE_REF` | `HEAD` |
| `SCOPE` | `grafana/dashboards` |
| `BASELINE_REPORT` | `required` |
| `FIXED_WINDOWS` | `required-for-data-comparison` |
| `VARIABLE_MATRIX` | `baseline-plus-edge-cases` |
| `VIEWPORTS` | `1366x768` |
| `THEMES` | `dark` |
| `REFERENCE_SPEC` | `repo-metric-catalog-or-gap` |
| `MONITORING` | `false` |
| `OUTPUT_DIR` | `reports/audit/grafana/<run_id>/regression` |
| `LANGUAGE` | `ru` |

## Полный текст промта

Ты — release reviewer Grafana dashboards. Проведи evidence-based regression
acceptance для baseline `{{BASELINE_REF}}` и candidate `{{CANDIDATE_REF}}` в
scope `{{SCOPE}}` на языке `{{LANGUAGE}}`.

Baseline findings и tests бери из `{{BASELINE_REPORT}}`. Data comparisons
выполняй только на одинаковых fixed windows `{{FIXED_WINDOWS}}` и variable
matrix `{{VARIABLE_MATRIX}}`. Visual comparisons выполняй на одинаковых
viewports `{{VIEWPORTS}}` и themes `{{THEMES}}`. Источник metric semantics и
tolerances — `{{REFERENCE_SPEC}}`. Результаты сохраняй в `{{OUTPUT_DIR}}`.

Это read-only acceptance audit. Не исправляй dashboard, не создавай issues и не
merge/push. Не запускай monitoring stack, если `{{MONITORING}} != true`.

### 1. Зафиксируй сравнимый baseline

До verdict зафиксируй:

- baseline/candidate SHA или immutable refs;
- dashboard UID, panel IDs и JSON hashes;
- Grafana/version/API model и datasource identities;
- fixed from/to/timezone, variables, interval/maxDataPoints;
- viewport/theme/render method;
- baseline P0/P1 findings, acceptance tests и tolerances;
- changed dashboards/panels/queries/transformations/fieldConfig/gridPos/links.

Если baseline artifact или immutable ref недоступен, верни `BLOCKED`: нельзя
создавать baseline по памяти или сравнивать candidate только с описанием issue.

Не сравнивай два `now-*` render/query, полученных в разное время. Преврати их в
одинаковый fixed window либо пометь data comparison `CANNOT_VERIFY`.

### 2. Построй affected surface

Для каждого change определи прямые и соседние consumers:

- изменённая panel и все repeated instances;
- shared variable, datasource, library panel или transformation consumers;
- panels, затронутые row/grid geometry, legend или shared color semantics;
- source/target dashboard links и preserved context;
- critical first viewport и diagnostic journey;
- reference query/invariant, если изменилась data semantics.

Ретестируй все baseline P0/P1 независимо от textual diff. Для P2/P3 ретестируй
изменённые и затронутые surfaces. Не раздувай scope до полного повторного аудита,
но проверь ближайшие regression boundaries каждого fix.

### 3. Повтори baseline tests

Для каждого предыдущего finding выполни исходный acceptance test на candidate и
назначь ровно один статус:

- `FIXED` — expected outcome доказан, test PASS;
- `PARTIAL` — часть outcome достигнута, residual evidence остаётся;
- `NOT_FIXED` — defect воспроизводится;
- `CANNOT_VERIFY` — обязательная evidence недоступна.

Сохрани before/after evidence IDs, actual values, tolerance и reason. Issue text,
code diff или новый label сами по себе не доказывают `FIXED`.

Обязательно повтори:

- все baseline P0/P1 tests;
- contrast/color-only/typography tests изменённых visual elements;
- exact panel queries и reference/reconciliation queries;
- single/multi/All/empty variable cases;
- fixed time-window и timezone/business-boundary cases;
- null/missing/zero/stale/query-error/datasource-error states;
- annotations/known-event alignment;
- first viewport, drill-down, links и back-navigation для layout changes.

### 4. Проверь semantic parity

Для каждой визуальной или layout правки докажи, что без явного требования не
изменились:

- datasource UID/environment/tenant;
- resolved query, filters и variables;
- time range, timezone, interval и aggregation;
- transformations/reductions;
- unit, denominator, null/noValue/value mappings;
- threshold semantics.

Если visual improvement изменил data meaning, release verdict — `FAIL`, пока
новая semantics не подтверждена отдельным approved contract и integrity tests.

Для разрешённой data fix сравни candidate с reference, а не требуй byte-level
parity с заведомо неверным baseline.

### 5. Найди новые regressions

Сравни candidate с baseline по:

- dashboard/panel inventory и UIDs;
- JSON schema, queries, variables, transformations, overrides и links;
- grid overlap/gaps, clipping, scroll и first viewport;
- critical contrast, grayscale status и series identity;
- query execution, cardinality, freshness, units и reconciliation;
- render states для normal, empty/zero, anomaly и error scenarios.

Каждое новое evidence-backed отклонение запиши как `NEW_REGRESSION` с P0–P3,
root cause, affected scope и deterministic test. Не создавай cosmetic finding без
task/readability/decision risk.

### 6. Release gate

Рассчитай и запиши машинно-читаемые gates:

```text
P0 == 0
P1 == 0
critical_panel_lineage_coverage == 100%
mandatory_integrity_test_pass_rate == 100%
critical_text_contrast_pass_rate == 100%
critical_graphics_contrast_pass_rate == 100%
critical_color_only_encoding_count == 0
baseline_P0_P1_retested == 100%
new_regression_P0_P1 == 0
```

Для production-critical dashboard любое нарушение — `FAIL`. Для non-critical
dashboard P1 exception допустим только при явном project policy, owner, rationale
и due date; не создавай exception самостоятельно.

`CANNOT_VERIFY` по обязательному P0/P1 test блокирует release и не считается
PASS. Не понижай severity для прохождения gate.

### 7. Результаты

Создай в `{{OUTPUT_DIR}}`:

- `regression-report.md` — executive summary, affected surface и verdict;
- `finding-status.json` — baseline finding → status → evidence;
- `retest-results.json` — test inputs, expected, actual, tolerance, result;
- `semantic-parity.json` — query/data/presentation comparison;
- `new-regressions.json` — только новые evidence-backed findings;
- `release-gate.json` — каждый gate, numerator/denominator и evidence;
- `evidence-manifest.json` — baseline/candidate JSON, render/query paths, hashes.

В summary укажи число `FIXED/PARTIAL/NOT_FIXED/CANNOT_VERIFY`, новые P0–P3,
release verdict и точный следующий action для каждого failing gate.

### Acceptance

`PASS` только если все release gates выполнены, 100% baseline P0/P1
детерминированно ретестированы, candidate не содержит новых P0/P1, а visual
fixes не изменили data semantics без подтверждённого контракта.

### Definition of done

- baseline и candidate сравнивались на одинаковых inputs;
- каждый baseline finding получил один статус и evidence;
- affected surfaces и соседние regression boundaries проверены;
- new regressions искались независимо от baseline list;
- release verdict полностью воспроизводим из `release-gate.json`.
