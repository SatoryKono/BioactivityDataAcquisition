# План: Унификация Registries + CSV Filter Reader Logger

**Дата:** 2025-12-26
**Ветка:** `claude/unify-registries-zgEJN`
**Приоритет:** Priority 5 (minor) + Minor task

---

## Обзор Задач

### Задача 1: Унификация ProviderRegistry и DataSourceRegistry

**Цель:** Объединить два реестра для уменьшения сложности.

**Текущее состояние:**
- `ProviderRegistry` (`src/bioetl/composition/providers/provider_registry.py`) - хранит конфигурации адаптеров (adapter_class, http_config, requires_http_client, custom_creator)
- `DataSourceRegistry` (`src/bioetl/composition/factories/data_source_registry.py`) - хранит creator functions для data sources

**Архитектурный анализ:**

| Аспект | ProviderRegistry | DataSourceRegistry |
|--------|------------------|-------------------|
| **Хранит** | ProviderConfig (класс + HTTP config) | DataSourceCreator (функции) |
| **Уровень** | Низкоуровневый (адаптеры) | Высокоуровневый (фабрики с wrapping) |
| **Зависимости** | Независимый | Зависит от ProviderRegistry |
| **Используется в** | DataSourceFactory, HttpClientFactory | GenericPipelineFactory |

---

### Задача 2: CSV Filter Reader Logger

**Цель:** Использовать LoggerPort вместо стандартного logging в CsvFilterReader.

**Текущее состояние:**
```python
# csv_filter_reader.py:9,17
import logging
logger = logging.getLogger(__name__)
```

**Проблема:** Нарушает принцип DI и архитектуру проекта (infrastructure не должен использовать прямые зависимости).

---

## Детальный План Реализации

### Фаза 1: CSV Filter Reader Logger (30 мин)

#### Шаг 1.1: Модификация CsvFilterReader

**Файл:** `src/bioetl/infrastructure/adapters/input/csv_filter_reader.py`

```python
# BEFORE
import logging
logger = logging.getLogger(__name__)

class CsvFilterReader:
    def __init__(self) -> None:
        pass  # No logger

    async def load_filter_ids(self, source_path: str, column_name: str) -> FilterLoadResult:
        ...
        logger.warning("filter_ids_duplicates_found", ...)  # Direct logging

# AFTER
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort

class CsvFilterReader:
    def __init__(self, logger: LoggerPort | None = None) -> None:
        self._logger = logger

    async def load_filter_ids(self, source_path: str, column_name: str) -> FilterLoadResult:
        ...
        if self._logger:
            self._logger.warning("filter_ids_duplicates_found", ...)
```

**Изменения:**
1. Удалить `import logging` и `logger = logging.getLogger(__name__)`
2. Добавить `LoggerPort` в TYPE_CHECKING
3. Добавить параметр `logger: LoggerPort | None = None` в конструктор
4. Заменить `logger.warning()` на `self._logger.warning()` с проверкой

#### Шаг 1.2: Обновление _wrap_with_filter

**Файл:** `src/bioetl/composition/factories/data_source_registry.py:57-82`

```python
# BEFORE
def _wrap_with_filter(
    data_source: DataSourcePort,
    filter_config: InputFilterConfig | None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    if filter_config and filter_config.enabled:
        return FilteredDataSource(
            filter_reader=CsvFilterReader(),  # No logger
            ...
        )

# AFTER
def _wrap_with_filter(
    data_source: DataSourcePort,
    filter_config: InputFilterConfig | None,
    logger: LoggerPort | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    if filter_config and filter_config.enabled:
        return FilteredDataSource(
            filter_reader=CsvFilterReader(logger=logger),  # With logger
            ...
        )
```

#### Шаг 1.3: Обновление creator functions

**Файл:** `src/bioetl/composition/factories/data_source_registry.py`

Все creator functions (`create_chembl_data_source`, `create_pubchem_data_source`, etc.) должны передавать `logger` в `_wrap_with_filter`:

```python
# BEFORE
return _wrap_with_filter(base_adapter, filter_config, metrics, pipeline_name)

# AFTER
return _wrap_with_filter(base_adapter, filter_config, logger, metrics, pipeline_name)
```

#### Шаг 1.4: Обновление тестов

