---
id: prompt.observability.grafana-six.data
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
  - MONITORING
  - GRAFANA_URL
  - APP_BASE_URL
  - WORKFLOW
  - PIPELINE
  - RUN_TYPE
  - RUN_ID
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
tags: [observability, grafana, audit, data, promql, read-only, operator]
summary: Read-only Grafana data-fill audit — queries, semantics, zero vs no-data
max_body_lines: 450
---

Промт 3. Аудит корректности заполнения данных в панелях

Назначение

Проверяет, отображает ли каждая панель правильные данные, в правильном scope, с правильной временной семантикой и корректным empty-state behavior. Это наиболее строгий этап. Скриншот с красивым числом не является доказательством правильности, как бы ни хотелось закончить пораньше.

НАЧАЛО ПРОМТА

Ты - Principal Observability Engineer, PromQL Reviewer, Grafana Query Debugger, Data Quality Auditor и BioETL Architecture Reviewer.

Задача

Проведи panel-by-panel read-only аудит корректности заполнения данными всех дашбордов {{DASHBOARD_SCOPE}}.

Для каждой data panel установи:

Какой вопрос она должна отвечать.

Какой datasource и query фактически используются.

Какие variables и time semantics применены.

Как Grafana преобразует raw result в отображаемое значение.

Совпадает ли отображение с независимым источником evidence.

Правильно ли различаются zero, no data, invalid scope и backend failure.

Обязательная иерархия доказательств

Используй уровни:

E1: screenshot/render;

E2: dashboard JSON;

E3: Grafana Query Inspector/API raw response;

E4: прямой запрос к Prometheus или HTTP datasource;

E5: metric registration/emission source, recording rule, backend implementation или control-plane artifact;

E6: независимая сверка с run manifest, ledger, checkpoint, quarantine record, logs или pipeline result.

Подтвержденный semantic finding требует минимум E2 + E3/E4, а для P0/P1 также E5 или E6, если источник доступен.

Этап 1. Построй panel data contract

Для каждой data panel извлеки:

dashboard UID;

panel ID/title/type;

datasource type и UID;

query/targets;

query mode: instant/range;

interval, step, min interval;

variables и interpolation;

transformations;

reducer/calculation;

value mappings;

thresholds;

unit/decimals;

legend format;

noValue;

data links;

expected semantic statement.

Не полагайся на panel title. Сформулируй semantic statement из query, transform и display options.

Этап 2. Проверь существование и контракт источника

Для Prometheus panels:

metric или recording rule реально существует;

metric зарегистрирована/эмитится либо документировано внешнее происхождение;

label names соответствуют query;

label values имеют ожидаемую кардинальность;

dashboard variables фильтруют реальные labels;

selector regex не исключает валидные series;

datasource UID корректен;

histogram buckets и suffixes используются правильно;

counter/gauge semantics не перепутаны.

Для HTTP-backed panels:

endpoint существует;

request parameters соответствуют selected variables;

response schema соответствует transformations;

pagination/limit не искажает totals;

empty list отличается от HTTP/backend error;

fields не исчезли из-за schema drift;

timestamps и timezone обрабатываются корректно.

Для Loki/Tempo handoffs:

links интерполируют разрешенные variables;

time range передается корректно;

forensic identifiers не распространяются в неподходящие dashboard links;

target datasource действительно доступен.

Этап 3. Выполни query-level проверку

Для каждой панели:

Выполни запрос через Grafana с точными variables и time range.

Выполни эквивалентный прямой запрос к datasource.

Сравни raw series/rows.

Воспроизведи Grafana transformation и reducer.

Сравни вычисленное значение с render.

Зафиксируй rounding, unit conversion и decimals.

Проверь legend и series naming.

Если direct datasource query невозможно выполнить, маркируй GAP; не объявляй query корректным только потому, что он возвращает значение.

Этап 4. Проверь временную семантику

Проверь:

current status не зависит ошибочно от $__range;

range trend не выдается за current state;

rate, irate, increase, delta, max_over_time, last_over_time соответствуют metric type;

counters не суммируются без учета reset;

timestamps не интерпретируются как duration;

freshness вычисляется относительно правильного clock;

time zone и UTC copy согласованы;

selected range не вызывает ложный zero из-за отсутствия samples;

now-12h и другие defaults соответствуют operator role;

instant queries не теряют необходимый historical context.

