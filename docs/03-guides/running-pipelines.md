# Running Pipelines

Руководство по запуску и управлению ETL-пайплайнами в BioETL.

**Версия:** 5.9.0
**Дата обновления:** 2026-01-26

---

## Prerequisites

1. **Virtual environment активирован:**
   ```bash
   # Linux/macOS
   source .venv/bin/activate

   # Windows
   .venv\Scripts\activate
   ```

2. **Environment настроен** (`.env` файл или переменные окружения)

3. **Зависимости установлены:**
   ```bash
   make install   # или: pip install -e ".[dev]"
   ```

> **Note:** BioETL использует **Local-Only** архитектуру (ADR-010).
> Docker и внешние сервисы (Redis, MinIO) **не требуются**.

---

## Быстрый старт

```bash
# Список доступных пайплайнов
python -m bioetl.main config list-pipelines

# Запуск пайплайна с ограничением (для тестирования)
python -m bioetl.main run --pipeline chembl_activity --limit 100

# Запуск полного пайплайна
python -m bioetl.main run --pipeline chembl_activity
```

---

## Типы запуска (Run Types)

| Тип | Флаг | Описание | Очистка данных |
|-----|------|----------|----------------|
| **Incremental** | (по умолчанию) | Обработка новых записей с последнего checkpoint | Нет |
| **Backfill** | `--run-type backfill` | Обработка записей для заполнения пробелов | Silver/Gold |
| **Rebuild** | `--run-type rebuild` | Полная перезагрузка всех данных | Bronze/Silver/Gold |

### Incremental Run

Обрабатывает только новые записи с момента последнего успешного запуска:

```bash
python -m bioetl.main run --pipeline chembl_activity
```

### Backfill Run

Заполняет пробелы в данных. Требует подтверждения (очищает Silver/Gold):

```bash
# С подтверждением
python -m bioetl.main run --pipeline chembl_activity --run-type backfill

# Без подтверждения
python -m bioetl.main run --pipeline chembl_activity --run-type backfill --yes

# Предпросмотр очистки
python -m bioetl.main run --pipeline chembl_activity --run-type backfill --dry-run
```

### Full Rebuild

Полная перезагрузка данных. Очищает все слои (Bronze/Silver/Gold):

```bash
# С подтверждением
python -m bioetl.main run --pipeline chembl_activity --run-type rebuild

# Без подтверждения
python -m bioetl.main run --pipeline chembl_activity --run-type rebuild --yes

# Предпросмотр очистки
python -m bioetl.main run --pipeline chembl_activity --run-type rebuild --dry-run
```

---

## Тестирование и разработка

### Ограничение количества записей

Для тестирования ограничьте количество обрабатываемых записей:

```bash
python -m bioetl.main run --pipeline chembl_activity --limit 100
```

### Resume (продолжение прерванного запуска)

Если пайплайн был прерван, продолжите с checkpoint:

```bash
python -m bioetl.main run --pipeline chembl_activity --resume
```

### Debug логирование

```bash
python -m bioetl.main run --pipeline chembl_activity --debug
```

### Bronze Cache (use_cached_bronze)

BioETL поддерживает запуск пайплайнов на основе локального кеша Bronze-слоя вместо выполнения HTTP-запросов к API. Это полезно для быстрой отладки трансформаций и тестирования DQ-правил на ранее загруженных данных.

> **Note:** С версии 5.9.0 опция `--use-cached-bronze` **включена по умолчанию**. 
> Пайплайн сначала ищет данные в `data/output/bronze/{provider}/{entity}`.

```bash
# Использовать кеш (по умолчанию)
python -m bioetl.main run --pipeline chembl_activity

# Принудительно запросить свежие данные из API
python -m bioetl.main run --pipeline chembl_activity --no-cached-bronze

# Фильтрация кеша по дате
python -m bioetl.main run --pipeline chembl_activity --cached-bronze-date 2026-01-20

# Указание кастомного пути к кешу
python -m bioetl.main run --pipeline chembl_activity --cached-bronze-path ./my_cache
```

### Фильтрация по CSV

Обрабатывать только записи с указанными ID:

```bash
python -m bioetl.main run --pipeline chembl_activity \
    --input-csv data/filter_ids.csv \
    --filter-column molecule_id \
    --filter-field molecule_chembl_id
```

