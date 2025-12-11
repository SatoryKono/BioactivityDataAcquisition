# План рефакторинга доменной архитектуры

**Дата создания:** 2025-12-11
**Интегральный балл архитектуры:** 5.76/10
**Статус:** В работе

---

## Краткое резюме

Архитектура проекта следует принципам Hexagonal Architecture (Ports & Adapters) с четырьмя слоями:
- `domain` — чистая бизнес-логика, контракты (ABC, Protocol)
- `application` — use cases, оркестрация
- `infrastructure` — технические реализации (HTTP, файлы, БД)
- `interfaces` — адаптеры пользовательского интерфейса (CLI, REST)

**Текущие проблемы:**
1. Нарушение границ слоёв через deprecation-прокси в домене
2. Дублирование реализаций (`InMemoryProviderRegistry`)
3. Незавершённая миграция портов Extraction с Pydantic на dict
4. Использование `SimpleNamespace` вместо явного порта метаданных

---

## Фаза 1: Очистка границ слоёв (Критично)

### Задача 1.1: Удаление ConfigMigrator прокси из домена

**Проблема:**
Файл `src/bioetl/domain/configs/migration.py` содержит динамический импорт из infrastructure через `importlib.import_module()`, что нарушает изоляцию доменного слоя.

**Текущее состояние:**
```python
# src/bioetl/domain/configs/migration.py:32
mod = importlib.import_module(".".join(["bioetl", "infrastructure", "config", "migration"]))
```

**Затронутые файлы:**
- `src/bioetl/domain/configs/migration.py` — удалить полностью
- `src/bioetl/domain/configs/__init__.py:146-157` — убрать реэкспорт
- `tests/bioetl/domain/test_config_migration.py:6` — обновить импорт

**Шаги выполнения:**
1. Обновить тест `tests/bioetl/domain/test_config_migration.py`:
   ```python
   # Было:
   from bioetl.domain.configs.migration import ConfigMigrator
   # Стало:
   from bioetl.infrastructure.config.migration import ConfigMigrator
   ```
2. Удалить файл `src/bioetl/domain/configs/migration.py`
3. Удалить реэкспорт из `src/bioetl/domain/configs/__init__.py`
4. Запустить архитектурные тесты: `pytest tests/architecture/ tests/project_rules/test_layer_architecture.py -v`

**Критерии готовности:**
- [ ] Файл `domain/configs/migration.py` удалён
- [ ] Архитектурные тесты проходят
- [ ] Нет импортов `bioetl.infrastructure` в домене

**Риски и митигация:**
- Риск: Внешний код зависит от старого пути импорта
- Митигация: Уже есть deprecation warning; документировать изменение в CHANGELOG

---

### Задача 1.2: Консолидация InMemoryProviderRegistry

**Проблема:**
Дублирование класса `InMemoryProviderRegistry` в двух слоях:
- `src/bioetl/infrastructure/provider_registry.py:17-57` (правильное расположение)
- `src/bioetl/application/memory_registry.py:17-56` (дубликат)

**Текущее использование (application версия):**
```
src/bioetl/application/orchestrator.py:42,300,323,328,330
```

**Текущее использование (infrastructure версия):**
```
src/bioetl/infrastructure/config/provider_registry.py:31,239,291,385
tests/conftest.py:556
tests/bioetl/application/test_container.py:25,45-46
tests/bioetl/application/test_container_provider_registration.py:11,21
tests/bioetl/application/test_container_schema_bootstrap.py:32,55,57,99,131,158,185,210,232
```

**Шаги выполнения:**
1. Обновить импорты в `src/bioetl/application/orchestrator.py`:
   ```python
   # Было:
   from bioetl.application.memory_registry import InMemoryProviderRegistry
   # Стало:
   from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry
   ```
2. Удалить файл `src/bioetl/application/memory_registry.py`
3. Обновить `tests/architecture/test_architecture_rules.py:32` — убрать из allowed duplicates
4. Обновить `tests/architecture/test_architecture_policies.py:195` — убрать исключение
5. Запустить тесты: `pytest tests/bioetl/application/ -v`

