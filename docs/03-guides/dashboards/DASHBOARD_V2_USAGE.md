# BioETL Dashboards v2: Usage

Дата сверки: **2026-02-24**  
Источник истины: `grafana/dashboards/*.json`

## Какие дашборды использовать

| Dashboard | UID | Для чего |
|---|---|---|
| Data Quality v2 | `bioetl-dq-v2` | Качество данных, карантин, аномалии, freshness |
| Overview v2 | `bioetl-overview-v2` | Общее состояние пайплайна по стадиям |
| Provider Health v2 | `bioetl-provider-health-v2` | Latency/успехи health-check провайдеров |
| Simple | `bioetl-simple` | Быстрый срез bronze/silver/gold + quality ratio |

## Фильтрация

- `bioetl-simple`, `bioetl-overview-v2`, `bioetl-dq-v2`: `$pipeline`, `$run_type`
- `bioetl-provider-health-v2`: `$pipeline`, `$provider`
- Переменные `$run_id` и `execution` не используются.

## Что смотреть в первую очередь

1. `bioetl-overview-v2`, panel `id=4`:
`sum(gold) / clamp_min(sum(bronze), 1)`
2. `bioetl-dq-v2`, panel `id=2`:
`(gold + quarantined) / clamp_min(bronze, 1)`
3. `bioetl-dq-v2`, panel `id=6`, `id=7`, `id=12`:
рост quarantine/threshold/failures за 24h.
4. `bioetl-provider-health-v2`, panel `id=1`, `id=102`, `id=103`:
p95 latency по провайдерам.

## Важные пороги (из JSON)

- `simple.id=4`: red `<0.8`, orange `>=0.8`, green `>=0.95`
- `overview.id=4`: red `<0.8`, yellow `>=0.8`, green `>=0.9`
- `dq.id=5`: red `<0.8`, yellow `>=0.8`, green `>=0.9`
- `dq.id=8`: yellow `>=3600s`, red `>=21600s`
- `provider.id=103`: yellow `>=1ms`, orange `>=2ms`, red `>=5ms`
- `provider.id=102`: yellow `>=100ms`, orange `>=500ms`, red `>=1000ms`

## Частые проблемы

1. `No data`:
проверьте `http://localhost:8000/metrics`, затем `http://localhost:9090/targets`.
2. Пустой `$provider`:
нет серии `bioetl_health_check_latency_ms_bucket` в metrics endpoint.
3. Пустой `$run_type`:
нет метрик `bioetl_records_processed_total` для выбранного `$pipeline`.

