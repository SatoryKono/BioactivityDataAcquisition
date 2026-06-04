# BioETL Silver Reject Explorer - Panels Documentation

**Dashboard File:** `grafana/dashboards/bioetl-silver-reject-explorer.json`

## Обзор

Dashboard обеспечивает детальный анализ отклонённых записей на слое Silver (Medallion Architecture).

## Ключевые панели

### 1. Silver Reject Rate
- **Тип:** Graph
- **Назначение:** Процент отклонённых записей
- **Источники данных:** `bioetl_silver_reject_rate`
- **Фильтры:** `pipeline_name`, `provider`

### 2. Reject Reasons Breakdown
- **Тип:** Pie Chart
- **Назначение:** Распределение причин отклонения
- **Источники данных:** `bioetl_silver_reject_by_reason`
- **Описание:** schema_violation, null_violation, duplicate, out_of_range

### 3. Rejects by Field
- **Тип:** Table
- **Назначение:** Отклонения по полям
- **Источники данных:** `bioetl_silver_rejects_by_field`
- **Фильтры:** `table_name`, `field_name`

### 4. Rejects Over Time
- **Тип:** Graph
- **Назначение:** Динамика отклонений во времени
- **Источники данных:** `bioetl_silver_rejects_total`
- **Фильтры:** `pipeline_name`

### 5. Quarantine from Silver
- **Тип:** Stat
- **Назначение:** Записи отправленные в карантин из Silver
- **Источники данных:** `bioetl_quarantine_from_silver_total`

## Переменные Dashboard

- `pipeline_name` - Выбор pipeline
- `provider` - Выбор провайдера
- `table_name` - Выбор таблицы Silver

## Примечания

- Dashboard отражает strict validation на слое Gold
- Использует Pandera data contracts для валидации