---

## Конфигурация пайплайнов

Все пайплайны настраиваются через **YAML-файлы** в `configs/pipelines/`:

```
configs/
├── pipelines/
│   ├── _base.yaml           # Базовая конфигурация (наследуется)
│   ├── chembl/
│   │   ├── activity.yaml
│   │   ├── molecule.yaml
│   │   └── ...
│   ├── pubchem/
│   │   └── compound.yaml
│   └── ...
├── dq/                       # Data Quality правила
└── filter/                   # Фильтры данных
```

### Просмотр конфигурации

```bash
# Показать конфигурацию пайплайна
python -m bioetl.main config show chembl_activity

# В формате JSON
python -m bioetl.main config show chembl_activity --format json

# Валидация конфигурации
python -m bioetl.main config validate chembl_activity
```

### Структура YAML-конфига

Минимальный конфиг (наследует из `_base.yaml`):

```yaml
pipeline_name: chembl_activity
provider: chembl
entity_type: activity
version: "1.2.0"
primary_keys: ["activity_id"]
silver_table: "chembl_activity"
gold_table: "chembl_activity"

# Переопределения DQ правил (опционально)
dq_rules:
  field_validations:
    - field: standard_value
      type: range
      min: 0
      nullable: true
```

> **Подробнее:** [Pipeline Configuration Guide](pipeline-configuration.md)

---

## Блокировки (Locking)

BioETL использует **in-memory блокировки** для предотвращения concurrent writes.

> **Архитектура:** In-memory locks достаточны для Local-Only deployment (ADR-010).
> Redis **не требуется**.

### Проверка статуса блокировки

```bash
python -m bioetl.main lock check --pipeline chembl_activity --run-id <UUID>
```

### Освобождение зависшей блокировки

Если пайплайн завершился аварийно и не освободил блокировку:

```bash
python -m bioetl.main lock release --pipeline chembl_activity --run-id <UUID>
```

> **Внимание:** Используйте только если уверены, что пайплайн не выполняется.

### TTL и Heartbeat

- **Default TTL:** 90 секунд
- **Heartbeat interval:** 30 секунд (автоматически продлевает блокировку)
- При аварийном завершении блокировка автоматически освобождается по истечении TTL

---

## Мониторинг и метрики

### Log Levels

```bash
# Via флаг
python -m bioetl.main run --pipeline chembl_activity --debug

# Via переменную окружения
export BIOETL_LOG_LEVEL=DEBUG
python -m bioetl.main run --pipeline chembl_activity
```

| Уровень | Использование |
|---------|---------------|
| `DEBUG` | Разработка, troubleshooting |
| `INFO` | Production (default) |
| `WARNING` | Только предупреждения |
| `ERROR` | Только ошибки |

### Prometheus Metrics

BioETL автоматически собирает метрики выполнения:

```bash
# Метрики доступны на порту 8000
curl http://localhost:8000/metrics | grep bioetl_
```

**Ключевые метрики:**

| Метрика | Тип | Описание |
|---------|-----|----------|
| `bioetl_pipeline_duration_seconds` | Histogram | Длительность выполнения пайплайна |
| `bioetl_records_processed_total` | Counter | Количество обработанных записей |
| `bioetl_errors_total` | Counter | Количество ошибок |
| `bioetl_batch_size_records` | Histogram | Размер батчей |
| `bioetl_dq_records_quarantined_total` | Counter | Карантинные записи |
| `bioetl_circuit_breaker_state` | Gauge | Состояние Circuit Breaker |

**Включение/отключение метрик:**

```bash
# Включить (по умолчанию)
export BIOETL_METRICS_ENABLED=true

# Отключить
export BIOETL_METRICS_ENABLED=false
```

> **Подробнее:** [Metrics & Monitoring Guide](metrics-monitoring.md)

### Health Server

При выполнении пайплайна доступен HTTP health server:

```bash
# Включён по умолчанию на порту 8080
python -m bioetl.main run --pipeline chembl_activity --health-port 8080

# Отключить
python -m bioetl.main run --pipeline chembl_activity --no-health-server
```

**Endpoints:**
- `GET /health` — общий статус
- `GET /health/live` — liveness probe
- `GET /health/ready` — readiness probe

### Standalone Health Server

