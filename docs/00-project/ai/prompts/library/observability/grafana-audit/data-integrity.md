---
id: prompt.observability.grafana-audit.data-integrity
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params:
  - SCOPE
  - GRAFANA_VERSION
  - CRITICAL_PANELS
  - REFERENCE_SPEC
  - TIME_RANGE
  - VARIABLES
  - KNOWN_EVENTS
  - MONITORING
  - GRAFANA_URL
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
  - Confirming data correctness from a screenshot
  - Auditing the raw query while ignoring Grafana transformations and reductions
  - Applying generic invariants without a metric definition
  - Claiming reconciliation without executing an equivalent request
  - Exposing datasource credentials or service-account tokens in artifacts
tags: [observability, grafana, dashboard, audit, data, lineage, integrity, operator]
summary: Forensic Grafana data audit — lineage, exact queries, invariants, reconciliation
max_body_lines: 260
---

# Prompt — корректность данных и data integrity

## Параметры

| Param | Default |
| --- | --- |
| `SCOPE` | `grafana/dashboards` |
| `GRAFANA_VERSION` | `detect` |
| `CRITICAL_PANELS` | `derive-from-contracts` |
| `REFERENCE_SPEC` | `repo-metric-catalog-or-gap` |
| `TIME_RANGE` | `fixed-required-for-reconciliation` |
| `VARIABLES` | `defaults-plus-edge-matrix` |
| `KNOWN_EVENTS` | `repo-evidence-or-gap` |
| `MONITORING` | `false` |
| `GRAFANA_URL` | `unset` |
| `OUTPUT_DIR` | `reports/audit/grafana/<run_id>/data-integrity` |
| `LANGUAGE` | `ru` |

## Полный текст промта

Ты — SRE и data-quality reviewer Grafana. Проведи forensic read-only audit
корректности данных для `{{SCOPE}}` на языке `{{LANGUAGE}}`.

Проверь critical panels `{{CRITICAL_PANELS}}` на фиксированном диапазоне
`{{TIME_RANGE}}` с variable matrix `{{VARIABLES}}`. Источник определений и
эталонных запросов — `{{REFERENCE_SPEC}}`; известные события —
`{{KNOWN_EVENTS}}`. Сохраняй результаты в `{{OUTPUT_DIR}}`.

Не запускай monitoring stack, если `{{MONITORING}} != true`. Даже при
`MONITORING=true` сначала выполни repository preflight и используй
`{{GRAFANA_URL}}` только как явно разрешённый endpoint. Все операции Grafana,
MCP и datasource должны оставаться read-only. Не печатай токены, cookies,
пароли, connection strings или secret-bearing headers.

### 1. Установи фактический контракт

Для каждого dashboard и critical panel зафиксируй:

- shipped JSON path, dashboard UID/title и panel ID/title/type;
- фактическую Grafana version и JSON/API model, если они доказуемы;
- datasource UID/type и provisioning/source evidence;
- environment, cluster, tenant, database/schema/index;
- заявленную metric semantics, unit, denominator, owner и tolerance;
- dashboard time range/timezone и panel overrides;
- evidence IDs для JSON, request, raw result, transformed result и reference.

Если version, datasource identity, metric definition или reference отсутствуют,
пометь конкретное поле `[неполные данные]`. Не подставляй предположение как
доказанный факт и не подтверждай бизнес-семантику без metric catalog/SLO/BI spec.

### 2. Восстанови полный lineage

Восстанови цепочку, не пропуская presentation stages:

`datasource → raw query → variable interpolation → dashboard range → panel
relative time/time shift → timezone → interval/maxDataPoints/rate interval →
datasource aggregation → Grafana transformations → joins/grouping → reductions
→ field overrides → units/decimals → value mappings/noValue → thresholds →
visualization`.

Для каждого stage сохрани input, operation, output schema, доказательство и
возможный failure mode. Конфиденциальные значения редактируй; query semantics,
labels, filters и timestamps не скрывай.

Проверь отдельно:

#### SOURCE

- правильный datasource UID/type;
- нужные environment, cluster, tenant и storage namespace;
- отсутствие silent fallback на default datasource;
- datasource health, если endpoint доступен и разрешён.

#### METRIC SEMANTICS

- metric/field соответствует названию и description panel;
- gauge/counter semantics и reset/wrap handling;
- корректность `rate`/`increase`, histogram bucket aggregation и quantile;
- numerator, denominator, normalization, unit и currency;
- source freshness и допустимый lag.

#### TIME

- dashboard `from/to`, panel relative time/time shift и timezone;
- `$__interval`, `$__rate_interval`, `intervalMs`, `maxDataPoints`;
- alignment окон, calendar/business-day boundaries и daylight-saving cases;
- сравнимость текущего, выбранного range и выбранного run.

#### FILTERS И VARIABLES

- single, multi, All и empty values;
- escaping/regex interpolation и dependent variables;
- environment, namespace, service и tenant filters;
- дефолт, который не создаёт ложное healthy/empty состояние;
- labels не теряют нужные series и не добавляют чужие объекты.

#### AGGREGATIONS

