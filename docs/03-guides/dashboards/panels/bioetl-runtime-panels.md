# BioETL Runtime - Panels Documentation

**Dashboard File:** `grafana/dashboards/bioetl-runtime.json`

## Обзор

Dashboard мониторит runtime метрики системы: память, CPU, GC, потоки.

## Ключевые панели

### 1. Memory Usage
- **Тип:** Graph
- **Назначение:** Использование памяти
- **Источники данных:** `process_resident_memory_bytes`
- **Описание:** RSS memory процесса

### 2. CPU Usage
- **Тип:** Graph
- **Назначение:** Использование CPU
- **Источники данных:** `process_cpu_seconds_total`
- **Описание:** CPU time процесса

### 3. GC Duration
- **Тип:** Graph
- **Назначение:** Время сборки мусора
- **Источники данных:** `python_gc_duration_seconds`
- **Фильтры:** `gc_gen` (0, 1, 2)

### 4. Thread Count
- **Тип:** Stat
- **Назначение:** Количество потоков
- **Источники данных:** `process_threads`

### 5. File Descriptors
- **Тип:** Stat
- **Назначение:** Количество открытых файловых дескрипторов
- **Источники данных:** `process_open_fds`

## Переменные Dashboard

- `instance` - Экземпляр процесса

## Примечания

- Dashboard использует стандартные Python Prometheus client метрики
- Важно для мониторинга ресурсных ограничений