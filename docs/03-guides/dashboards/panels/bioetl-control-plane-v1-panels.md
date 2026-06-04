# BioETL Control Plane v1 - Panels Documentation

**Dashboard File:** `grafana/dashboards/bioetl-control-plane-v1.json`

## Обзор

Dashboard мониторит Control Plane артефакты: RunManifest, RunLedger, WorkflowManifest, WorkflowLedger.

## Ключевые панели

### 1. Active Runs
- **Тип:** Stat
- **Назначение:** Количество активных pipeline запусков
- **Источники данных:** `bioetl_control_plane_active_runs`
- **Фильтры:** `run_state`

### 2. RunManifest Operations
- **Тип:** Graph
- **Назначение:** Операции над RunManifest
- **Источники данных:** `bioetl_run_manifest_operations_total`
- **Фильтры:** `operation_type` (create, update, seal)

### 3. Ledger Write Operations
- **Тип:** Graph
- **Назначение:** Операции записи в RunLedger
- **Источники данных:** `bioetl_ledger_write_duration_seconds`
- **Описание:** Время записи событий в ledger

### 4. Workflow Execution Status
- **Тип:** Table
- **Назначение:** Статус выполнения workflow
- **Источники данных:** `bioetl_workflow_status`
- **Фильтры:** `workflow_name`, `workflow_state`

### 5. Checkpoint Operations
- **Тип:** Graph
- **Назначение:** Операции checkpoint
- **Источники данных:** `bioetl_checkpoint_operations_total`
- **Фильтры:** `checkpoint_type`, `operation`

## Переменные Dashboard

- `workflow_name` - Выбор workflow
- `run_id` - Идентификатор запуска
- `time_range` - Временной диапазон

## Примечания

- Dashboard отражает состояние Control Plane согласно ADR-047
- Отображает детерминизм и replay возможности