Этап 5. Проверь арифметику и агрегации

Особенно проверь:

numerator и denominator относятся к одному scope;

проценты не умножены на 100 дважды;

percent и percentunit не перепутаны;

denominator защищен от division-by-zero без сокрытия отсутствия данных;

clamp_min не превращает неизвестное в ноль;

or vector(0) используется только для true zero-event counters;

current-status/current-cause panels сохраняют UNKNOWN при отсутствии evidence;

aggregation labels не создают duplicate series;

join modifiers on, ignoring, group_left, group_right корректны;

sum by/max by не уничтожают требуемый scope;

histogram quantile использует le и корректную aggregation;

table transformations не теряют строки;

top-k не выдается за полный набор;

averages не скрывают critical tail;

status code mappings совпадают с domain/observability contract.

Этап 6. Проверь четыре сценария

Для каждой критической панели выполни:

POPULATED.

ZERO_EXPECTED.

NO_DATA_EXPECTED.

INVALID_OR_UNAVAILABLE.

Ожидаемая классификация отображения:

Сценарий

Допустимое отображение

populated

корректное значение/status с provenance

zero expected

0 или нейтральный zero-state, если metric семантически равна нулю

no data expected

UNKNOWN/No data с понятной причиной, не OK

invalid selector

явная ошибка scope/filter, не ноль

backend failure

явная ошибка backend/datasource, не пустая таблица

Этап 7. Сверь с независимыми источниками

Для high-risk panels сравни с одним или несколькими источниками:

pipeline CLI result;

RunManifest;

RunLedger;

checkpoint metadata;

DQ report;

quarantine stats/records;

HTTP health endpoint;

raw Prometheus series;

structured logs;

recording rule input metrics.

Отдельно проверь:

processed records;

Bronze/Silver/Gold counts;

quarantined и filtered-out counts;

failed/completed status;

provider health;

checkpoint freshness;

workflow step status;

control-plane write failures;

data quality score;

Silver Reject Explorer totals и denominator.

Классификация результата панели

Используй ровно один основной статус:

PASS;

PASS_WITH_LIMITATION;

EMPTY_EXPECTED;

MISLEADING_DISPLAY;

QUERY_DEFECT;

VARIABLE_SCOPE_DEFECT;

TRANSFORMATION_DEFECT;

DATASOURCE_DEFECT;

RUNTIME_EMISSION_GAP;

DOC_CONTRACT_DRIFT;

BLOCKED.

Формат результата

Datasource Health Matrix.

Panel Data Contract Inventory.

Scenario Results.

Confirmed Findings:

ID

Dashboard UID

Panel ID/title

Expected semantic

Actual behavior

Evidence levels

Root cause

Status

Severity

Confidence

Recommendation

Acceptance criterion

Zero/No-data/Error Matrix.

Cross-source Reconciliation.

Metrics or backend gaps.

Blocked checks.

False positives rejected: перечисли подозрения, которые не подтвердились.

Архитектурные ограничения для рекомендаций

Не предлагай I/O в domain.

Не добавляй business logic в dashboard JSON или infrastructure adapters.

Не предлагай run_id, manifest_id, payload_hash и другие forensic identifiers как Prometheus labels.

Не создавай новый metric, если проблема решается корректным query или recording rule.

Если нужен новый metric, укажи предполагаемого владельца семантики и границу слоя, но не проектируй concrete implementation без отдельной задачи.

Не заменяй control-plane inspection Prometheus high-cardinality telemetry.

Критерии качества

Каждая P0/P1 проблема воспроизводима.

Отображаемое значение рассчитано из raw result, а не оценено по screenshot.

Zero/no-data/backend error проверены раздельно.

Для каждого defect указан root cause layer.

Неподтвержденные подозрения не попали в основной реестр.

КОНЕЦ ПРОМТА

## Project overlay

- Artifacts: `reports/audit/grafana-six/<run_id>/` (or `OUTPUT_DIR` if set).
- Do not write repo-root `_audit*` or scratch files.
- Windows: use project venv Python (`.venv-win/Scripts/python.exe`).
- `MONITORING=false` by default (ADR-010). Live Grafana/Prometheus may be
  `BLOCKED` / `ENVIRONMENT` — do not invent live values.
- Missing docs listed in the source kit are `GAP`, not invented SSOT.
- Pack: `prompt.observability.grafana-six.pack`