**Файл:** `tests/unit/infrastructure/adapters/test_csv_filter_reader.py`

```python
# Добавить mock logger в тесты
from unittest.mock import MagicMock

@pytest.fixture
def mock_logger() -> MagicMock:
    return MagicMock()

@pytest.fixture
def filter_reader(mock_logger: MagicMock) -> CsvFilterReader:
    return CsvFilterReader(logger=mock_logger)

# Добавить тест для проверки логирования дубликатов
async def test_load_filter_ids_logs_duplicates(
    filter_reader: CsvFilterReader,
    mock_logger: MagicMock,
    tmp_path: Path,
) -> None:
    # Create CSV with duplicates
    csv_file = tmp_path / "ids.csv"
    csv_file.write_text("id\nA\nA\nB\n")

    await filter_reader.load_filter_ids(str(csv_file), "id")

    mock_logger.warning.assert_called_once()
```

---

### Фаза 2: Унификация Registries (1-2 часа)

#### Анализ целесообразности

**Вариант A: Полное объединение** (НЕ рекомендуется)
- Смешение ответственностей (config vs factory)
- Усложнение API
- Нарушение SRP

**Вариант B: Композиция** (рекомендуется)
- DataSourceRegistry делегирует ProviderRegistry
- Единый публичный API
- Сохранение чёткой ответственности

**Вариант C: Упрощение DataSourceRegistry** (рекомендуется)
- Перенести creator logic в ProviderRegistry
- DataSourceRegistry становится тонким фасадом
- Минимальные изменения в клиентском коде

#### Шаг 2.1: Расширение ProviderConfig

**Файл:** `src/bioetl/composition/providers/provider_registry.py`

```python
@dataclass(frozen=True)
class ProviderConfig:
    adapter_class: type[DataSourcePort]
    http_config: HttpConfig | None = None
    requires_http_client: bool = True
    requires_logger: bool = True
    default_kwargs: dict[str, Any] = field(default_factory=dict)
    custom_creator: AdapterCreator | None = None
    # NEW: High-level creator for DataSourceRegistry
    data_source_creator: DataSourceCreator | None = None
```

#### Шаг 2.2: Добавление create_data_source в ProviderRegistry

```python
class ProviderRegistry:
    @classmethod
    def create_data_source(
        cls,
        name: str,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        filter_config: InputFilterConfig | None = None,
        metrics: MetricsPort | None = None,
        pipeline_name: str = "unknown",
    ) -> DataSourcePort:
        """Create fully configured data source with wrapping."""
        config = cls.get(name)

        if config.data_source_creator:
            return config.data_source_creator(
                settings, pipeline_config, logger,
                filter_config, metrics, pipeline_name
            )

        # Default creation logic
        http_client = HttpClientFactory.create_for_provider(name, settings)
        base_adapter = cls.create_adapter(name, http_client, logger)
        return _wrap_with_filter(base_adapter, filter_config, logger, metrics, pipeline_name)
```

#### Шаг 2.3: Упрощение DataSourceRegistry

```python
class DataSourceRegistry:
    """Thin facade over ProviderRegistry for data source creation.

    DEPRECATED: Prefer using ProviderRegistry.create_data_source() directly.
    This class is kept for backward compatibility.
    """

    @classmethod
    def get(cls, provider: str) -> DataSourceCreator:
        """Get creator function for provider.

        Returns a wrapper that delegates to ProviderRegistry.create_data_source().
        """
        ensure_providers_loaded()

        if not ProviderRegistry.is_registered(provider):
            available = ", ".join(ProviderRegistry.list_providers())
            raise KeyError(f"Unknown provider: {provider}. Available: {available}")

        # Return a closure that delegates to ProviderRegistry
        def creator(
            settings: Settings,
            pipeline_config: PipelineYamlConfig,
            logger: LoggerPort,
            filter_config: InputFilterConfig | None = None,
            metrics: MetricsPort | None = None,
            pipeline_name: str = "unknown",
        ) -> DataSourcePort:
            return ProviderRegistry.create_data_source(
                provider, settings, pipeline_config, logger,
                filter_config, metrics, pipeline_name
            )

        return creator
```

#### Шаг 2.4: Перенос creator functions в registration.py

**Файл:** `src/bioetl/composition/providers/registration.py`

