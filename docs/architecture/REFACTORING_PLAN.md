# Консолидированный план рефакторинга архитектуры BioETL

**Дата обновления:** 2025-12-11
**Базовый интегральный балл:** 6.1 - 8.3 (среднее ~7.0/10)
**Целевой балл:** 8.5 - 9.0/10
**Статус:** В работе

> Этот документ консолидирует результаты 9 архитектурных обзоров и является каноничным источником для планирования рефакторинга.

---

## Оглавление

1. [Краткое резюме](#краткое-резюме)
2. [Сводная архитектурная оценка](#сводная-архитектурная-оценка)
3. [Фаза 1: Устранение дублирования контрактов](#фаза-1-устранение-дублирования-контрактов-p0)
4. [Фаза 2: Изоляция интерфейсного слоя](#фаза-2-изоляция-интерфейсного-слоя-p1)
5. [Фаза 3: Декомпозиция god objects](#фаза-3-декомпозиция-god-objects-p1)
6. [Фаза 4: Устранение глобальных синглтонов](#фаза-4-устранение-глобальных-синглтонов-p2)
7. [Фаза 5: Обработка ошибок и устойчивость](#фаза-5-обработка-ошибок-и-устойчивость-p2)
8. [Фаза 6: Документация и архитектурные тесты](#фаза-6-документация-и-архитектурные-тесты-p3)
9. [Метрики и тесты](#метрики-и-тесты)
10. [Порядок выполнения](#порядок-выполнения)
11. [Устаревшие задачи](#устаревшие-задачи-из-предыдущих-версий)

---

## Краткое резюме

Архитектура проекта следует принципам **Hexagonal Architecture (Ports & Adapters)** с четырьмя слоями:

```
┌─────────────────────────────────────────────────────────────┐
│                        interfaces                            │
│              (CLI, REST API, composition root)               │
├─────────────────────────────────────────────────────────────┤
│                       application                            │
│          (use cases, orchestration, pipelines)               │
├─────────────────────────────────────────────────────────────┤
│                         domain                               │
│    (entities, value objects, contracts ABC/Protocol)         │
├─────────────────────────────────────────────────────────────┤
│                      infrastructure                          │
│        (HTTP clients, files, DB, Pandera, logging)           │
└─────────────────────────────────────────────────────────────┘
```

### Сильные стороны
- Чёткое разделение слоёв, защищённое архитектурными тестами
- 79 ABC/Protocol контрактов, обеспечивающих Ports & Adapters
- Централизованный Composition Root для сборки зависимостей
- Детальная документация (README, ADR, архитектурные гайды)

### Консолидированные проблемы (приоритет ↓)

| # | Проблема | Влияние | Файлы | Категория |
|---|----------|---------|-------|-----------|
| 1 | **Дублирование контрактов пайплайнов** (YAML + hardcoded) | Рассинхронизация, двойное обновление | `domain/schemas/pipeline_contracts.py`, `configs/pipeline_contracts.yaml` | Конфигурация |
| 2 | **Хардкод пайплайнов в run_pipeline.py** | Обход DI, дублирование путей | `run_pipeline.py` | Техдолг |
| 3 | **HTTP-сессии в interfaces** | Нарушение Ports & Adapters | `interfaces/composition_root.py:178-182` | Слоистая архитектура |
| 4 | **PipelineContainer как god object** | 369 строк, 18+ методов | `application/container.py` | Модульность |
| 5 | **CompositionRoot слишком сложный** | 566 строк, смешение ответственностей | `interfaces/composition_root.py` | Модульность |
| 6 | **Глобальные синглтоны** (29 файлов) | Скрытые зависимости, проблемы тестов | Разные файлы | DI/Конфигурация |
| 7 | **Отсутствие обработки ошибок в RunPipelineUseCase** | Необработанные исключения | `application/use_cases/run_pipeline.py` | Устойчивость |
| 8 | **CLI зависит от глобальных реестров** | Затруднено тестирование | `interfaces/cli/app.py` | Ports & Adapters |

---

## Сводная архитектурная оценка

> Усреднённая оценка по 9 архитектурным обзорам

| Категория | Описание | Вес | Текущий балл | После рефакторинга |
|-----------|----------|-----|--------------|-------------------|
| Слоистая архитектура | Чёткость разделения domain/application/infrastructure | 0.15 | 7.5 | 8.5 |
| Ports & Adapters / DDD | Наличие портов, явность границ контекстов | 0.10 | 7.0 | 8.5 |
| Модульность и связность | Разбиение на модули, отсутствие god objects | 0.10 | 6.5 | 8.0 |
| Конфигурация и DI | Единый источник, отсутствие глобального состояния | 0.10 | 6.5 | 8.0 |
| Обработка ошибок | Политики ошибок, fail-fast, типизированные исключения | 0.10 | 6.5 | 7.5 |
| Логирование и наблюдаемость | Единообразие логов/метрик | 0.08 | 7.0 | 7.5 |
| Тестирование и QA-гейты | Архитектурные тесты, покрытие | 0.10 | 7.5 | 8.5 |
| Документация и стандарты | Правила и путеводители | 0.10 | 8.0 | 8.5 |
| Доменная модель | Контракты, схемы, Value Objects | 0.10 | 7.0 | 7.5 |
| Технический долг | Синглтоны, дублирование, обратная совместимость | 0.07 | 6.0 | 8.0 |
| **Итого** | | **1.0** | **~7.0** | **~8.5** |

**Уровень 7.0:** Архитектура в целом зрелая, но требует упорядочивания и снижения долга.

---

## Фаза 1: Устранение дублирования контрактов (P0)

**Цель:** Единый источник правды для контрактов пайплайнов.
**Ожидаемый эффект:** +0.7 к интегральному баллу

### Задача 1.1: Единый источник контрактов пайплайнов

**Проблема:**
Контракты пайплайнов дублируются между YAML и hardcoded словарём `PIPELINE_CONTRACTS`.

**Файлы:**
- `src/bioetl/domain/schemas/pipeline_contracts.py` (строки 84-115)
- `configs/pipeline_contracts.yaml`

**Текущее состояние:**
```python
# domain/schemas/pipeline_contracts.py
PIPELINE_CONTRACTS: dict[str, PipelineSchemaModel] = {
    "chembl.activity": PipelineSchemaModel(
        pipeline_code="chembl.activity",
        schema_out="activity",
        schema_in="activity_input",
        output_schema="activity_output",
    ),
    # ... дублирует данные из YAML
}
```

**Решение:**
1. Удалить `PIPELINE_CONTRACTS` словарь из доменного слоя
2. Сделать `PipelineContractLoaderPortABC` обязательным (убрать fallback)
3. Обновить `get_pipeline_contract()` для выброса исключения если loader не настроен
4. Добавить валидацию в bootstrap приложения

**Шаги выполнения:**

```bash
# 1. Проверить использование PIPELINE_CONTRACTS
grep -r "PIPELINE_CONTRACTS" src/ tests/

# 2. Обновить get_pipeline_contract() - убрать fallback
# 3. Удалить PIPELINE_CONTRACTS из pipeline_contracts.py
# 4. Обновить архитектурные тесты
# 5. Запустить тесты
pytest tests/architecture/ -v
```

**Затрагиваемые файлы:**
- `src/bioetl/domain/schemas/pipeline_contracts.py`
- `src/bioetl/infrastructure/config/pipeline_contract_loader.py`
- `src/bioetl/interfaces/composition_root.py`
- `tests/architecture/test_contracts_sync.py`

**Критерии готовности:**
- [ ] `PIPELINE_CONTRACTS` удалён из кода
- [ ] Архитектурный тест запрещает hardcoded контракты в domain
- [ ] Все тесты проходят с единым YAML источником
- [ ] Добавление нового пайплайна требует только изменения YAML

**Риски и смягчение:**
- **Риск:** Потеря обратной совместимости
- **Смягчение:** Deprecation warning в текущей версии + миграционный период (1 релиз)

---

### Задача 1.2: Убрать хардкод пайплайнов в run_pipeline.py

**Проблема:**
Словарь `PIPELINES` в `run_pipeline.py` дублирует информацию из конфигов и registry.

**Текущее состояние:**
```python
# run_pipeline.py (строки 17-43)
PIPELINES = {
    "activity": {
        "name": "activity_chembl",
        "config": "configs/pipelines/chembl/activity.yaml",
        "output": "data/output/chembl/activity",
    },
    # ... хардкод для каждого пайплайна
}
```

**Решение:**
1. Создать функцию `discover_pipelines()` в interfaces слое
2. Генерировать список пайплайнов из `configs/pipeline_contracts.yaml`
3. Использовать конвенцию для путей: `configs/pipelines/{provider}/{entity}.yaml`
4. Добавить `--list` команду в CLI для вывода доступных пайплайнов

**Новый файл:** `src/bioetl/interfaces/factories/pipeline_discovery.py`

```python
def discover_pipelines() -> dict[str, PipelineInfo]:
    """Discover pipelines from contract registry.

    Returns pipeline info based on:
    - configs/pipeline_contracts.yaml for pipeline codes
    - Convention: configs/pipelines/{provider}/{entity}.yaml
    """
    contracts = load_pipeline_contracts()
    pipelines = {}
    for code in contracts:
        provider, entity = code.split(".")
        pipelines[entity] = PipelineInfo(
            name=f"{entity}_{provider}",
            config=f"configs/pipelines/{provider}/{entity}.yaml",
            output=f"data/output/{provider}/{entity}",
        )
    return pipelines
```

**Затрагиваемые файлы:**
- `run_pipeline.py`
- `src/bioetl/interfaces/cli/app.py`
- `src/bioetl/interfaces/factories/pipeline_discovery.py` (новый)

**Критерии готовности:**
- [ ] `run_pipeline.py` не содержит статического `PIPELINES` словаря
- [ ] CLI `--list` выводит пайплайны из registry
- [ ] Добавление нового пайплайна не требует изменения Python кода

---

### Задача 1.3: Удаление ConfigMigrator прокси из домена

**Проблема:**
Файл `src/bioetl/domain/configs/migration.py` содержит динамический импорт из infrastructure.

**Текущее состояние:**
```python
# src/bioetl/domain/configs/migration.py:32-34
mod = importlib.import_module(
    ".".join(["bioetl", "infrastructure", "config", "migration"])
)
return getattr(mod, "ConfigMigrator")
```

**Шаги выполнения:**
```bash
# 1. Проверить внешние зависимости на старый путь
grep -r "from bioetl.domain.configs.migration import" src/ tests/

# 2. Удалить deprecated модуль
rm src/bioetl/domain/configs/migration.py

# 3. Обновить __init__.py (удалить __getattr__ для ConfigMigrator)

# 4. Запустить архитектурные тесты
pytest tests/architecture/test_domain_boundaries.py -v
```

**Критерии готовности:**
- [ ] Файл `domain/configs/migration.py` удалён
- [ ] Архитектурный тест `test_domain_has_no_dynamic_infrastructure_imports` проходит

---

## Фаза 2: Изоляция интерфейсного слоя (P1)

**Цель:** Interfaces слой не должен напрямую импортировать инфраструктуру.
**Ожидаемый эффект:** +0.5 к интегральному баллу

### Задача 2.1: Делегировать создание HTTP-сессий инфраструктурной фабрике

**Проблема:**
`CompositionRoot` напрямую импортирует `requests.Session` (строки 178-182).

**Текущее состояние:**
```python
# interfaces/composition_root.py:178-182
def _get_http_session_factory(self) -> type:
    if self._http_session_factory is None:
        import requests  # Нарушение: interfaces импортирует infrastructure библиотеку
        return requests.Session
    return self._http_session_factory
```

**Решение:**
1. Создать `HttpSessionFactoryABC` в `domain/ports/http.py`
2. Реализовать `RequestsHttpSessionFactory` в `infrastructure/clients/base/`
3. Инжектировать фабрику через `InfrastructureFactoryABC`
4. Убрать импорт `requests` из interfaces слоя

**Новые файлы:**
- `src/bioetl/domain/ports/http_session.py`

```python
from abc import ABC, abstractmethod
from typing import Any

class HttpSessionFactoryABC(ABC):
    """Port for creating HTTP sessions."""

    @abstractmethod
    def create_session(self) -> Any:
        """Create a new HTTP session instance."""
        ...
```

**Затрагиваемые файлы:**
- `src/bioetl/domain/ports/http_session.py` (новый)
- `src/bioetl/infrastructure/clients/base/factories.py`
- `src/bioetl/interfaces/composition_root.py`
- `src/bioetl/interfaces/factories/infrastructure.py`

**Критерии готовности:**
- [ ] Архитектурный тест: interfaces не импортирует `requests`
- [ ] `CompositionRoot` использует только `InfrastructureFactoryABC`
- [ ] Тесты HTTP можно запускать с mock-фабрикой

---

### Задача 2.2: Изолировать UseCaseFactory от инфраструктурных зависимостей

**Проблема:**
`UseCaseFactory` в interfaces импортирует конкретные инфраструктурные фабрики.

**Файл:** `src/bioetl/interfaces/use_case_factory.py`

**Решение:**
1. Переместить создание use cases в `CompositionRoot`
2. `UseCaseFactory` должен получать готовые зависимости через конструктор
3. Убрать прямые импорты infrastructure из interfaces (кроме composition_root)

**Критерии готовности:**
- [ ] `UseCaseFactory` не импортирует из infrastructure
- [ ] Архитектурный тест подтверждает изоляцию
- [ ] Тесты use cases работают без infrastructure mock

---

## Фаза 3: Декомпозиция god objects (P1)

**Цель:** Уменьшить размер и сложность ключевых классов.
**Ожидаемый эффект:** +1.3 к интегральному баллу

### Задача 3.1: Декомпозировать PipelineContainer

**Проблема:**
`PipelineContainer` (369 строк) объединяет слишком много ответственностей.

**Файл:** `src/bioetl/application/container.py`

**Текущие ответственности (18+ методов):**
- Управление конфигурацией
- Создание сервисов (extraction, normalization)
- Создание transform компонентов (hash, timestamp, index)
- Управление record source
- Runtime компоненты (hooks, error policy)
- Schema contract resolution

**Решение:** Разбить на специализированные под-контейнеры:

```
PipelineContainer (фасад, ~150 строк)
├── _service_container: ServiceContainer
│   ├── get_extraction_service()
│   ├── get_normalization_service()
│   └── get_entity_model_registry()
├── _transform_container: TransformContainer
│   ├── get_hash_service()
│   ├── get_index_generator()
│   └── get_timestamp_provider()
├── _runtime_container: RuntimeContainer
│   ├── get_hooks()
│   └── get_error_policy()
└── _validation_container: ValidationContainer
    ├── get_validation_service()
    └── get_schema_contract()
```

**Новые файлы:**
- `src/bioetl/application/containers/service_container.py`
- `src/bioetl/application/containers/transform_container.py`
- `src/bioetl/application/containers/runtime_container.py`
- `src/bioetl/application/containers/validation_container.py`

**Критерии готовности:**
- [ ] `PipelineContainer` < 150 строк
- [ ] Каждый под-контейнер < 100 строк
- [ ] Цикломатическая сложность снижена на 40%
- [ ] Все существующие тесты проходят

---

### Задача 3.2: Декомпозировать CompositionRoot

**Проблема:**
`CompositionRoot` (566 строк) смешивает создание разных типов зависимостей.

**Файл:** `src/bioetl/interfaces/composition_root.py`

**Текущие ответственности:**
- Provider Registry (строки 117-147)
- Observability (строки 153-166)
- HTTP Infrastructure (строки 172-232)
- Schema Contract Provider (строки 238-267)
- Config Migration (строки 273-299)
- Pipeline Container (строки 305-374)
- Config Loader (строки 376-408)

**Решение:** Разбить на специализированные roots:

```
CompositionRoot (координатор, ~200 строк)
├── _observability: ObservabilityRoot
│   ├── get_logger()
│   ├── get_metrics()
│   └── get_observability_stack()
├── _infrastructure: InfrastructureRoot
│   ├── create_http_session()
│   ├── create_http_transport()
│   └── create_rate_limiter()
├── _configuration: ConfigurationRoot
│   ├── get_schema_contract_provider()
│   ├── create_config_loader()
│   └── create_config_migration_service()
└── _providers: ProviderRoot
    ├── get_provider_registry()
    └── create_pipeline_container()
```

**Новые файлы:**
- `src/bioetl/interfaces/roots/observability_root.py`
- `src/bioetl/interfaces/roots/infrastructure_root.py`
- `src/bioetl/interfaces/roots/configuration_root.py`
- `src/bioetl/interfaces/roots/provider_root.py`

**Критерии готовности:**
- [ ] `CompositionRoot` < 200 строк
- [ ] Каждый специализированный root < 150 строк
- [ ] Тесты можно писать для каждого root отдельно

---

### Задача 3.3: Разделить ответственности PipelineBase

**Проблема:**
`PipelineBase` (26+ KB) объединяет оркестрацию и трансформации.

**Файл:** `src/bioetl/application/pipelines/base.py`

**Решение:**
1. Выделить `PipelineOrchestrator` для координации stages
2. Выделить `StageExecutor` для выполнения отдельных stages
3. Оставить `PipelineBase` как Template Method с минимальной логикой

**Структура:**
```
PipelineBase (Template Method, ~300 строк)
├── _orchestrator: PipelineOrchestrator (~200 строк)
│   ├── run_stages()
│   └── handle_errors()
└── _executor: StageExecutor (~150 строк)
    ├── execute_extract()
    ├── execute_transform()
    └── execute_load()
```

**Критерии готовности:**
- [ ] `PipelineBase` < 300 строк
- [ ] `PipelineOrchestrator` < 200 строк
- [ ] Unit-тесты для каждого компонента отдельно

---

## Фаза 4: Устранение глобальных синглтонов (P2)

**Цель:** Централизовать управление состоянием в ApplicationContext.
**Ожидаемый эффект:** +0.8 к интегральному баллу

### Задача 4.1: Централизовать управление синглтонами

**Проблема:**
29 файлов содержат глобальные синглтоны/ContextVar.

**Ключевые файлы:**
| Файл | Синглтон | Тип |
|------|----------|-----|
| `domain/schemas/registry.py` | `_default_registry` | Global |
| `domain/services/entity_factory.py` | `_entity_factory` | Global |
| `infrastructure/chembl/model_registry.py` | `_default_registry` | Global |
| `infrastructure/observability/server.py` | `_default_manager` | Global |
| `domain/schemas/pipeline_contracts.py` | `_CONTRACT_LOADER_CTX` | ContextVar |
| `application/pipelines/registry.py` | `PIPELINE_REGISTRY` | Dict |

**Решение:**
1. Переместить все singleton accessor'ы в `ApplicationContext`
2. Добавить `reset()` методы для тестирования
3. Использовать `ContextVar` только где необходима изоляция async контекста
4. Пометить глобальные `get_*()` функции `@deprecated`

**Пример миграции:**
```python
# До:
from bioetl.domain.schemas.registry import get_default_registry
registry = get_default_registry()

# После:
from bioetl.interfaces.application_context import get_application_context
registry = get_application_context().schema_registry
```

**Критерии готовности:**
- [ ] Глобальные функции помечены `@deprecated`
- [ ] `ApplicationContext` предоставляет все сервисы
- [ ] Тесты используют `reset_application_context()` для изоляции
- [ ] Параллельные тесты (`pytest -n auto`) проходят без конфликтов

---

### Задача 4.2: Инвертировать зависимости CLI от глобальных реестров

**Проблема:**
CLI напрямую использует `PIPELINE_REGISTRY` и `get_application_context()`.

**Файлы:**
- `src/bioetl/interfaces/cli/app.py`
- `src/bioetl/application/pipelines/registry.py`

**Решение:**
1. CLI получает реестр через DI (параметр команды или context)
2. Добавить `PipelineRegistryABC` порт в domain
3. Реализовать `InMemoryPipelineRegistry` в infrastructure
4. Инжектировать через `CompositionRoot`

**Критерии готовности:**
- [ ] CLI не импортирует `PIPELINE_REGISTRY` напрямую
- [ ] Unit-тесты CLI с mock registry
- [ ] Архитектурный тест на запрет прямого доступа к реестру

---

## Фаза 5: Обработка ошибок и устойчивость (P2)

**Цель:** Типизированные исключения и graceful degradation.
**Ожидаемый эффект:** +0.7 к интегральному баллу

### Задача 5.1: Ввести доменное исключение для ошибок валидации

**Проблема:**
`ValidationService` возвращает общие `ValueError`.

**Файл:** `src/bioetl/domain/validation/service.py`

**Решение:**
1. Создать `ValidationError(DomainError)` с категоризацией
2. Добавить поля: `field_name`, `validation_type`, `details`
3. Обновить `ValidationService` для выброса типизированных ошибок

**Новый файл:** `src/bioetl/domain/validation/errors.py`

```python
from enum import Enum
from dataclasses import dataclass
from typing import Any

class ValidationErrorType(Enum):
    SCHEMA_MISMATCH = "schema_mismatch"
    TYPE_ERROR = "type_error"
    CONSTRAINT_VIOLATION = "constraint_violation"
    MISSING_FIELD = "missing_field"

@dataclass
class ValidationError(DomainError):
    """Typed validation error with detailed context."""
    field_name: str | None
    validation_type: ValidationErrorType
    details: dict[str, Any]
```

**Критерии готовности:**
- [ ] Все ошибки валидации типизированы
- [ ] Логирование включает категорию ошибки
- [ ] Метрики по типам ошибок

---

### Задача 5.2: Ввести политику обработки ошибок в RunPipelineUseCase

**Проблема:**
`RunPipelineUseCase` не перехватывает исключения оркестратора.

**Файл:** `src/bioetl/application/use_cases/run_pipeline.py`

**Решение:**
1. Обернуть выполнение в try-except
2. Конвертировать исключения в структурированный `RunResult`
3. Добавить политику retry для recoverable ошибок
4. Логировать с correlation ID

```python
class RunPipelineUseCase:
    def execute(self, pipeline_id: str) -> RunResult:
        try:
            return self._execute_pipeline(pipeline_id)
        except RecoverableError as e:
            return self._handle_recoverable_error(e)
        except DomainError as e:
            return self._handle_domain_error(e)
        except Exception as e:
            return self._handle_unexpected_error(e)
```

**Критерии готовности:**
- [ ] Все исключения конвертируются в `RunResult`
- [ ] Retry для сетевых ошибок
- [ ] Correlation ID в логах

---

## Фаза 6: Документация и архитектурные тесты (P3)

**Цель:** Синхронизировать документацию и усилить автоматический контроль.
**Ожидаемый эффект:** +0.5 к интегральному баллу

### Задача 6.1: Консолидировать архитектурные планы

**Проблема:**
Несколько версий планов в `docs/architecture/` создают путаницу:
- `REFACTORING_PLAN.md` (этот документ - каноничный)
- `REFACTORING_PLAN_v2.md` ... `REFACTORING_PLAN_v6.md`
- `REFACTORING_PLAN_HEXAGONAL_DDD.md`
- `REFACTORING_PLAN_MERGED.md`

**Решение:**
1. Этот документ становится каноничным источником
2. Архивировать старые версии в `docs/architecture/archive/`
3. Добавить CHANGELOG для отслеживания изменений
4. Обновить README с ссылкой на актуальный план

**Критерии готовности:**
- [ ] Один каноничный REFACTORING_PLAN.md
- [ ] Старые планы архивированы
- [ ] README обновлён

---

### Задача 6.2: Расширить архитектурные тесты

**Текущие тесты:** `tests/architecture/`
- `test_layer_dependencies.py`
- `test_domain_boundaries.py`
- `test_architecture_policies.py`

**Новые тесты:**
1. `test_no_hardcoded_contracts.py` - запрет PIPELINE_CONTRACTS в domain
2. `test_no_global_singletons.py` - запрет глобальных `get_*()` в production коде
3. `test_interfaces_isolation.py` - interfaces не импортирует requests, pandas напрямую
4. `test_composition_root_factories.py` - CompositionRoot использует только фабрики

**Критерии готовности:**
- [ ] 4+ новых архитектурных теста
- [ ] 100% прохождение тестов
- [ ] CI блокирует нарушения

---

### Задача 6.3: Добавить verbose режим в CLI

**Проблема:**
Опция `--verbose` упоминается в коде, но не объявлена в Click.

**Файл:** `src/bioetl/interfaces/cli/app.py`

**Решение:**
1. Добавить `@click.option('--verbose', '-v', is_flag=True)`
2. Пробросить в обработку ошибок
3. При verbose выводить full traceback

**Критерии готовности:**
- [ ] `--verbose` в `--help`
- [ ] Traceback при ошибках с verbose
- [ ] Unit-тест на verbose режим

---

## Метрики и тесты

### Сводная таблица метрик

| Метрика | Текущее | Целевое |
|---------|---------|---------|
| Hardcoded contracts в domain | 1 (PIPELINE_CONTRACTS) | 0 |
| Hardcoded pipelines в run_pipeline.py | 5 | 0 |
| Импорты requests в interfaces | 1 | 0 |
| Размер PipelineContainer | 369 строк | <150 строк |
| Размер CompositionRoot | 566 строк | <200 строк |
| Глобальные синглтоны | 29 файлов | 0 |
| Необработанные исключения в UseCase | да | нет |

### Архитектурные тесты для контроля

**Существующие:**
- `tests/architecture/test_layer_dependencies.py`
- `tests/architecture/test_domain_boundaries.py`
- `tests/architecture/test_architecture_policies.py`

**Новые тесты (после рефакторинга):**

```python
# tests/architecture/test_refactoring_compliance.py

def test_no_hardcoded_pipeline_contracts():
    """Domain layer should not contain PIPELINE_CONTRACTS dict."""
    from bioetl.domain.schemas import pipeline_contracts
    assert not hasattr(pipeline_contracts, 'PIPELINE_CONTRACTS')

def test_interfaces_no_requests_import():
    """Interfaces layer should not import requests directly."""
    # Scan interfaces/*.py for 'import requests'
    ...

def test_composition_root_size():
    """CompositionRoot should be under 200 lines."""
    from bioetl.interfaces.composition_root import CompositionRoot
    import inspect
    source = inspect.getsource(CompositionRoot)
    assert len(source.splitlines()) < 200

def test_pipeline_container_size():
    """PipelineContainer should be under 150 lines."""
    from bioetl.application.container import PipelineContainer
    import inspect
    source = inspect.getsource(PipelineContainer)
    assert len(source.splitlines()) < 150
```

### Связка с интегральным баллом

| Фаза | Категории улучшения | Ожидаемый рост |
|------|---------------------|----------------|
| Фаза 1 | Конфигурация, Техдолг | +0.7 |
| Фаза 2 | Слоистая архитектура, Ports & Adapters | +0.5 |
| Фаза 3 | Модульность, Связность | +1.3 |
| Фаза 4 | DI, Тестируемость | +0.8 |
| Фаза 5 | Обработка ошибок, Устойчивость | +0.7 |
| Фаза 6 | Документация, Тестирование | +0.5 |
| **Итого** | | **+4.5** → **~8.5** |

---

## Порядок выполнения

```
Фаза 1: Устранение дублирования контрактов (P0)
├── 1.1 Единый источник контрактов            [2 часа]
├── 1.2 Убрать хардкод в run_pipeline.py      [2 часа]
└── 1.3 Удаление ConfigMigrator прокси        [1 час]

Фаза 2: Изоляция интерфейсного слоя (P1)
├── 2.1 HTTP-сессии через фабрику             [2 часа]
└── 2.2 Изолировать UseCaseFactory            [1 час]

Фаза 3: Декомпозиция god objects (P1)
├── 3.1 Декомпозировать PipelineContainer     [4 часа]
├── 3.2 Декомпозировать CompositionRoot       [4 часа]
└── 3.3 Разделить PipelineBase                [4 часа]

Фаза 4: Устранение глобальных синглтонов (P2)
├── 4.1 Централизовать в ApplicationContext   [3 часа]
└── 4.2 DI для CLI                            [2 часа]

Фаза 5: Обработка ошибок (P2)
├── 5.1 Доменные ошибки валидации             [2 часа]
└── 5.2 Error handling в UseCase              [2 часа]

Фаза 6: Документация и тесты (P3)
├── 6.1 Консолидация архитектурных планов     [1 час]
├── 6.2 Новые архитектурные тесты             [2 часа]
└── 6.3 Verbose режим CLI                     [1 час]
```

### Визуализация прогресса

```
Текущий балл: ████████░░░░░░░░░░░░ 7.0/10

После Фазы 1-2: ██████████████░░░░░░ 7.7/10

После Фазы 3-4: ████████████████░░░░ 8.5/10

После Фазы 5-6: █████████████████░░░ 8.8/10
```

---

## Команды для проверки

```bash
# Архитектурные тесты (все)
pytest tests/architecture/ -v

# Проверка границ домена
pytest tests/architecture/test_domain_boundaries.py -v

# Полный набор архитектурных проверок
pytest tests/architecture/ tests/project_rules/ -v --tb=short

# Поиск дублирования контрактов
grep -r "PIPELINE_CONTRACTS" src/

# Поиск глобальных синглтонов
grep -rn "^_[A-Z].*: .* = None$" src/bioetl/

# Поиск импортов requests в interfaces
grep -r "import requests" src/bioetl/interfaces/
```

---

## Риски и смягчение

| Риск | Вероятность | Влияние | Смягчение |
|------|-------------|---------|-----------|
| Регрессии при декомпозиции | Средняя | Высокое | Покрыть тестами до изменений |
| Потеря обратной совместимости | Высокая | Среднее | Deprecation warnings, миграционный период |
| Увеличение сложности DI | Средняя | Среднее | Builder pattern для контейнеров |
| Сломанный CI | Низкая | Высокое | Feature branches, постепенный merge |

---

## Устаревшие задачи (из предыдущих версий)

> Следующие задачи были консолидированы из предыдущих версий плана.
> Они либо выполнены, либо включены в новые фазы.

### Выполненные
- ✅ Архитектурные тесты на границы слоёв
- ✅ CompositionRoot создан
- ✅ 79 ABC/Protocol контрактов определены

### Включены в новый план
- Регистрация Pandera-схем → Фаза 7 (дополнительная)
- Глобальный реестр провайдеров → Фаза 4
- Наблюдаемость → Фаза 5 + документация

---

## Ссылки

- [Domain Layer Audit](./18-domain-layer-audit.md)
- [Architecture Tests](../../tests/architecture/)
- [Infrastructure Validation Schemas](../../src/bioetl/infrastructure/validation/schemas/)
- [Domain Schema Registry](../../src/bioetl/domain/schemas/registry.py)
- [ADR Index](./decisions/0000-adr-index.md)

---

**Владелец плана:** Architecture Team
**Ревьюеры:** Lead Developers
**Дата последнего обновления:** 2025-12-11
