______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-13'

______________________________________________________________________

# Dashboard Extension Guide (LLM)

Дата сверки: **2026-04-13**
Источник истины: `grafana/dashboards/*.json`

Короткий playbook для LLM/AI-агента, который меняет или расширяет shipped
Grafana dashboards в BioETL.

## 1. Обязательная стартовая точка

Перед правкой dashboard:

1. Прочитай целевой JSON в `grafana/dashboards/`.
1. Сверь текущую navigation model и operator role dashboard.
1. Не выводи структуру dashboard по памяти, скриншотам или старым docs.

## 2. Текущая модель shipped dashboards

- `1. Overview` — hub: `2. Runtime`, `Control Plane v1`, `3. Provider Health`, `4. Data Quality`, `Explore Logs (Loki, tracing profile)`, `Explore Traces (Tempo, tracing profile)`
- `2. Runtime` — `Back to Overview`, `Control Plane v1`, `4. Data Quality` + Explore links
- `BioETL Control Plane v1` — `Back to Overview`, `2. Runtime`, `4. Data Quality` + Explore links
- `3. Provider Health` — `Back to Overview`, `2. Runtime` + Explore links
- `4. Data Quality` — `Back to Overview`, `5. Silver Reject Explorer` + Explore links

Если правка меняет эту модель, синхронизируй docs в том же change set.

## 3. Обязательные invariants

- Не меняй `uid` без явной migration reason.
- Не invent metric names — используй только реально существующие метрики.
- Не добавляй high-cardinality filters/labels в summary-panels без необходимости.
- Не используй encoded Loki interpolation по `$pipeline/$provider` как источник истины.
- Не превращай `Alert Conditions` в “real alert engine”, если datasource/state этого не поддерживает.

## 4. Query conventions

### Prometheus

Если отсутствие серии означает “событий нет”, а не “источник сломан”, используй:

```promql
sum(increase(metric_name[24h])) or vector(0)
```

Если отсутствие серии должно остаться диагностическим сигналом, не маскируй его
через `or vector(0)`.

### Loki

Используй безопасный baseline:

```logql
{job="bioetl"}
```

Для log-hygiene и warnings работай через `| json` и `__error__`.

### Tempo

Используй минимальный, но contextual handoff:

```text
datasource = tempo
queryType = traceqlSearch
query = { span."bioetl.pipeline" =~ "${pipeline:regex}" && span."bioetl.run_type" =~ "${run_type:regex}" }
```

Для provider-only dashboards замени pipeline/run_type filter на:

```text
query = { span."bioetl.provider" =~ "${provider:regex}" }
```

## 5. Docs cascade rule

Если изменилось хотя бы одно из следующего:

- title dashboard
- navigation links
- time range / refresh
- operator role dashboard
- drilldown behavior

то обнови минимум:

- `docs/03-guides/dashboards/README.md`
- `docs/03-guides/dashboards/monitoring-index.md`
- `docs/03-guides/dashboards/dashboard-v2-usage.md`
- `docs/05-operations/01-monitoring-guide.md`
- `grafana/README.md`

## 6. Verification protocol

Минимум:

```bash
uv run python -m json.tool grafana/dashboards/<dashboard>.json
uv run python -m pytest -q tests/integration/test_grafana_config.py
```

Если меняется observability navigation, дополнительно проверь реальный Grafana UI.

## 7. Definition of Done

- JSON валиден.
- Dashboard obeys current shipped navigation model.
- `No data` vs `0` выбрано сознательно, а не случайно.
- Contract tests проходят.
- Docs синхронизированы в том же PR/change set.
