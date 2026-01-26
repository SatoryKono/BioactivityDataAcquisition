# CLI Reference

BioETL command-line interface (CLI) - основной способ взаимодействия с системой.
Построен на фреймворке **Click** для стабильности и расширяемости.

**Версия:** 5.9.0
**Дата обновления:** 2026-01-26

---

## Запуск CLI

```bash
# Рекомендуемый способ
python -m bioetl.main <command> [options]

# Или через активированное venv
bioetl <command> [options]
```

Для справки по любой команде добавьте `--help`:

```bash
python -m bioetl.main --help
python -m bioetl.main run --help
```

---

## Команды

### `run` — Запуск одного пайплайна

Выполняет ETL-пайплайн для указанной сущности.

**Синтаксис:**
```bash
python -m bioetl.main run --pipeline <NAME> [OPTIONS]
```

**Обязательные параметры:**

| Параметр | Описание |
|----------|----------|
| `--pipeline <NAME>` | Имя пайплайна (соответствует YAML в `configs/pipelines/`) |

**Опции:**

| Опция | Тип | По умолчанию | Описание |
|-------|-----|--------------|----------|
| `--run-type` | choice | `incremental` | Тип запуска: `incremental`, `backfill`, `rebuild` |
| `--limit` | int | None | Максимальное количество записей |
| `--resume` | flag | False | Продолжить с последнего checkpoint |
| `--dry-run` | flag | False | Предпросмотр без записи данных |
| `--yes`, `-y` | flag | False | Пропустить подтверждение для rebuild/backfill |
| `--input-csv` | path | None | Путь к CSV с ID для фильтрации |
| `--filter-column` | str | `id` | Имя колонки в CSV с ID |
| `--filter-field` | str | varies | Поле API для фильтрации |
| `--vacuum-after-run` | flag | None | Запустить VACUUM после успешного выполнения |
| `--vacuum-retention-days` | int | 7 | Retention для VACUUM (дней) |
| `--debug` | flag | False | Включить DEBUG логирование |
| `--health-server/--no-health-server` | flag | True | Включить HTTP health server |
| `--health-port` | int | 8080 | Порт для health server |

**Примеры:**

```bash
# Инкрементальный запуск (по умолчанию)
python -m bioetl.main run --pipeline chembl_activity

# С ограничением записей (для тестирования)
python -m bioetl.main run --pipeline chembl_activity --limit 100

# Полная перезагрузка данных
python -m bioetl.main run --pipeline chembl_activity --run-type rebuild --yes

# Предпросмотр очистки без выполнения
python -m bioetl.main run --pipeline chembl_activity --run-type rebuild --dry-run

# Продолжить прерванный запуск
python -m bioetl.main run --pipeline chembl_activity --resume

# С фильтрацией по CSV
python -m bioetl.main run --pipeline chembl_activity \
    --input-csv data/filter_ids.csv \
    --filter-column molecule_id \
    --filter-field molecule_chembl_id

# С DEBUG логированием
python -m bioetl.main run --pipeline chembl_activity --debug
```

**Типы запуска:**

| Тип | Описание | Очистка данных |
|-----|----------|----------------|
| `incremental` | Обработка новых записей с последнего checkpoint | Нет |
| `backfill` | Обработка определённого диапазона | Silver/Gold |
| `rebuild` | Полная перезагрузка всех данных | Bronze/Silver/Gold |

**Exit Codes:**

| Код | Значение |
|-----|----------|
| 0 | Успешное выполнение |
| 82 | Ошибка выполнения пайплайна |
| 83 | Превышен порог Data Quality |
| 84 | Ошибка захвата блокировки |
| 86 | Сетевая ошибка |
| 130 | Прервано (Ctrl+C) |

---

### `run-all` — Запуск всех пайплайнов провайдера

Последовательно выполняет все пайплайны для указанного провайдера.

**Синтаксис:**
```bash
python -m bioetl.main run-all --source <PROVIDER> [OPTIONS]
```

**Опции:**