**Критерии готовности:**
- [ ] Файл `application/memory_registry.py` удалён
- [ ] Все импорты используют `infrastructure.provider_registry`
- [ ] Тесты на дубликаты проходят без исключений

**Примечание:**
Это допустимое нарушение правила "infrastructure не импортирует application", поскольку application импортирует из infrastructure, а не наоборот.

---

### Задача 1.3: Добавить архитектурный тест на динамические импорты

**Цель:**
Предотвратить будущие обходы границ слоёв через `importlib`.

**Файл:** `tests/architecture/test_domain_boundaries.py`

**Новый тест:**
```python
def test_domain_has_no_dynamic_infrastructure_imports(
    domain_files: list[Path], domain_trees: dict[Path, ast.Module]
) -> None:
    """Verify domain doesn't use importlib to import infrastructure."""
    violations: list[str] = []

    for file_path in domain_files:
        code = file_path.read_text(encoding="utf-8")
        if "importlib.import_module" in code and "infrastructure" in code:
            violations.append(f"{file_path.as_posix()}: dynamic import of infrastructure")

    if violations:
        pytest.fail(f"Domain must not dynamically import infrastructure:\n" +
                   "\n".join(violations))
```

**Критерии готовности:**
- [ ] Тест добавлен и проходит
- [ ] CI включает новый тест

---

## Фаза 2: Миграция портов Extraction (Критично)

### Задача 2.1: Удаление устаревших Pydantic-конвертеров

**Проблема:**
Функции `to_raw_records()` и `from_raw_records()` в `domain/ports/extraction.py` используют Pydantic-модели, создавая зависимость домена от конкретных моделей и блокируя чистую dict-архитектуру.

**Текущее состояние:**
```python
# src/bioetl/domain/ports/extraction.py:161-207
def to_raw_records(batch: RecordBatch) -> list["SourceRecordModel"]:
    from bioetl.domain.record_source import SourceRecordModel
    return [SourceRecordModel.model_validate(record) for record in batch]

def from_raw_records(records: list["SourceRecordModel"]) -> RecordBatch:
    return [record.model_dump() for record in records]
```

**Использование:**
- `tests/bioetl/domain/ports/test_extraction.py` — тесты на deprecated функции
- `src/bioetl/domain/ports/__init__.py` — реэкспорт
- `src/bioetl/domain/_deprecations.py` — регистрация deprecation

**Шаги выполнения:**

#### Этап 2.1.1: Поиск реального использования
```bash
grep -r "to_raw_records\|from_raw_records" src/ --include="*.py" | grep -v "test_\|_test.py\|__pycache__"
```

#### Этап 2.1.2: Миграция клиентов (если найдены)
Для каждого клиента:
1. Заменить `to_raw_records(batch)` на прямую работу с dict
2. Заменить `from_raw_records(records)` на `[r.model_dump() for r in records]` или возврат dict напрямую

#### Этап 2.1.3: Удаление deprecated функций
1. Удалить функции из `src/bioetl/domain/ports/extraction.py:161-207`
2. Удалить из `__all__` в том же файле
3. Удалить реэкспорт из `src/bioetl/domain/ports/__init__.py:24-25,83-84`
4. Удалить из `src/bioetl/domain/_deprecations.py:133-143`

#### Этап 2.1.4: Обновление тестов
1. Удалить тесты `TestBackwardCompatibilityHelpers` из `tests/bioetl/domain/ports/test_extraction.py:286-391`
2. Или переместить в `tests/migrations/` как исторический артефакт

**Критерии готовности:**
- [ ] `to_raw_records` и `from_raw_records` удалены из порта
- [ ] Нет импортов `SourceRecordModel` в `domain/ports/extraction.py`
- [ ] Все клиенты мигрированы на dict
- [ ] Архитектурные тесты проходят

---

### Задача 2.2: Очистка TYPE_CHECKING импортов в портах

