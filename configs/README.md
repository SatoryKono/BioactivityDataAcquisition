# Configuration Architecture

## Структура

```
configs/
├── profiles/               # Переиспользуемые профили конфигураций
│   ├── chembl_default.yaml    # Базовые настройки для всех ChEMBL-пайплайнов
│   ├── development.yaml       # Профиль для локальной разработки
│   └── production.yaml        # Профиль для production окружения
│
└── pipelines/             # Конфигурации конкретных пайплайнов
    └── chembl/
        ├── activity.yaml      # Activity pipeline (extends chembl_default)
        ├── assay.yaml         # Assay pipeline (extends chembl_default)
        ├── target.yaml        # Target pipeline (extends chembl_default)
        ├── document.yaml      # Document pipeline (extends chembl_default)
        └── molecule.yaml      # Molecule pipeline (extends chembl_default)
```

## Иерархия наследования

```
chembl_default.yaml (базовые параметры: pagination, client, storage, logging)
      ↓ extends
development.yaml / production.yaml (override для окружения)
      ↓ extends
activity.yaml / assay.yaml / ... (специфика entity: endpoint, fields)
```

## Использование профилей

### Development (быстрые прогоны)

```bash
bioetl run activity_chembl --profile development
```

Применяются настройки:
- `pagination.limit: 100` (вместо 1000)
- `pagination.max_pages: 5` (ограничение для быстрого теста)
- `logging.level: DEBUG`
- `qc.enable_quality_report: false` (отключение QC для скорости)

### Production (полные прогоны)

```bash
bioetl run activity_chembl --profile production
```

Применяются настройки:
- `pagination.limit: 1000` (полные страницы)
- `client.timeout: 60.0` (увеличенные таймауты)
- `qc.enable_quality_report: true` (полные QC-отчёты)
- `determinism.validate_checksums: true` (проверка контрольных сумм)

### Без профиля (default)

```bash
bioetl run activity_chembl
```

Автоматически применяется `chembl_default.yaml`.

## Переопределение параметров

### Через CLI

```bash
# Override одного параметра
bioetl run activity_chembl --set client.timeout=120

# Override нескольких параметров
bioetl run activity_chembl \
  --set client.timeout=120 \
  --set pagination.limit=500
```

### Через переменные окружения

```bash
export BIOETL_CLIENT_TIMEOUT=120
export BIOETL_PAGINATION_LIMIT=500
bioetl run activity_chembl
```

### Приоритет (от высшего к низшему)

1. **Переменные окружения** (`BIOETL_*`)
2. **CLI overrides** (`--set key=value`)
3. **Pipeline config** (`configs/pipelines/chembl/activity.yaml`)
4. **Profile** (`configs/profiles/development.yaml`)
5. **Base profile** (`configs/profiles/chembl_default.yaml`)

## Добавление нового пайплайна

### 1. Создать конфиг пайплайна

```yaml
# configs/pipelines/chembl/new_entity.yaml
extends: chembl_default

entity_name: new_entity
endpoint: /new_entity
primary_key: entity_id

fields:
  - name: entity_id
    data_type: integer
    is_nullable: false
    description: ID сущности

# Специфичные параметры (если нужны)
pipeline:
  custom_param: value
```

### 2. Проверить конфигурацию

```bash
bioetl validate-config configs/pipelines/chembl/new_entity.yaml
```

### 3. Запустить smoke-тест

```bash
bioetl run new_entity_chembl --profile development --dry-run
```

## Параметры в chembl_default.yaml

### Секция `pagination`
- `limit`: количество записей на страницу
- `offset`: начальный offset
- `max_pages`: максимальное количество страниц (null = без ограничений)

### Секция `client`
- `timeout`: таймаут HTTP-запроса (секунды)
- `max_retries`: максимальное количество повторных попыток
- `rate_limit`: ограничение запросов в секунду
- `backoff_factor`: множитель для exponential backoff
- `circuit_breaker_threshold`: порог срабатывания circuit breaker
- `circuit_breaker_recovery_time`: время (секунды) удержания открытого circuit breaker перед повторной попыткой

### Секция `storage`
- `output_path`: путь для финальных артефактов
- `cache_path`: путь для кэша HTTP-ответов
- `temp_path`: путь для временных файлов

### Секция `logging`
- `level`: уровень логирования (DEBUG/INFO/WARN/ERROR)
- `structured`: включает структурированное логирование
- `redact_secrets`: маскирует секреты

### Секция `metrics`
- `enabled`: включает экспорт метрик Prometheus (по умолчанию включено)
- `port`: порт HTTP-сервера метрик
- `address`: адрес биндинга (по умолчанию `0.0.0.0`)

Экспортер метрик запускается один раз на процесс в CLI-энтрипоинте. При повторных
запусках в рамках одного процесса повторный старт подавляется. Установите
`metrics.enabled: false` в профиле или конфиге пайплайна для полного отключения
Prometheus-эндпоинта или переопределите `port`/`address` для совместимости с
инфраструктурой.

### Секция `determinism`
- `stable_sort`: стабильная сортировка строк/колонок
- `utc_timestamps`: все даты в UTC
- `canonical_json`: канонический JSON (упорядоченные ключи)
- `atomic_writes`: атомарная запись (temp → os.replace)
- `validate_checksums`: проверка контрольных сумм при чтении

### Секция `qc`
- `enable_quality_report`: генерация quality_report_table.csv
- `enable_correlation_report`: генерация correlation_report_table.csv
- `min_coverage`: минимальный порог покрытия данных
- `fail_on_low_coverage`: fail пайплайна при низком покрытии

### Секция `features`
- `rest_interface_enabled`: включает REST-сервер на FastAPI (по умолчанию `false`)
- `mq_interface_enabled`: разрешает запуск через MQ-слушатель (по умолчанию `false`)

## Related Documents

- `docs/cli/03-config-precedence-and-profiles.md` — детальное описание приоритетов
- `docs/00-styleguide/04-architecture-and-duplication-reduction.md` — архитектура снижения дублирования
- `docs/infrastructure/config/00-config-resolver.md` — ConfigResolver

