______________________________________________________________________

Version: 1.0.1
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-03'

______________________________________________________________________

# Dashboard v2 Updates (Audit 2026-03-29)

Источник истины: `grafana/dashboards/bioetl-*.json`

## Проверенные дашборды

- `bioetl-overview-v2`
- `bioetl-control-plane-v1`
- `bioetl-dq-v2`
- `bioetl-provider-health-v2`
- `bioetl-runtime`
- `bioetl-silver-reject-explorer`
- `bioetl-workflow-overview`

## Подтверждено по JSON

- Все shipped dashboards, кроме `bioetl-silver-reject-explorer`, используют `refresh: 30s`.
- `bioetl-silver-reject-explorer` использует `refresh: 1m` и `time.from: now-24h`.
- `time.from` для `overview/runtime/provider-health/dq/workflow` = `now-12h`.
- `time.from` для `control-plane-v1` = `now-6h`.
- Переменные `overview`: `$pipeline`, `$run_type`.
- Переменные `control-plane-v1`: `$pipeline`, `$run_type`.
- Переменные `dq/runtime`: `$pipeline`, `$run_type`, `$stage`.
- Переменные `provider-health-v2`: `$provider`, `$adapter`.
- Переменные `workflow-overview`: `$workflow`, `$status`.
- В Prometheus-backed dashboards отсутствуют forensic variables `$run_id` и `execution`.
- `bioetl-silver-reject-explorer` остаётся единственным shipped exception для `$run_id`/`$payload_hash`.

## Исправления, внесенные в JSON

1. Удалены устаревшие forensic variables `run_id`/`execution` из всех
   Prometheus-backed dashboards; они остались только в
   `bioetl-silver-reject-explorer`.
1. Удалены вводящие в заблуждение формулировки про "Latest Run Only".
1. Исправлен DQ panel `id=12`:

```promql
sum(increase(bioetl_silver_validation_failures_total{pipeline=~"$pipeline"}[24h]))
```

4. Упрощён `3. Provider Health`:

- removed legacy `Pipeline`/`Execution Timestamp` header section;
- removed duplicate repeated latency gauge `id=103`;
- switched summary counters to 15-minute operational windows;
- kept provider-only filtering because health-check metrics are provider-labeled, not pipeline-labeled.

5. Актуальный repeated latency gauge:

```promql
histogram_quantile(0.95, sum by (le, provider) (rate(bioetl_health_check_latency_seconds_bucket{provider=~"$provider"}[5m])))
```

6. Добавлен operator drilldown surface:

- `bioetl-overview-v2`, `bioetl-dq-v2`, `bioetl-provider-health-v2` теперь содержат
  dashboard links `Explore Logs (Loki, tracing profile)` и `Explore Traces (Tempo, tracing profile)`;
- `overview.id=1`, `dq.id=1`, `provider.id=1` дублируют этот handoff через data links;
- Loki links используют low-cardinality entrypoint `{job="bioetl"}` без encoded
  interpolation dashboard variables внутри Explore payload;
- Tempo links сохраняют текущее time range и используют bounded TraceQL filters
  по текущему dashboard scope: `pipeline/run_type` для pipeline dashboards и
  `provider` для provider dashboard.

7. Добавлен отдельный runtime dashboard:

- `bioetl-runtime` собирает Loki-backed `Warnings` и `Unstructured Logs` за выбранный
  Grafana time range;
- panel `Log Hygiene Trend` теперь действительно является timeseries и использует
  adaptive bucket size через `$__interval`;
- Prometheus-backed панели `Alert Conditions` привязаны к тем же fixed windows, что и
  shipped rule pack, но по-прежнему не являются real firing-state alert engine;
- runtime dashboard содержит `Back to Overview` и Explore surfaces; переходы
  к `3. Provider Health` и `4. Data Quality` идут через `1. Overview`.

8. Исправлена selected-range семантика counter-панелей:

- `bioetl-overview-v2` и `bioetl-dq-v2` больше не используют сырые cumulative
  значения `bioetl_records_processed_total` для range-based KPI;
- range summaries и distributions используют `increase(...[$__range])`, а trend-панели
  используют `increase(...[$__interval])`.