**Проблема:**
Даже в `TYPE_CHECKING` блоке ссылка на `SourceRecordModel` создаёт концептуальную связь домена с конкретной моделью.

**Текущее состояние:**
```python
# src/bioetl/domain/ports/extraction.py:30-31
if TYPE_CHECKING:
    from bioetl.domain.record_source import SourceRecordModel
```

**Шаги выполнения:**
1. После удаления `to_raw_records`/`from_raw_records` — удалить TYPE_CHECKING импорт
2. Убедиться, что `RecordBatch = list[dict[str, Any]]` остаётся единственным контрактом

**Критерии готовности:**
- [ ] Нет импортов `SourceRecordModel` в extraction.py
- [ ] Порт работает только с `RecordBatch` (dict)

---

## Фаза 3: Стандартизация метаданных пайплайнов (Высокий приоритет)

### Задача 3.1: Создание DefaultRunMetadataBuilder

**Проблема:**
В `PipelineBase` используется `SimpleNamespace` с `cast()` для создания fallback metadata builder, что обходит типизацию и усложняет тестирование.

**Текущее состояние:**
```python
# src/bioetl/application/pipelines/base.py:82-103
def _create_default_metadata_builder() -> RunMetadataBuilderProtocol:
    return cast(
        RunMetadataBuilderProtocol,
        SimpleNamespace(
            build_run_metadata=lambda context, write_result: {...},
            build_dry_run_metadata=lambda context, row_count: {...},
        ),
    )
```

**Шаги выполнения:**

#### Этап 3.1.1: Создание класса в application
```python
# src/bioetl/application/metadata/builder.py
from bioetl.domain.clients.base.output.contracts import (
    RunMetadataBuilderProtocol,
    WriteResult,
)
from bioetl.domain.models import RunContext


class DefaultRunMetadataBuilder:
    """Default implementation of RunMetadataBuilderProtocol.

    Provides basic metadata building without external dependencies.
    Used as fallback when container doesn't provide a builder.
    """

    def build_run_metadata(
        self, context: RunContext, write_result: WriteResult
    ) -> dict[str, object]:
        return {
            "run_id": context.run_id,
            "provider": context.provider,
            "entity": context.entity_name,
            "row_count": write_result.row_count,
            "dry_run": False,
        }

    def build_dry_run_metadata(
        self, context: RunContext, row_count: int
    ) -> dict[str, object]:
        return {
            "run_id": context.run_id,
            "provider": context.provider,
            "entity": context.entity_name,
            "row_count": row_count,
            "dry_run": True,
        }
```

#### Этап 3.1.2: Обновление PipelineBase
```python
# src/bioetl/application/pipelines/base.py
from bioetl.application.metadata.builder import DefaultRunMetadataBuilder

# Удалить функцию _create_default_metadata_builder()
# Заменить:
self._metadata_builder = metadata_builder or DefaultRunMetadataBuilder()
```

#### Этап 3.1.3: Обновление фабрик
Обновить `src/bioetl/application/factories/noop.py`:
```python
from bioetl.application.metadata.builder import DefaultRunMetadataBuilder

def create_noop_metadata_builder() -> RunMetadataBuilderProtocol:
    return DefaultRunMetadataBuilder()
```

**Критерии готовности:**
- [ ] `DefaultRunMetadataBuilder` создан в `application/metadata/`
- [ ] `SimpleNamespace` удалён из `pipelines/base.py`
- [ ] Все фабрики используют новый класс
- [ ] Unit-тесты покрывают builder

---

## Фаза 4: Усиление DDD/Hexagon (Средний приоритет)

### Задача 4.1: Формализация портов логирования

**Цель:**
Убедиться, что все порты наблюдаемости определены в домене и реализованы в infrastructure.

**Текущее состояние:**
- `LoggingPortABC` уже в `domain/observability/`
- Реализации в `infrastructure/logging/`

**Проверка:**
```bash
grep -r "class.*LoggingPort\|class.*MetricsPort\|class.*TracingPort" src/
```