- `sum/avg/min/max/count`, grouping dimensions и joins;
- weighted против unweighted average;
- duplicate series, fan-out и double counting;
- `sum(parts)`/whole reconciliation только для совместимых dimensions;
- reduction производится над ожидаемым field и окном.

#### DISPLAY PIPELINE

- transformations просмотрены после raw query result;
- join/group/reduce/organize/rename не меняют meaning скрыто;
- null, NaN, missing series, stale и numeric zero различаются;
- `connect nulls`, value mappings, no-value text и thresholds не маскируют gap;
- overrides не задают неверные unit/decimals/min/max.

#### ANNOTATIONS

- timestamp, timezone, tags, dashboard/panel binding;
- coverage известных deploy/incident events;
- отсутствие misleading alignment из-за time shift или browser timezone.

### 3. Воспроизведи exact panel request

Если разрешён read-only Grafana MCP, используй минимальный набор инструментов:
поиск dashboard, summary/property, panel queries, datasource metadata и
`run_panel_query` только для target panels. Передай тот же fixed time range и
variable overrides.

Если используется HTTP API, сначала определи поддерживаемую модель текущей
версии. Для datasource применяй UID-based metadata/health endpoints и
воспроизводи фактический `POST /api/ds/query` request из panel JSON или Query
Inspector. Не конструируй datasource-specific payload по памяти.

Для каждого запуска сохрани redacted request fingerprint:

- endpoint/API model;
- datasource UID/type;
- refId;
- resolved query/filters;
- from/to/timezone;
- variables;
- intervalMs/maxDataPoints;
- response status/schema/cardinality/freshness;
- raw evidence path.

Недоступный UI/API/MCP — `BLOCKED` или `NOT_VERIFIABLE`, а не `PASS` и не data
`FAIL`. JSON mismatch может доказать configuration defect; screenshot alone —
никогда data correctness.

### 4. Выполни минимальный integrity suite

Для каждой critical panel запусти и запиши `PASS/FAIL/BLOCKED/NA`:

1. `T1 Query execution` — exact request выполняется без error.
2. `T2 Datasource/environment identity` — источник соответствует contract.
3. `T3 Expected non-empty/cardinality` — empty/zero/cardinality объяснимы.
4. `T4 Time-window semantics` — границы, timezone и interval корректны.
5. `T5 Variable/filter matrix` — single/multi/All/empty edge cases.
6. `T6 Unit semantics` — source unit, conversion, decimals и label согласованы.
7. `T7 Aggregation semantics` — dimensions, denominator и reduction корректны.
8. `T8 Null/missing-data behavior` — missing не превращён молча в zero/healthy.
9. `T9 Independent reconciliation` — panel и reference сравнимы на том же окне.
10. `T10 Known-event/annotation alignment` — normal и known-anomaly periods.

Domain invariants применяй только если они следуют из definition, например:
`errors <= requests`, `0 <= utilization <= 1`, `success + failure ≈ total`,
`sum(parts) ≈ whole`, `p50 <= p90 <= p95 <= p99`, non-negative counter rate с
учётом reset/wrap. Для каждого invariant укажи applicability evidence и
tolerance; иначе статус `NA`, а не выдуманный test.

### 5. Reconciliation и verdict

Сравни panel result, Inspector/transformed result и independent/reference query
на идентичных inputs. Зафиксируй absolute/relative error, tolerance, sample size
и расхождение по timestamps/dimensions. Не сравнивай числа с разными окнами,
timezone, aggregation grain или filters.

Классифицируй root cause: `source`, `query`, `variable/filter`, `time`,
`aggregation`, `transformation`, `presentation`, `datasource operational` или
`unknown`. Data `FAIL` допустим только при прямом JSON/API/query evidence и
воспроизводимом test. Severity назначай по влиянию на решение, не по величине
процентного расхождения сама по себе.

### 6. Результаты

Создай в `{{OUTPUT_DIR}}`:

- `lineage.json` — полный stage-by-stage lineage;
- `integrity-tests.json` — T1–T10 и domain invariants;
- `reconciliation.csv` — panel/reference inputs, values, error, tolerance;
- `data-findings.json` — только evidence-backed findings;
- `data-integrity-report.md` — summary, risks, fixes, unknowns/blockers;
- `evidence-manifest.json` — redacted request/result paths и hashes.

Каждый finding должен содержать dashboard, panel ID/title, expected, actual,
evidence IDs, severity P0–P3, confidence, root cause, minimal fix и executable
verification test. Не включай secrets в artifacts.

### Acceptance

`PASS` для critical panel только если lineage coverage = 100%, обязательные
T1–T10 применимые tests прошли, reference reconciliation находится в tolerance,
а missing/null/zero semantics доказаны. Отсутствующий source-of-truth означает
`[неполные данные]`/`BLOCKED`, но не автоматический `FAIL` и не `PASS`.

### Definition of done

- каждая critical panel имеет полную lineage table;
- каждый test имеет evidence path и детерминированный verdict;
- exact panel request воспроизведён либо blocker описан точно;
- reconciliation использует одинаковые time/filter/aggregation inputs;
- data findings не основаны только на screenshot.
