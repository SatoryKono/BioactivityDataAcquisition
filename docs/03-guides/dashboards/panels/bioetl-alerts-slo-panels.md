# BioETL Alerts SLO - Panels Documentation

**Dashboard File:** `grafana/dashboards/bioetl-alerts-slo.json`

## Обзор

Dashboard мониторит SLO (Service Level Objectives) и alerting правила для BioETL.

## Ключевые панели

### 1. Pipeline Success SLO
- **Тип:** Gauge
- **Назначение:** SLO успешного выполнения pipeline
- **Источники данных:** `bioetl_slo_pipeline_success`
- **Пороги:** Green (>99%), Yellow (95-99%), Red (<95%)

### 2. Data Freshness SLO
- **Тип:** Graph
- **Назначение:** SLO свежести данных
- **Источники данных:** `bioetl_slo_data_freshness_seconds`
- **Описание:** Время между доступностью данных и обработкой

### 3. Error Budget
- **Тип:** Stat
- **Назначение:** Error budget для SLO
- **Источники данных:** `bioetl_error_budget_remaining`
- **Описание:** Оставшийся error budget в процентах

### 4. Alert Fire Rate
- **Тип:** Graph
- **Назначение:** Частота срабатывания алертов
- **Источники данных:** `bioetl_alerts_fired_total`
- **Фильтры:** `alert_name`, `severity`

### 5. Alert Resolution Time
- **Тип:** Graph
- **Назначение:** Время разрешения алертов
- **Источники данных:** `bioetl_alert_resolution_duration_seconds`
- **Фильтры:** `alert_name`

## Переменные Dashboard

- `slo_type` - Тип SLO (pipeline_success, data_freshness, availability)
- `severity` - Уровень серьезности (critical, warning, info)

## Примечания

- Dashboard использует Prometheus alerting rules из `grafana/prometheus-rules/`
- SLO конфигурируются согласно операционным требованиям