**Шаги:**
1. Аудит всех портов наблюдаемости
2. Документировать в `docs/architecture/ports.md`
3. Добавить диаграмму зависимостей

---

### Задача 4.2: Обновление документации границ слоёв

**Файлы для обновления:**
- `docs/architecture/18-domain-layer-audit.md` — отметить выполненные задачи
- `ARCHITECTURE.md` — обновить описание границ
- Диаграммы в `docs/architecture/diagrams/`

---

## Фаза 5: Документация и правила (Средний приоритет)

### Задача 5.1: Обновление CHANGELOG

Добавить раздел Breaking Changes:
```markdown
## [Unreleased]

### Breaking Changes
- `ConfigMigrator` больше не доступен из `bioetl.domain.configs.migration`
  Используйте `from bioetl.infrastructure.config.migration import ConfigMigrator`
- `to_raw_records()` и `from_raw_records()` удалены из `bioetl.domain.ports.extraction`
  Используйте `RecordMapperABC` в application layer
```

### Задача 5.2: Обновление styleguide

Добавить раздел о границах слоёв в styleguide:
```markdown
## Layer Boundaries

### Domain Layer Rules
1. NEVER import from infrastructure, application, or interfaces
2. NEVER use importlib to dynamically import other layers
3. Only define contracts (ABC, Protocol) and pure business logic
4. All external dependencies must be injected through ports

### Application Layer Rules
1. MAY import from domain
2. NEVER import from infrastructure or interfaces
3. Orchestrates use cases using domain contracts
```

---

## Фаза 6: Тестовая матрица (Желательный приоритет)

### Задача 6.1: Property-based тесты для трансформаций

**Цель:** Добавить hypothesis-тесты для валидации трансформаций.

**Файл:** `tests/bioetl/domain/transform/test_transformers_property.py`

### Задача 6.2: Контрактные тесты клиентов

**Цель:** Проверить, что реализации портов соответствуют контрактам без Pydantic.

---

## Метрики успеха

| Метрика | До | После (ожидание) |
|---------|-----|------------------|
| Импорты infrastructure в domain | 1 (dynamic) | 0 |
| Дублированные классы | 1 | 0 |
| Deprecated функции в портах | 2 | 0 |
| SimpleNamespace в base.py | 1 | 0 |
| Архитектурные тесты | Pass | Pass |
| Интегральный балл | 5.76 | 7.0+ |

---

## Порядок выполнения

```
Фаза 1 (Критично)
├── 1.1 ConfigMigrator прокси      [1-2 часа]
├── 1.2 InMemoryProviderRegistry   [1 час]
└── 1.3 Тест на динамические импорты [30 мин]

Фаза 2 (Критично)
├── 2.1 Удаление Pydantic-конвертеров [2-3 часа]
└── 2.2 Очистка TYPE_CHECKING      [30 мин]

Фаза 3 (Высокий)
└── 3.1 DefaultRunMetadataBuilder  [1-2 часа]

Фаза 4 (Средний)
├── 4.1 Аудит портов наблюдаемости [1 час]
└── 4.2 Обновление документации    [1-2 часа]

Фаза 5 (Средний)
├── 5.1 CHANGELOG                  [30 мин]
└── 5.2 Styleguide                 [30 мин]

Фаза 6 (Желательный)
├── 6.1 Property-based тесты       [2-3 часа]
└── 6.2 Контрактные тесты          [2-3 часа]
```

---

## Команды для проверки

```bash
# Архитектурные тесты
pytest tests/architecture/ -v

# Тесты слоёв
pytest tests/project_rules/test_layer_architecture.py -v

# Тесты на дубликаты
pytest tests/project_rules/test_duplicates.py -v

# Полный набор
pytest tests/architecture/ tests/project_rules/ -v

# Проверка импортов в домене
grep -r "from bioetl.infrastructure\|from bioetl.application" src/bioetl/domain/
```

---

## Ссылки

- [Domain Layer Audit](./18-domain-layer-audit.md)
- [Architecture Tests](../../tests/architecture/)
- [Project Rules Tests](../../tests/project_rules/)
