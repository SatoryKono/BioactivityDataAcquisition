______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# VACUUM и Retention в BioETL

*Reference: [ADR-010](../02-architecture/decisions/ADR-010-local-only-deployment.md)*

> Runtime profile: Local-Only single-instance. Все примеры предполагают локальные Delta-таблицы и локальные планировщики задач.

Руководство по управлению хранилищем Delta Lake: автоматизация VACUUM,
настройка retention, и рекомендации по scheduled maintenance.

______________________________________________________________________

## Обзор

BioETL использует Delta Lake для Silver и Gold слоёв. Delta Lake накапливает
версии данных для time travel, что требует периодической очистки старых файлов.

| Термин          | Описание                                                                   |
| --------------- | -------------------------------------------------------------------------- |
| **VACUUM**      | Удаление файлов данных, которые больше не нужны для текущей версии таблицы |
| **Retention**   | Минимальный возраст файлов для удаления (по умолчанию 7 дней)              |
| **Time Travel** | Возможность запросить исторические версии данных                           |

______________________________________________________________________

## Автоматический VACUUM

### Pipeline-интегрированный VACUUM

Pipeline-integrated VACUUM **поддерживается, но выключен по умолчанию**.
Он выполняется только если включён через YAML (`maintenance.auto_vacuum: true`)
или через CLI `--vacuum-after-run` для конкретного запуска:

```
PipelineRunner.run()
    └── PostrunService.run()
            └── MedallionLifecycleService.finalize_run()
                    └── StoragePort.optimize(...)
```

**Реализация:**

- `PostrunService` (`application/core/postrun/service.py`)
- `MedallionLifecycleService.finalize_run()` (`application/services/medallion_lifecycle.py`)
- YAML defaults: `configs/base/pipeline.yaml` (`maintenance.auto_vacuum: false`)

### Конфигурация

Автоматический VACUUM контролируется через `RuntimeConfig`:

```python
from bioetl.domain.config import RuntimeConfig

config = RuntimeConfig(
    vacuum_after_run=False,  # Default: VACUUM after run disabled
    vacuum_retention_days=7,  # Файлы старше 7 дней удаляются
)
```

Чтобы включить VACUUM после успешного запуска, нужно явно задать
`vacuum_after_run=True`, включить `maintenance.auto_vacuum: true` в YAML
или передать CLI-флаг `--vacuum-after-run`. Retention настраивается через
`vacuum_retention_days` / `--vacuum-retention-days`.

______________________________________________________________________

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

| Опция                    | Описание                                     | По умолчанию |
| ------------------------ | -------------------------------------------- | ------------ |
| `--retention-days`, `-r` | Минимальный возраст файлов для удаления      | 7            |
| `--dry-run`              | Показать что будет удалено без удаления      | False        |
| `--layer`                | Слой для vacuum-all: `all`, `silver`, `gold` | `all`        |

______________________________________________________________________

## Scheduled VACUUM (Cron)

Для long-running local или production-like профиля рекомендуется настроить
scheduled VACUUM через cron:

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

### Скрипт автоматизации (пример)

```bash
#!/bin/bash
# Example operator wrapper (not shipped). Prefer repo entrypoint:
#   python -m scripts.ops.data.vacuum_delta --help
# or schedule a thin host cron that invokes that module.

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

______________________________________________________________________

## Retention Policy

### Рекомендуемые значения

| Сценарий                          | Retention  | Обоснование                              |
| --------------------------------- | ---------- | ---------------------------------------- |
| **Development**                   | 1 день     | Минимум, экономия места                  |
| **Staging-like local profile**    | 7 дней     | Баланс между отладкой и хранением        |
| **Production-like local profile** | 7-30 дней  | Time travel для расследования инцидентов |
| **Compliance**                    | 30-90 дней | Требования аудита                        |

### Forensic Retention

Для критических таблиц используйте отдельный cron-профиль/команду с большим
`--retention-days` (например, `30`) вместо глобального значения.

______________________________________________________________________

## Мониторинг

### Логи

VACUUM операции логируются с structlog pattern:

```json
{
  "event": "vacuum_completed",
  "layer": "silver",
  "table": "chembl_activity",
  "files-removed": 42,
  "run-id": "abc123-..."
}
```

### Метрики Prometheus

| Метрика                                    | Тип     | Описание                          |
| ------------------------------------------ | ------- | --------------------------------- |
| `bioetl_vacuum_files_removed_total`        | Counter | Количество удалённых файлов       |
| `bioetl_errors_total` (label `error_code`) | Counter | Ошибки выполнения, включая VACUUM |

Длительность VACUUM не публикуется как отдельная public Prometheus family.
Для operator triage используйте структурированные логи `vacuum_completed` и
postrun/runtime tracing вместо legacy histogram selector.

______________________________________________________________________

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
1. Использовать `--layer` для поэтапного vacuum

______________________________________________________________________

## Связанные ресурсы

- [ADR-001: Delta Lake vs Parquet](../02-architecture/decisions/ADR-001-delta-lake-vs-parquet.md)
- [ADR-002: Medallion Architecture](../02-architecture/decisions/ADR-002-medallion-architecture.md)
- [RULES.md §3.1: Medallion Architecture](../00-project/RULES.md)
- [VacuumService](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/src/bioetl/application/services/vacuum_service.py)
- [RetentionPolicy](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/src/bioetl/infrastructure/storage/support/retention.py)