9. Убрана misleading зависимость от Prometheus `*_created`:

- панели `Execution Timestamp` заменены на `Latest Data Timestamp`;
- источником теперь служит доменная gauge-метрика `bioetl_data_freshness_seconds`,
  а не bookkeeping series клиента Prometheus.

10. Исправлена семантика aggregate DQ score:

- panel `Data Quality Score` переименована в `Data Quality Score (Volume-weighted)`;
- aggregate score больше не является простым `avg(...)` по сущностям;
- для weighting используется новая gauge-метрика
  `bioetl_dq_validation_record_count`.

11. Уточнён scope control-plane lookup panels:

- `Control-plane Lookup Failures`, `Control-plane Lookup Outcomes` и
  `Control-plane Lookup p95` переименованы в `Global ...`;
- operator UI больше не намекает, что эти панели фильтруются по `$pipeline`,
  потому что underlying metrics имеют только `store/operation/status`.

8. Синхронизирована dashboard-навигация:

- `1. Overview` содержит links `2. Runtime`, `3. Provider Health`,
  `4. Data Quality`, `6. Workflow Overview`, `Explore Logs (Loki, tracing profile)`,
  `Explore Traces (Tempo, tracing profile)`;
- `2. Runtime`, `3. Provider Health`, `4. Data Quality` и
  `6. Workflow Overview` встроены в shipped operator flow и используют
  target-scoped handoffs без variable leakage.

## Актуальные ключевые панели

- `bioetl-overview-v2`: `id=99`, `id=101`, `id=1..4`, `id=110..114`, `id=116`, `id=118..120`, `id=221`
- `bioetl-control-plane-v1`: checkpoint/replay/audit/global-read + lineage detail
- `bioetl-dq-v2`: `id=99`, `id=101`, `id=1..12`, `id=116`
- `bioetl-provider-health-v2`: row `id=91` + панели `1,2,104,7,102`
- `bioetl-runtime`: `id=1..9`, `Back to Overview`, links в `Explore`
- `bioetl-workflow-overview`: `id=1..5` с `$workflow/$status` scope

## Примечание по старым гайдам

Документы в `docs/03-guides/dashboards/`, где фигурируют `$run_id`, `execution` или "latest run only", относятся к устаревшей версии и не описывают текущее состояние JSON.

## Lightweight Manual Validation Process (Dashboard UX)

Применяется после любых изменений dashboard UX, навигации, panel copy,
dashboard links или Explore handoff.

### Incident scenario checklist (3–5 обязательных сценариев)

1. **Runtime деградация**: оператор из `1. Overview` должен корректно перейти в
   `2. Runtime`/Explore и зафиксировать первую action.
2. **Provider latency/health инцидент**: оператор из `1. Overview` должен
   перейти в `3. Provider Health` и получить root-cause signal.
3. **DQ regression**: оператор из `1. Overview` должен перейти в
   `4. Data Quality` и найти failing dimension/pipeline.
4. **Replay safety/blocker**: оператор из `1. Overview` должен перейти в
   `Control Plane / Replay Safety` и подтвердить blocker state.
5. **Workflow failure/skip** (если затронут workflow surface): оператор должен
   перейти в `6. Workflow Overview` и локализовать failing step/status.

### KPI фиксация по каждому сценарию

Для каждого сценария зафиксировать в changelog:

- `time-to-first-action` (сек);
- `click-depth to root cause` (кол-во кликов);
- `first-hop accuracy from Overview` (`yes/no` + короткое пояснение).

Рекомендуемый шаблон записи:

```md
- Scenario: <name>
  - time-to-first-action: <N sec>
  - click-depth to root cause: <N>
  - first-hop accuracy from Overview: <yes/no> (<note>)
```

## Merge Gate: KPI Checklist Required

Dashboard change считается **complete** только если:

1. обновлён этот changelog (`dashboard-v2-updates.md`) с результатами
   lightweight manual validation;
2. заполнен KPI-чеклист минимум по 3 и максимум по 5 инцидентным сценариям;
3. для каждого сценария явно зафиксирован `first-hop accuracy from Overview`.
