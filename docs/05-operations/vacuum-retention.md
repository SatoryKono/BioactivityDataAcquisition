# VACUUM и Retention в BioETL

*Версия: 1.0 | Дата: 2026-01-01*

Руководство по управлению хранилищем Delta Lake: автоматизация VACUUM,
настройка retention, и рекомендации по scheduled maintenance.

---

## Обзор

BioETL использует Delta Lake для Silver и Gold слоёв. Delta Lake накапливает
версии данных для time travel, что требует периодической очистки старых файлов.

| Термин | Описание |
|--------|----------|
| **VACUUM** | Удаление файлов данных, которые больше не нужны для текущей версии таблицы |
| **Retention** | Минимальный возраст файлов для удаления (по умолчанию 7 дней) |
| **Time Travel** | Возможность запросить исторические версии данных |

---

## Автоматический VACUUM

### Pipeline-интегрированный VACUUM

VACUUM выполняется **автоматически** после каждого успешного pipeline run:

```
PipelineRunner.run()
    └── PostrunService.run_vacuum_if_enabled()
            └── RetentionManager.vacuum(retention_hours=168)
```

**Реализация:**
- `PostrunService` (`application/services/postrun_service.py:137-153`)
- `RetentionManager` (`infrastructure/storage/retention_manager.py:57-91`)

### Конфигурация

Автоматический VACUUM контролируется через `RuntimeConfig`:

```python
from bioetl.domain.config import RuntimeConfig

config = RuntimeConfig(
    vacuum_enabled=True,      # Включить автоматический VACUUM
    vacuum_retention_days=7,  # Файлы старше 7 дней удаляются
)
```

Или через переменные окружения:

```bash
export BIOETL_VACUUM_ENABLED=true
export BIOETL_VACUUM_RETENTION_DAYS=7
```

---

## Ручной VACUUM

### CLI команды

#### Одна таблица

```bash
# VACUUM с retention 7 дней (по умолчанию)
bioetl maintenance vacuum chembl.activity

# Указать retention
bioetl maintenance vacuum chembl.activity --retention-days 30

# Dry-run — показать что будет удалено
bioetl maintenance vacuum chembl.activity --dry-run
```

#### Все таблицы

```bash
# VACUUM всех таблиц
bioetl maintenance vacuum-all

# Только Silver слой
bioetl maintenance vacuum-all --layer silver

# Только Gold слой
bioetl maintenance vacuum-all --layer gold

# Dry-run для всех
bioetl maintenance vacuum-all --dry-run
```

### Опции

| Опция | Описание | По умолчанию |
|-------|----------|--------------|
| `--retention-days`, `-r` | Минимальный возраст файлов для удаления | 7 |
| `--dry-run` | Показать что будет удалено без удаления | False |
| `--layer` | Слой для vacuum-all: `all`, `silver`, `gold` | `all` |

---

## Scheduled VACUUM (Cron)

Для production рекомендуется настроить scheduled VACUUM через cron:

### Еженедельный VACUUM

```cron
# Каждое воскресенье в 02:00 UTC
0 2 * * 0 cd /path/to/bioetl && bioetl maintenance vacuum-all --retention-days 7 >> /var/log/bioetl/vacuum.log 2>&1
```

### Ежедневный VACUUM (высокая нагрузка)

```cron
# Каждый день в 03:00 UTC
0 3 * * * cd /path/to/bioetl && bioetl maintenance vacuum-all --retention-days 7 >> /var/log/bioetl/vacuum.log 2>&1
```

### Скрипт автоматизации

```bash
#!/bin/bash
# scripts/scheduled-vacuum.sh

set -euo pipefail

RETENTION_DAYS="${VACUUM_RETENTION_DAYS:-7}"
LOG_FILE="${VACUUM_LOG_FILE:-/var/log/bioetl/vacuum.log}"

echo "[$(date -Iseconds)] Starting scheduled vacuum" >> "$LOG_FILE"

cd "$(dirname "$0")/.."

if bioetl maintenance vacuum-all \
    --retention-days "$RETENTION_DAYS" \
    >> "$LOG_FILE" 2>&1; then
    echo "[$(date -Iseconds)] Vacuum completed successfully" >> "$LOG_FILE"
else
    echo "[$(date -Iseconds)] Vacuum failed with exit code $?" >> "$LOG_FILE"
    exit 1
fi
```

---

## Retention Policy

### Рекомендуемые значения

| Сценарий | Retention | Обоснование |
|----------|-----------|-------------|
| **Development** | 1 день | Минимум, экономия места |
| **Staging** | 7 дней | Баланс между отладкой и хранением |
| **Production** | 7-30 дней | Time travel для расследования инцидентов |
| **Compliance** | 30-90 дней | Требования аудита |

### Forensic Retention

Для критических таблиц можно настроить расширенный retention:

```yaml
# configs/runtime.yaml
vacuum:
  default_retention_days: 7
  forensic_tables:
    - chembl_activity
    - pubchem_compound
  forensic_retention_days: 30
```

---

## Мониторинг

### Логи

VACUUM операции логируются с structlog pattern:

```json
{
  "event": "vacuum_completed",
  "layer": "silver",
  "table": "chembl_activity",
  "files_removed": 42,
  "run_id": "abc123-..."
}
```

### Метрики Prometheus

| Метрика | Тип | Описание |
|---------|-----|----------|
| `vacuum_files_removed` | Counter | Количество удалённых файлов |
| `vacuum_duration_seconds` | Histogram | Время выполнения VACUUM |
| `vacuum_errors_total` | Counter | Ошибки VACUUM |

---

## Troubleshooting

### VACUUM не удаляет файлы

**Причина:** Файлы моложе retention period.

**Решение:** Уменьшить `--retention-days` или дождаться истечения периода.

### Ошибка "Table not found"

**Причина:** Таблица не существует или неправильное имя.

**Решение:** Проверить имя таблицы через `bioetl config list-pipelines`.

### VACUUM занимает много времени

**Причина:** Большое количество файлов для удаления.

**Решение:**
1. Запускать VACUUM чаще (ежедневно вместо еженедельно)
2. Использовать `--layer` для поэтапного vacuum

---

## Связанные ресурсы

- [ADR-002: Delta Lake Storage](../02-architecture/decisions/ADR-002-delta-lake-storage.md)
- [RULES.md §3.1: Medallion Architecture](../RULES.md)
- [VacuumService](../../src/bioetl/application/services/vacuum_service.py)
- [RetentionManager](../../src/bioetl/infrastructure/storage/retention_manager.py)
