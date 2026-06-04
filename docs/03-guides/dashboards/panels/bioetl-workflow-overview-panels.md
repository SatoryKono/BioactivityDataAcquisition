# BioETL Workflow Overview - Panels Documentation

**Dashboard File:** `grafana/dashboards/bioetl-workflow-overview.json`

## Обзор

Dashboard обеспечивает обзор выполнения workflow и их компонентов.

## Ключевые панели

### 1. Workflow Execution Status
- **Тип:** Table
- **Назначение:** Статус выполнения workflow
- **Источники данных:** `bioetl_workflow_execution_status`
- **Фильтры:** `workflow_name`, `workflow_state`

### 2. Workflow Duration
- **Тип:** Graph
- **Назначение:** Время выполнения workflow
- **Источники данных:** `bioetl_workflow_duration_seconds`
- **Фильтры:** `workflow_name`

### 3. Workflow Success Rate
- **Тип:** Stat
- **Назначение:** Процент успешных выполнений workflow
- **Источники данных:** `bioetl_workflow_success_rate`
- **Пороги:** Green (>95), Yellow (90-95), Red (<90)

### 4. Active Workflows
- **Тип:** Stat
- **Назначение:** Количество активных workflow
- **Источники данных:** `bioetl_workflow_active_count`

## Переменные Dashboard

- `workflow_name` - Выбор workflow
- `time_range` - Временной диапазон

## Примечания

- Dashboard отражает состояние Workflow Control Plane (ADR-047)
- Интегрирован с RunManifest/RunLedger