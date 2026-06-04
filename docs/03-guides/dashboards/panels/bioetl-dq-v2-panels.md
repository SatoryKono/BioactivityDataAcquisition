# BioETL Data Quality v2 - Panels Documentation

**Dashboard File:** `grafana/dashboards/bioetl-dq-v2.json`

## Обзор

Dashboard обеспечивает детальный мониторинг качества данных (DQ) для всех pipelines.

## Ключевые панели

### 1. Overall DQ Score
- **Тип:** Gauge
- **Назначение:** Агрегированный показатель качества данных
- **Источники данных:** `bioetl_dq_score`
- **Пороги:** Green (>90), Yellow (70-90), Red (<70)

### 2. DQ Rule Pass Rate
- **Тип:** Graph
- **Назначение:** Процент прохождения DQ правил
- **Источники данных:** `bioetl_dq_rule_pass_rate`
- **Фильтры:** `rule_name`, `pipeline_name`

### 3. Quarantine by Reason
- **Тип:** Pie Chart
- **Назначение:** Распределение карантинных записей по причинам
- **Источники данных:** `bioetl_quarantine_by_reason`

### 4. Silver Reject Rate
- **Тип:** Graph
- **Назначение:** Процент отклонённых записей на слое Silver
- **Источники данных:** `bioetl_silver_reject_rate`

### 5. Validation Errors
- **Тип:** Table
- **Назначение:** Детали ошибок валидации
- **Источники данных:** `bioetl_validation_errors_total`
- **Фильтры:** `error_code`, `field_name`

## Переменные Dashboard

- `pipeline_name` - Выбор pipeline
- `provider` - Выбор провайдера
- `rule_type` - Тип DQ правила (schema, value, cross)

## Примечания

- Dashboard отражает состояние DQ фреймворка Pandera
- Использует composite validation для cross-field проверок