| Опция | Тип | По умолчанию | Описание |
|-------|-----|--------------|----------|
| `--source` | str | Required | Имя провайдера (chembl, pubchem, uniprot и др.) |
| `--run-type` | choice | `incremental` | Тип запуска |
| `--limit` | int | None | Лимит записей для каждого пайплайна |
| `--dry-run` | flag | False | Показать пайплайны без выполнения |
| `--yes`, `-y` | flag | False | Пропустить подтверждение |
| `--list-only` | flag | False | Только показать список пайплайнов |
| `--debug` | flag | False | DEBUG логирование |

**Примеры:**

```bash
# Запуск всех ChEMBL пайплайнов
python -m bioetl.main run-all --source chembl

# Только просмотр списка
python -m bioetl.main run-all --source chembl --list-only

# Предпросмотр
python -m bioetl.main run-all --source pubchem --dry-run

# Rebuild всех пайплайнов провайдера
python -m bioetl.main run-all --source chembl --run-type rebuild --yes
```

---

### `run-composite` — Запуск композитных пайплайнов

Выполняет композитный пайплайн (seed + enrichers) согласно ADR-026.

**Синтаксис:**
```bash
python -m bioetl.main run-composite --composite <NAME> [OPTIONS]
```

**Опции:**

| Опция | Тип | По умолчанию | Описание |
|-------|-----|--------------|----------|
| `--composite` | str | Required | Имя композитного пайплайна |
| `--resume` | flag | False | Продолжить с checkpoint |
| `--dry-run` | flag | False | Предпросмотр без записи |
| `--seed-limit` | int | None | Лимит записей для seed пайплайна |
| `--enrich-only` | str | None | Запустить только указанные enrichers (через запятую) |
| `--required-only` | flag | False | Пропустить опциональные enrichers |
| `--force-enricher` | str | None | Принудительный перезапуск enricher |
| `--debug` | flag | False | DEBUG логирование |

**Примеры:**

```bash
# Запуск композитного пайплайна публикаций
python -m bioetl.main run-composite --composite publication

# С ограничением seed
python -m bioetl.main run-composite --composite publication --seed-limit 100

# Только определённые enrichers
python -m bioetl.main run-composite --composite publication --enrich-only crossref,openalex

# Только обязательные enrichers
python -m bioetl.main run-composite --composite publication --required-only
```

---

### `export` — Экспорт данных

Экспортирует Delta-таблицы Silver/Gold в CSV, XLSX или TSV.

**Синтаксис:**
```bash
python -m bioetl.main export [TABLE] [OPTIONS]
```

**Аргументы:**

| Аргумент | Описание |
|----------|----------|
| `TABLE` | Имя таблицы в формате `provider.entity` (опционально при `--list`) |

**Опции:**

| Опция | Тип | По умолчанию | Описание |
|-------|-----|--------------|----------|
| `--list` | flag | False | Показать все доступные таблицы |
| `--preview` | flag | False | Показать схему и sample данных |
| `--format`, `-f` | choice | `csv` | Формат: `csv`, `xlsx`, `tsv` |
| `--layer`, `-l` | choice | `silver` | Слой: `silver`, `gold` |
| `--output`, `-o` | path | `data/exports` | Директория для экспорта |
| `--limit` | int | None | Максимальное количество строк |
| `--columns`, `-c` | str | None | Колонки для экспорта (через запятую) |

**Примеры:**

```bash
# Список всех таблиц
python -m bioetl.main export --list

# Предпросмотр таблицы
python -m bioetl.main export chembl.activity --preview

# Экспорт в CSV (по умолчанию)
python -m bioetl.main export chembl.activity

# Экспорт в Excel
python -m bioetl.main export chembl.activity --format xlsx

# С ограничением строк и колонок
python -m bioetl.main export chembl.activity --limit 10000 --columns id,name,value

# Экспорт Gold-слоя
python -m bioetl.main export chembl.activity --layer gold

# В указанную директорию
python -m bioetl.main export chembl.activity -o ./my_exports
```

---

### `config` — Управление конфигурацией

Просмотр и валидация конфигурации пайплайнов.

