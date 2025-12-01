# 02 Logging And Configuration

## Описание

Документ описывает централизованные компоненты логирования и конфигурации, используемые всеми пайплайнами проекта. Логирование обеспечивает структурированный вывод событий с контекстными метаданными, а система конфигурации позволяет описывать параметры запуска и загружать их из YAML-файлов, упрощая переиспользование пайплайнов в разных окружениях.

## Логирование

### UnifiedLogger

Логирование централизовано в модуле `src/bioetl/core/logging.py`, где реализован `UnifiedLogger` — единый логгер для всего проекта.

**Основные возможности:**

- **Форматирование**: структурированный вывод логов с поддержкой различных форматов (JSON, текстовый)
- **Контекстные метаданные**: автоматическое добавление контекстной информации (run_id, имя пайплайна, стадия выполнения)
- **Динамический контроль уровня**: возможность изменения уровня логирования во время выполнения
- **Интеграция с LoggerAdapterABC**: реализация интерфейса `LoggerAdapterABC` для единообразного использования в пайплайнах

**Модуль:** `src/bioetl/core/logging.py`

**Использование:**

```python
from bioetl.core.logging import UnifiedLogger

# Создание логгера
logger = UnifiedLogger()

# Логирование с контекстом
logger = logger.bind(run_id="run-123", pipeline="chembl-activity")
logger.info("Pipeline started", stage="extract")

# Динамическое изменение уровня
logger.set_level("DEBUG")
```

**Структурированные поля:**

Логгер поддерживает структурированное логирование с дополнительными полями:

```python
logger.info(
    "Processing records",
    record_count=1000,
    stage="transform",
    duration_ms=150.5
)
```

**Уровни логирования:**

- `DEBUG` — детальная отладочная информация
- `INFO` — информационные сообщения о ходе выполнения
- `WARNING` — предупреждения о потенциальных проблемах
- `ERROR` — ошибки выполнения

## Конфигурация

### Конфигурационные модели

Конфигурационные модели определены в модуле `src/bioetl/core/config/models.py` и позволяют описывать параметры запуска пайплайнов.

**Основные возможности:**

- **Типизированные модели**: использование Pydantic или dataclasses для валидации конфигурации
- **Загрузка из YAML**: автоматическая загрузка конфигурации из YAML-файлов
- **Профили конфигурации**: поддержка различных профилей (development, production, testing)
- **Переопределения**: возможность переопределения параметров через CLI или переменные окружения

**Модуль:** `src/bioetl/core/config/models.py`

**Типы параметров:**

Конфигурационные модели описывают следующие категории параметров:

1. **Пути хранения** (`storage_path`, `output_path`): пути для сохранения результатов и промежуточных данных
2. **Настройки клиента** (`client_config`): параметры подключения к внешним API (таймауты, retry, rate limiting)
3. **Профили** (`profile`): именованные наборы настроек для разных окружений
4. **Параметры пайплайна** (`pipeline_params`): специфичные для пайплайна настройки (фильтры, лимиты, опции трансформации)

**Пример конфигурации:**

```yaml
# configs/pipelines/chembl/activity.yaml
profile: production

storage:
  output_path: ./data/output
  cache_path: ./data/cache

client:
  timeout: 30.0
  max_retries: 3
  rate_limit: 10  # requests per second

pipeline:
  filters:
    assay_type: "B"
  limit: null  # no limit
```

**Загрузка конфигурации:**

```python
from bioetl.core.config.models import PipelineConfig
from bioetl.core.config.resolver import ConfigResolver

# Загрузка из YAML
resolver = ConfigResolver()
config = resolver.resolve(
    profile="production",
    overrides={"client.timeout": 60.0}
)
```

**Интеграция с ConfigResolverABC:**

Конфигурационные модели используются реализацией `ConfigResolverABC`, которая:

1. Загружает базовую конфигурацию из YAML-файла
2. Применяет профиль конфигурации
3. Применяет переопределения (overrides)
4. Валидирует финальную конфигурацию по модели
5. Возвращает типизированный объект конфигурации

## Переиспользование в разных окружениях

Централизованные логирование и конфигурация упрощают переиспользование пайплайнов в разных окружениях:

1. **Разработка**: профиль `development` с детальным логированием и локальными путями
2. **Тестирование**: профиль `testing` с ограничениями и валидацией
3. **Продакшн**: профиль `production` с оптимизированными настройками и мониторингом

**Пример использования профилей:**

```bash
# Запуск с профилем development
bioetl run-chembl-activity --profile development

# Запуск с профилем production
bioetl run-chembl-activity --profile production

# Переопределение параметров
bioetl run-chembl-activity --profile production --override client.timeout=60
```

## Related Components

- **LoggerAdapterABC**: интерфейс адаптера логирования (см. `docs/01-ABC/08-logger-adapter-abc.md`)
- **ConfigResolverABC**: интерфейс разрешения конфигурации (см. `docs/01-ABC/03-config-resolver-abc.md`)
- **PipelineBase**: базовый класс пайплайнов, использующий логирование и конфигурацию (см. `docs/02-pipelines/00-pipeline-base.md`)

## Модули

- `src/bioetl/core/logging.py` — реализация UnifiedLogger
- `src/bioetl/core/config/models.py` — конфигурационные модели
- `src/bioetl/core/config/resolver.py` — разрешение конфигураций (если существует)