```bash
python -m bioetl.main health server --port 8080
```

---

## Выходные данные (Pipeline Output)

Пайплайны записывают данные в три слоя (Medallion Architecture):

| Слой | Путь | Формат | Retention |
|------|------|--------|-----------|
| **Bronze** | `data/bronze/{provider}/{entity}/{date}/` | JSONL + zstd | 90 дней |
| **Silver** | `data/silver/{provider}/{entity}/` | Delta Lake | Permanent |
| **Gold** | `data/gold/{provider}/{entity}/` | Delta Lake / Parquet | Permanent |

### Структура директорий

```
data/
├── bronze/
│   └── chembl/activity/2026-01-26/
│       └── batch_001.jsonl.zst
├── silver/
│   └── chembl/activity/
│       └── _delta_log/
├── gold/
│   └── chembl/activity/
│       └── _delta_log/
├── checkpoints/
│   └── chembl_activity.json
└── quarantine/
    └── chembl/activity/
```

### Экспорт данных

```bash
# Список доступных таблиц
python -m bioetl.main export --list

# Экспорт в CSV
python -m bioetl.main export chembl.activity

# Экспорт в Excel
python -m bioetl.main export chembl.activity --format xlsx

# Экспорт Gold слоя
python -m bioetl.main export chembl.activity --layer gold
```

---

## Maintenance операции

### VACUUM (очистка старых версий)

```bash
# VACUUM одной таблицы
python -m bioetl.main maintenance vacuum chembl.activity

# VACUUM всех таблиц
python -m bioetl.main maintenance vacuum-all

# С кастомным retention
python -m bioetl.main maintenance vacuum-all --retention-days 30

# Предпросмотр
python -m bioetl.main maintenance vacuum-all --dry-run
```

### Bronze Cleanup

Удаление старых Bronze файлов (по умолчанию >90 дней):

```bash
python -m bioetl.main maintenance bronze-cleanup
python -m bioetl.main maintenance bronze-cleanup --retention-days 60 --dry-run
```

---

## Карантин (Quarantine)

Записи, не прошедшие валидацию, помещаются в карантин для анализа.

### Просмотр карантина

```bash
# Статистика
python -m bioetl.main quarantine stats --pipeline chembl_activity

# Просмотр записей
python -m bioetl.main quarantine inspect --pipeline chembl_activity --limit 50

# Фильтрация по коду ошибки
python -m bioetl.main quarantine inspect --pipeline chembl_activity --error-code DQ_MISSING_FIELD
```

### Повторная обработка

```bash
python -m bioetl.main quarantine replay --pipeline chembl_activity --dry-run
python -m bioetl.main quarantine replay --pipeline chembl_activity --max-age-days 7
```

### Очистка карантина

```bash
python -m bioetl.main quarantine purge --pipeline chembl_activity --older-than-days 30 --dry-run
```

---

## Распространённые проблемы

| Проблема | Решение |
|----------|---------|
| Lock acquisition failed | Подождите или освободите зависшую блокировку |
| Rate limit (429) | Автоматический retry с backoff |
| Schema drift detected | Проверьте логи, review новых полей |
| Checkpoint not found | Запустите без `--resume` |
| DQ threshold exceeded | Проверьте `quarantine stats`, исправьте источник |
| Circuit breaker open | Подождите recovery (5 мин) или проверьте health провайдера |

---

## Запуск нескольких пайплайнов

### Все пайплайны провайдера

```bash
# Список пайплайнов
python -m bioetl.main run-all --source chembl --list-only

# Запуск всех
python -m bioetl.main run-all --source chembl

# С ограничением
python -m bioetl.main run-all --source chembl --limit 100
```

### Композитные пайплайны

Для сущностей с обогащением из нескольких источников (например, publications):

```bash
python -m bioetl.main run-composite --composite publication
python -m bioetl.main run-composite --composite publication --seed-limit 100
```

---

## См. также

- [CLI Reference](../04-reference/cli.md) — полная документация CLI
- [Pipeline Configuration](pipeline-configuration.md) — настройка конфигураций
- [Metrics & Monitoring](metrics-monitoring.md) — метрики и мониторинг
- [Troubleshooting](troubleshooting.md) — решение проблем
- [Getting Started](getting-started.md) — начало работы