#### `config show` — Показать конфигурацию пайплайна

```bash
python -m bioetl.main config show <PIPELINE> [--format yaml|json]
```

**Примеры:**
```bash
python -m bioetl.main config show chembl_activity
python -m bioetl.main config show chembl_activity --format json
```

#### `config validate` — Валидация конфигурации

```bash
python -m bioetl.main config validate <PIPELINE>
```

Выводит: Provider, Entity type, Silver table, Gold table (если есть).

#### `config show-settings` — Глобальные настройки

```bash
python -m bioetl.main config show-settings [--format yaml|json]
```

Показывает все `BIOETL_*` переменные окружения (API-ключи маскируются).

#### `config list-pipelines` — Список пайплайнов

```bash
python -m bioetl.main config list-pipelines
```

---

### `quarantine` — Управление карантином

Dashboard для работы с проблемными записями.

#### `quarantine inspect` — Просмотр записей

```bash
python -m bioetl.main quarantine inspect --pipeline <NAME> [OPTIONS]
```

| Опция | Тип | По умолчанию | Описание |
|-------|-----|--------------|----------|
| `--pipeline` | str | Required | Имя пайплайна |
| `--limit` | int | 100 | Максимум записей |
| `--error-code` | str | None | Фильтр по коду ошибки |

**Примеры:**
```bash
python -m bioetl.main quarantine inspect --pipeline chembl_activity
python -m bioetl.main quarantine inspect --pipeline chembl_activity --error-code DQ_MISSING_FIELD
```

#### `quarantine stats` — Статистика

```bash
python -m bioetl.main quarantine stats --pipeline <NAME> [--json]
```

Показывает: общее количество, распределение по кодам ошибок, статусы (NEW, REVIEWED, RESOLVED).

#### `quarantine replay` — Повторная обработка

```bash
python -m bioetl.main quarantine replay --pipeline <NAME> [OPTIONS]
```

| Опция | Тип | По умолчанию | Описание |
|-------|-----|--------------|----------|
| `--pipeline` | str | Required | Имя пайплайна |
| `--error-code` | str | None | Фильтр по коду ошибки |
| `--max-age-days` | int | 7 | Максимальный возраст записей |
| `--dry-run` | flag | False | Предпросмотр |

#### `quarantine purge` — Удаление старых записей

```bash
python -m bioetl.main quarantine purge --pipeline <NAME> [OPTIONS]
```

| Опция | Тип | По умолчанию | Описание |
|-------|-----|--------------|----------|
| `--older-than-days` | int | 30 | Удалить записи старше N дней |
| `--dry-run` | flag | False | Предпросмотр |
| `--force` | flag | False | Без подтверждения |

#### `quarantine resolve` — Пометить как решённое

```bash
python -m bioetl.main quarantine resolve --pipeline <NAME> --payload-hash <HASH> [--status IGNORED|REPROCESSED]
```

---

### `checkpoint` — Управление checkpoint

#### `checkpoint list` — Список checkpoint

```bash
python -m bioetl.main checkpoint list --pipeline <NAME>
```

---

### `health` — Health checks

#### `health server` — HTTP health server

```bash
python -m bioetl.main health server [--host 127.0.0.1] [--port 8080]
```

**Endpoints:**
- `GET /health` — общий статус
- `GET /health/live` — Kubernetes liveness probe
- `GET /health/ready` — Kubernetes readiness probe
- `GET /health/providers` — детальный статус провайдеров

#### `health check` — Проверка провайдеров

```bash
python -m bioetl.main health check [--provider chembl] [--json]
```

Проверяет connectivity и health всех или указанных провайдеров.

**Примеры:**
```bash
python -m bioetl.main health check
python -m bioetl.main health check --provider chembl --provider pubchem
python -m bioetl.main health check --json
```

---

### `lock` — Управление блокировками

#### `lock release` — Освобождение блокировки

```bash
python -m bioetl.main lock release --pipeline <NAME> --run-id <UUID> [--exclusive]
```

> **Внимание:** Используйте только если уверены, что пайплайн не выполняется.

#### `lock check` — Проверка статуса блокировки

