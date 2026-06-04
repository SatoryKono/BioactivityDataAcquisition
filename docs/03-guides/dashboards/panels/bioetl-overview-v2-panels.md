# BioETL Overview v2 - Panels Documentation

**Dashboard File:** `grafana/dashboards/bioetl-overview-v2.json`

## Обзор

Dashboard обеспечивает комплексный обзор состояния BioETL системы, включая pipeline запуски, производительность и качество данных.

## Панели

### 1. Pipeline Runs Overview
- **Тип:** Stat / Timeseries
- **Назначение:** Обзор количества pipeline запусков по состояниям
- **Источники данных:** `bioetl_pipeline_run_total{status="..."}`
- **Фильтры:** `pipeline_name`, `provider`, `time_range`
- **Описание:** Показывает распределение pipeline запусков по статусам (PENDING, RUNNING, COMPLETED, FAILED, SHUTDOWN)

### 2. Pipeline Duration
- **Тип:** Graph
- **Назначение:** Время выполнения pipeline
- **Источники данных:** `bioetl_pipeline_run_duration_seconds`
- **Фильтры:** `pipeline_name`, `provider`
- **Описание:** Гистограмма времени выполнения pipeline, разбитая по квантилям (p50, p95, p99)

### 3. Records Processed
- **Тип:** Stat
- **Назначение:** Общее количество обработанных записей
- **Источники данных:** `bioetl_records_processed_total`
- **Фильтры:** `pipeline_name`, `provider`, `stage`
- **Описание:** Суммарное количество записей, обработанных за выбранный период

### 4. Data Quality Score
- **Тип:** Gauge
- **Назначение:** Общий показатель качества данных
- **Источники данных:** `bioetl_dq_score`
- **Фильтры:** `pipeline_name`, `provider`
- **Пороги:** Green (>90), Yellow (70-90), Red (<70)
- **Описание:** Агрегированный показатель качества данных на основе DQ проверок

### 5. Provider Health
- **Тип:** Table
- **Назначение:** Состояние провайдеров данных
- **Источники данных:** `bioetl_provider_success_rate`, `bioetl_provider_latency_seconds`
- **Фильтры:** `provider`
- **Описание:** Таблица с показателями успеха и задержки для каждого провайдера

### 6. Error Rate
- **Тип:** Graph
- **Назначение:** Частота ошибок
- **Источники данных:** `bioetl_errors_total`
- **Фильтры:** `pipeline_name`, `provider`, `error_type`
- **Описание:** График количества ошибок во времени

### 7. Quarantine Rate
- **Тип:** Stat
- **Назначение:** Процент записей в карантине
- **Источники данных:** `bioetl_quarantine_rate`
- **Фильтры:** `pipeline_name`, `provider`
- **Описание:** Процент записей, отправленных в карантин из-за проблем с качеством

### 8. Active Batches
- **Тип:** Stat
- **Назначение:** Количество активных батчей
- **Источники данных:** `bioetl_batch_active`
- **Фильтры:** `status`
- **Описание:** Текущее количество батчей в каждом состоянии (OPEN, SEALED, WRITING)

## Переменные Dashboard

- `pipeline_name` - Выбор pipeline для фильтрации
- `provider` - Выбор провайдера данных
- `time_range` - Временной диапазон (1h, 6h, 24h, 7d)
- `environment` - Окружение (local, dev, prod)

## Примечания

- Dashboard использует aggregation по времени для улучшения производительности
- Данные обновляются каждые 15 секунд
- Для детального анализа используйте специализированные dashboards (DQ, Provider Health, etc.)