```python
def _create_chembl_data_source(...) -> DataSourcePort:
    """ChEMBL data source creator with filtering support."""
    http_client = HttpClientFactory.create_for_provider("chembl", settings)
    base_adapter = DataSourceFactory.create("chembl", http_client=http_client, logger=logger)
    return _wrap_with_filter(base_adapter, filter_config, logger, metrics, pipeline_name)

def register_all_providers() -> None:
    if not ProviderRegistry.is_registered("chembl"):
        ProviderRegistry.register(
            "chembl",
            ProviderConfig(
                adapter_class=ChemblAdapter,
                http_config=HttpConfig(rate=10.0, capacity=20),
                requires_http_client=True,
                requires_logger=True,
                data_source_creator=_create_chembl_data_source,  # NEW
            ),
        )
```

#### Шаг 2.5: Обновление GenericPipelineFactory

**Файл:** `src/bioetl/composition/factories/generic_factory.py:109`

```python
# BEFORE
self._create_data_source = data_source_creator or DataSourceRegistry.get(provider)

# AFTER (optional - keeps compatibility)
# No change needed if DataSourceRegistry.get() delegates properly
```

#### Шаг 2.6: Обновление тестов

**Файлы:**
- `tests/unit/composition/factories/test_data_source_registry.py`
- `tests/unit/composition/providers/test_provider_registry.py`
- `tests/architecture/test_registry_contracts.py`

Добавить тесты для:
1. `ProviderRegistry.create_data_source()`
2. `DataSourceRegistry.get()` делегирует в ProviderRegistry
3. Backward compatibility

---

## Порядок Выполнения

### Этап 1: CSV Filter Reader Logger
1. [x] Анализ текущего состояния
2. [ ] Модификация CsvFilterReader (добавить logger parameter)
3. [ ] Обновление _wrap_with_filter (передать logger)
4. [ ] Обновление всех creator functions
5. [ ] Обновление тестов
6. [ ] Запуск `make lint && make test`

### Этап 2: Унификация Registries
1. [x] Анализ архитектуры
2. [ ] Расширение ProviderConfig (добавить data_source_creator)
3. [ ] Добавление ProviderRegistry.create_data_source()
4. [ ] Перенос creator functions в registration.py
5. [ ] Упрощение DataSourceRegistry до thin facade
6. [ ] Обновление тестов
7. [ ] Запуск `make lint && make test`

---

## Файлы для Изменения

### Фаза 1 (обязательные)
| Файл | Тип изменения |
|------|---------------|
| `src/bioetl/infrastructure/adapters/input/csv_filter_reader.py` | Добавить LoggerPort |
| `src/bioetl/composition/factories/data_source_registry.py` | Передать logger в _wrap_with_filter |
| `tests/unit/infrastructure/adapters/test_csv_filter_reader.py` | Обновить тесты |

### Фаза 2 (опциональные)
| Файл | Тип изменения |
|------|---------------|
| `src/bioetl/composition/providers/provider_registry.py` | Добавить create_data_source |
| `src/bioetl/composition/providers/registration.py` | Перенести creators |
| `src/bioetl/composition/factories/data_source_registry.py` | Упростить до facade |
| `tests/unit/composition/providers/test_provider_registry.py` | Новые тесты |
| `tests/architecture/test_registry_contracts.py` | Обновить контракты |

---

## Риски и Митигация

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Breaking change в DataSourceRegistry API | Низкая | Сохранить backward compatible API |
| Circular imports | Средняя | TYPE_CHECKING для типов |
| Пропущенные тесты | Низкая | Запуск полного test suite |

---

## Критерии Завершения

- [ ] `make lint` проходит без ошибок
- [ ] `make test` проходит (1471+ тестов)
- [ ] CsvFilterReader использует LoggerPort
- [ ] DataSourceRegistry делегирует в ProviderRegistry
- [ ] Все архитектурные тесты проходят
- [ ] Коммит с описательным сообщением
- [ ] Push в ветку `claude/unify-registries-zgEJN`

---

## Рекомендация

**Рекомендую начать с Фазы 1 (CSV Filter Reader Logger)** как менее рискового изменения. После успешного завершения можно перейти к Фазе 2.

Фаза 2 является опциональной оптимизацией — система работает корректно и без неё. Решение о её выполнении следует принять после Фазы 1.