```bash
python -m bioetl.main lock check --pipeline <NAME> --run-id <UUID>
```

---

### `maintenance` — Maintenance операции

#### `maintenance vacuum` — VACUUM одной таблицы

```bash
python -m bioetl.main maintenance vacuum <TABLE> [OPTIONS]
```

| Опция | Тип | По умолчанию | Описание |
|-------|-----|--------------|----------|
| `--retention-days`, `-r` | int | 7 | Минимальный возраст файлов |
| `--dry-run` | flag | False | Предпросмотр |

**Примеры:**
```bash
python -m bioetl.main maintenance vacuum chembl.activity
python -m bioetl.main maintenance vacuum chembl.activity --dry-run
python -m bioetl.main maintenance vacuum chembl.activity -r 30
```

#### `maintenance vacuum-all` — VACUUM всех таблиц

```bash
python -m bioetl.main maintenance vacuum-all [OPTIONS]
```

| Опция | Тип | По умолчанию | Описание |
|-------|-----|--------------|----------|
| `--retention-days`, `-r` | int | 7 | Минимальный возраст файлов |
| `--dry-run` | flag | False | Предпросмотр |
| `--layer` | choice | `all` | Слой: `all`, `silver`, `gold` |

#### `maintenance archive` — Архивирование таблицы

```bash
python -m bioetl.main maintenance archive <TABLE> <TARGET_PATH> [--remove-source]
```

#### `maintenance bronze-cleanup` — Очистка Bronze

```bash
python -m bioetl.main maintenance bronze-cleanup [OPTIONS]
```

| Опция | Тип | По умолчанию | Описание |
|-------|-----|--------------|----------|
| `--retention-days`, `-r` | int | 90 | Удалить файлы старше N дней |
| `--dry-run` | flag | False | Предпросмотр |

---

## Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `BIOETL_ENV` | Окружение (`dev`, `prod`) | `dev` |
| `BIOETL_DATA_DIR` | Директория данных | `./data` |
| `BIOETL_LOG_LEVEL` | Уровень логирования | `INFO` |
| `BIOETL_METRICS_ENABLED` | Включить Prometheus метрики | `true` |
| `BIOETL_METRICS_PORT` | Порт для Prometheus | `8000` |
| `BIOETL_TRACING_ENABLED` | Включить OpenTelemetry tracing | `false` |

**API-ключи провайдеров:**
- `BIOETL_UNIPROT_API_KEY`
- `BIOETL_OPENALEX_API_KEY`
- `BIOETL_SEMANTIC_SCHOLAR_API_KEY`

---

## Exit Codes

Коды возврата следуют стандартам Unix (sysexits.h):

| Код | Константа | Описание |
|-----|-----------|----------|
| 0 | OK | Успешное выполнение |
| 1 | FAIL | Неспецифицированная ошибка |
| 64 | EX_USAGE | Ошибка использования командной строки |
| 78 | EX_CONFIG | Ошибка конфигурации |
| 80 | CONFIG_ERROR | Ошибка конфигурации пайплайна |
| 81 | INIT_ERROR | Ошибка инициализации |
| 82 | PIPELINE_ERROR | Ошибка выполнения пайплайна |
| 83 | DATA_QUALITY_ERROR | Превышен DQ порог |
| 84 | LOCK_ERROR | Ошибка блокировки |
| 85 | STORAGE_ERROR | Ошибка хранилища |
| 86 | NETWORK_ERROR | Сетевая ошибка |
| 87 | CHECKPOINT_ERROR | Ошибка checkpoint |
| 130 | SIGINT | Прервано Ctrl+C |
| 143 | SIGTERM | Завершено SIGTERM |

---

## См. также

- [Running Pipelines](../03-guides/running-pipelines.md) — руководство по запуску
- [Pipeline Configuration](../03-guides/pipeline-configuration.md) — настройка конфигураций
- [Metrics & Monitoring](../03-guides/metrics-monitoring.md) — метрики и мониторинг
- [Troubleshooting](../03-guides/troubleshooting.md) — решение проблем
