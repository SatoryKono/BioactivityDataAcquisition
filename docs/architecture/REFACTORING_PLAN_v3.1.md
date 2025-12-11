# Объединённый план рефакторинга архитектуры BioETL

**Версия:** 3.1 (консолидация планов v2.1 и v3.0, актуализация по кодовой базе)
**Дата создания:** 2025-12-11
**Дата обновления:** 2025-12-11

**Базовые документы:**
- План v2.1: фокус на interfaces layer и application layer инкапсуляцию
- План v3.0: фокус на гексагональность, pandas в application, детерминизм, наблюдаемость

**Текущий интегральный балл:** 6.6–7.0/10 (усреднённая оценка)
**Целевой интегральный балл:** ≥8.0/10
**Статус:** Планирование

---

## Оглавление

1. [Резюме](#резюме)
2. [Текущее состояние кодовой базы](#текущее-состояние-кодовой-базы)
3. [Консолидированная оценка архитектуры](#консолидированная-оценка-архитектуры)
4. [Полный реестр выявленных проблем](#полный-реестр-выявленных-проблем)
5. [Приоритеты рефакторинга](#приоритеты-рефакторинга)
6. [Фаза 1: Изоляция слоёв от инфраструктурных деталей](#фаза-1-изоляция-слоёв-от-инфраструктурных-деталей)
7. [Фаза 2: Порты и адаптеры для interfaces](#фаза-2-порты-и-адаптеры-для-interfaces)
8. [Фаза 3: Декомпозиция PipelineBase](#фаза-3-декомпозиция-pipelinebase)
9. [Фаза 4: Детерминизм и атомарность записи](#фаза-4-детерминизм-и-атомарность-записи)
10. [Фаза 5: Наблюдаемость и устойчивость клиентов](#фаза-5-наблюдаемость-и-устойчивость-клиентов)
11. [Фаза 6: Централизация сервисов](#фаза-6-централизация-сервисов)
12. [Фаза 7: Гибкость реестра моделей](#фаза-7-гибкость-реестра-моделей)
13. [Фаза 8: Усиление архитектурных тестов](#фаза-8-усиление-архитектурных-тестов)
14. [Метрики и контроль](#метрики-и-контроль)
15. [План выполнения](#план-выполнения)
16. [Ожидаемые результаты](#ожидаемые-результаты)
17. [Риски и митигация](#риски-и-митигация)

---

## Резюме

Данный документ объединяет несколько планов рефакторинга с различными фокусами анализа:

| План | Фокус | Ключевые проблемы |
|------|-------|-------------------|
| v2.1 | interfaces → infrastructure | 26 прямых импортов в interfaces layer, fallback в orchestrator |
| v3.0 | Гексагональность, PipelineBase | pandas в application, детерминизм записи, перегруженный PipelineBase |

### Общая картина проблем

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     ARCHITECTURE PROBLEMS MAP (актуализировано)              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  СЛОЙ APPLICATION                          СЛОЙ INTERFACES                   │
│  ════════════════                          ════════════════                   │
│                                                                              │
│  ┌─────────────────────┐                   ┌─────────────────────┐           │
│  │ 1 импорт infra      │                   │ 26 импортов infra   │           │
│  │ (orchestrator.py:67)│                   │ (8 файлов)          │           │
│  └─────────────────────┘                   └─────────────────────┘           │
│           │                                          │                       │
│           ↓                                          ↓                       │
│  ┌─────────────────────┐                   ┌─────────────────────┐           │
│  │ Приватные вызовы    │                   │ Отсутствуют порты   │           │
│  │ _get_extract_*      │                   │ application/ports/  │           │
│  │ (строки 156-159)    │                   │                     │           │
│  └─────────────────────┘                   └─────────────────────┘           │
│           │                                          │                       │
│           ↓                                          ↓                       │
│  ┌─────────────────────┐                   ┌─────────────────────┐           │
│  │ Перегруженный       │                   │ Отсутствуют адаптеры│           │
│  │ PipelineBase        │                   │ infrastructure/     │           │
│  │ (~15 параметров)    │                   │ adapters/           │           │
│  └─────────────────────┘                   └─────────────────────┘           │
│                                                                              │
│  ══════════════════════════════════════════════════════════════════════════  │
│                           ДОПОЛНИТЕЛЬНЫЕ ПРОБЛЕМЫ                            │
│  ══════════════════════════════════════════════════════════════════════════  │
│                                                                              │
│  • pandas.DataFrame в типах результатов портов (нарушение гексагональности)  │
│  • Политики детерминизма/атомарности не формализованы                        │
│  • Недостаток метрик наблюдаемости для клиентов                              │
│  • ChemblEntityModelRegistry импортирует raw-модели напрямую                 │
│  • .importlinter содержит 2 неактуальных исключения (chembl_extraction)      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Ключевые цели

1. **Изолировать application от infrastructure** — убрать fallback импорты и приватные вызовы
2. **Изолировать interfaces от infrastructure** — создать порты и адаптеры
3. **Очистить application-слой от pandas** — усилить гексагональность
4. **Декомпозировать PipelineBase** — разделить обязанности на конфигураторы и стадии
5. **Усилить детерминизм записи** — предотвратить регресс в воспроизводимости артефактов
6. **Стандартизировать наблюдаемость** — централизовать метрики, логи, retries/timeout
7. **Очистить .importlinter** — удалить неактуальные исключения, добавить строгие правила

---

## Текущее состояние кодовой базы

### ✅ Уже реализовано

| Компонент | Статус | Комментарий |
|-----------|--------|-------------|
| Глобальное состояние ProviderRegistry | ✅ DEPRECATED | `__getattr__` выдаёт warnings и AttributeError |
| Domain ports (`domain/ports/`) | ✅ Есть | 9 файлов с портами |
| Import linter контракты | ✅ Есть | 4 контракта |
| Architecture tests | ✅ Есть | 4 файла в `tests/architecture/` |
| Legacy adapters | ✅ Есть | `interfaces/legacy_adapters.py` |
| Application services | ✅ Есть | 4 файла: config_migration, filter_enrichment, schema_bootstrap, schema_contract_provider |

### 🔴 Актуальные проблемы

| Проблема | Файл | Строки | Детали |
|----------|------|--------|--------|
| Fallback InMemoryProviderRegistry | `orchestrator.py` | 58-69, 92 | Lazy import из infrastructure |
| Приватные вызовы `_get_extract_callable` | `orchestrator.py` | 156 | `noqa: SLF001` |
| Приватные вызовы `_normalize_extract_result` | `orchestrator.py` | 157-159 | `noqa: SLF001` |
| 26 импортов infrastructure в interfaces | 8 файлов | — | См. детальную таблицу ниже |
| Неактуальные исключения в .importlinter | `.importlinter` | 24-25, 37 | `chembl_extraction` не существует |

### ❌ Отсутствующие компоненты

| Компонент | Целевая директория | Статус |
|-----------|-------------------|--------|
| Application ports | `application/ports/` | ❌ Не создано |
| Infrastructure adapters | `infrastructure/adapters/` | ❌ Не создано |
| TabularDataProtocol | `domain/data/tabular.py` | ❌ Не создано |
| ExtractOnlyResult | `domain/models.py` | ❌ Не создано |
| `run_extract_only()` | `application/pipelines/base.py` | ❌ Не создано |
| PipelineConfiguration | `domain/configs/pipeline_parts.py` | ❌ Не создано |
| StageRegistry | `application/pipelines/stages/` | ❌ Не создано |
| DeterministicWriterABC | `domain/output/contracts.py` | ❌ Не создано |
| ResilientClientABC | `domain/clients/resilience.py` | ❌ Не создано |
| ObservabilityService | `application/services/` | ❌ Не создано |
| ConfigurationService | `application/services/` | ❌ Не создано |

### Детальный анализ импортов

#### Application layer (1 импорт infrastructure)

| Файл | Импорт | Строка |
|------|--------|--------|
| `orchestrator.py` | `bioetl.infrastructure.provider_registry.InMemoryProviderRegistry` | 67 |

> **Примечание:** Файл `application/services/chembl_extraction.py` **НЕ СУЩЕСТВУЕТ**.
> Исключения в `.importlinter` для этого файла неактуальны и должны быть удалены.

#### Interfaces layer (26 импортов infrastructure)

| Файл | Кол-во | Строки | Примеры импортов |
|------|:------:|--------|-----------------|
| `composition_root.py` | 10 | 56, 66, 145, 148, 263, 295, 320, 354, 395, 417 | `config.loader`, `provider_registry`, `validation.bootstrap` |
| `factories/infrastructure.py` | 4 | 82, 99, 111, 126 | `clients.base.factories`, `abc_registry_resolver` |
| `monitoring/__init__.py` | 3 | 24, 25, 26 | `observability.metrics`, `observability.factories`, `observability.server` |
| `bootstrap_factory.py` | 2 | 38, 109 | `config.loader`, `validation.bootstrap` |
| `factories/observability.py` | 2 | 36, 50 | `observability.factories` |
| `cli/app.py` | 2 | 14, 84 | `config.sources` |
| `use_case_factory.py` | 2 | 63, 66 | `config.provider_registry`, `config.sources` |
| `application_context.py` | 1 | 86 | `observability.factories` |

---

## Консолидированная оценка архитектуры

| Категория | Вес | Оценка | Взвеш. балл | Проблемы |
|-----------|:---:|:------:|:-----------:|----------|
| Слоистая архитектура | 0.12 | 6.5 | 0.78 | interfaces→infra (26), application→infra (1) |
| Ports & Adapters / DDD | 0.10 | 6 | 0.60 | Отсутствуют application/ports/, infrastructure/adapters/ |
| Модульность и связность | 0.10 | 6.5 | 0.65 | Перегруженный PipelineBase (~15 параметров) |
| Доменная модель и контракты | 0.10 | 7 | 0.70 | pandas в типах портов |
| Конфигурация и детерминизм | 0.10 | 6 | 0.60 | Политики не формализованы |
| Обработка ошибок и наблюдаемость | 0.10 | 6 | 0.60 | Нет централизованного ObservabilityService |
| Тестирование и QA | 0.10 | 6.5 | 0.65 | Тесты проверяют только `impl`, не все infra-импорты |
| Валидация данных | 0.08 | 7 | 0.56 | — |
| Производительность | 0.08 | 6 | 0.48 | — |
| Документация | 0.06 | 7 | 0.42 | — |
| Сопровождаемость | 0.06 | 6.5 | 0.39 | 3 исключения в .importlinter (2 неактуальны) |
| **Интегральный балл** | **1.00** | | **6.43** | |

---

## Полный реестр выявленных проблем

### Категория A: Нарушения слоистой архитектуры

| ID | Слой | Файл | Строка | Описание | Приоритет |
|:--:|------|------|:------:|----------|:---------:|
| A1 | application | `orchestrator.py` | 58-69, 92 | Fallback `_get_default_registry_factory()` импортирует `InMemoryProviderRegistry` | Критический |
| A2 | application | Порты | — | pandas.DataFrame в типах результатов портов | Критический |
| A3 | interfaces | `composition_root.py` | 56, 66, 145... | 10 прямых импортов infrastructure | Критический |
| A4 | interfaces | `bootstrap_factory.py` | 38, 109 | 2 прямых импорта infrastructure | Высокий |
| A5 | interfaces | `factories/infrastructure.py` | 82, 99, 111, 126 | 4 прямых импорта infrastructure | Высокий |
| A6 | interfaces | `factories/observability.py` | 36, 50 | 2 прямых импорта infrastructure | Высокий |
| A7 | interfaces | `cli/app.py` | 14, 84 | 2 прямых импорта infrastructure | Средний |
| A8 | interfaces | `use_case_factory.py` | 63, 66 | 2 прямых импорта infrastructure | Средний |
| A9 | interfaces | `application_context.py` | 86 | 1 прямой импорт infrastructure | Средний |
| A10 | interfaces | `monitoring/__init__.py` | 24-26 | 3 прямых импорта infrastructure | Средний |

### Категория B: Нарушения инкапсуляции

| ID | Файл | Строка | Описание | Приоритет |
|:--:|------|:------:|----------|:---------:|
| B1 | `orchestrator.py` | 156 | Вызов `pipeline._get_extract_callable()` с `noqa: SLF001` | Высокий |
| B2 | `orchestrator.py` | 157-159 | Вызов `pipeline._normalize_extract_result()` с `noqa: SLF001` | Высокий |

### Категория C: Проблемы связности и ответственности

| ID | Компонент | Описание | Приоритет |
|:--:|-----------|----------|:---------:|
| C1 | PipelineBase | Совмещает настройку хешей, индексов, метаданных, хуков, error policy (~15 параметров в __init__) | Высокий |
| C2 | ChemblEntityModelRegistry | Прямой импорт Pydantic raw-моделей из домена | Средний |

### Категория D: Недостатки операционных гарантий

| ID | Область | Описание | Приоритет |
|:--:|---------|----------|:---------:|
| D1 | Loader/QC | Политики детерминизма/атомарности не формализованы | Высокий |
| D2 | Клиенты | Недостаток метрик наблюдаемости, retries/timeout на уровне портов | Средний |

### Категория E: Технический долг

| ID | Файл | Описание | Приоритет |
|:--:|------|----------|:---------:|
| E1 | `.importlinter` | 2 неактуальных исключения для `chembl_extraction` (файл не существует) | Высокий |
| E2 | `domain/schemas/generator.py` | Deprecated модуль с lazy imports на Pandera/YAML | Низкий |

### Категория F: Недостающие компоненты

| ID | Описание | Приоритет |
|:--:|----------|:---------:|
| F1 | Порты в `application/ports/` | Критический |
| F2 | Адаптеры в `infrastructure/adapters/` | Критический |
| F3 | TabularDataProtocol в domain | Критический |
| F4 | ExtractOnlyResult в `domain/models.py` | Высокий |
| F5 | `run_extract_only()` в `PipelineBase` | Высокий |
| F6 | PipelineConfiguration, StageRegistry, RuntimeContext | Высокий |
| F7 | DeterministicWriterABC | Средний |
| F8 | ResilientClientABC, ClientMetricsPortABC | Средний |
| F9 | ObservabilityService, ConfigurationService | Средний |
| F10 | Тесты на все инфраструктурные импорты (не только impl) | Высокий |
| F11 | Тесты на pandas импорты в application | Средний |

---

## Приоритеты рефакторинга

```
══════════════════════════════════════════════════════════════════════════════
                           МАТРИЦА ПРИОРИТЕТОВ
══════════════════════════════════════════════════════════════════════════════

КРИТИЧЕСКИЙ (блокирует архитектурную чистоту)
┌────────────────────────────────────────────────────────────────────────────┐
│  [A1] Изолировать orchestrator от InMemoryProviderRegistry                 │
│  [A2] Исключить pandas из application-портов (TabularDataProtocol)         │
│  [A3] Устранить 26 импортов infrastructure в interfaces                    │
│  [F1-F2] Создать application/ports/ и infrastructure/adapters/             │
│  [E1] Удалить неактуальные исключения в .importlinter                      │
└────────────────────────────────────────────────────────────────────────────┘

ВЫСОКИЙ (инкапсуляция, декомпозиция, воспроизводимость)
┌────────────────────────────────────────────────────────────────────────────┐
│  [B1-B2] Публичный API для extract-only режима (run_extract_only)          │
│  [C1] Декомпозировать PipelineBase на конфигураторы и стадии               │
│  [D1] Усилить детерминизм и атомарную запись в Loader                      │
│  [F10] Усилить архитектурные тесты (все infra-импорты, не только impl)     │
└────────────────────────────────────────────────────────────────────────────┘

СРЕДНИЙ (гибкость, наблюдаемость, сервисы)
┌────────────────────────────────────────────────────────────────────────────┐
│  [C2] Провайдер raw-моделей для ChemblEntityModelRegistry                  │
│  [D2] Стандартизовать наблюдаемость и fault-tolerance клиентов             │
│  [F9] Создать ObservabilityService и ConfigurationService                  │
│  [F11] Тесты на pandas импорты в application                               │
└────────────────────────────────────────────────────────────────────────────┘

НИЗКИЙ (документация, deprecated код)
┌────────────────────────────────────────────────────────────────────────────┐
│  [E2] Deprecated generator.py (можно оставить с warnings)                  │
│  Актуализация документации после изменений                                 │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Фаза 1: Изоляция слоёв от инфраструктурных деталей

**Приоритет:** Критический
**Решает:** A1, A2, B1, B2, E1, F3, F4, F5
**Время:** ~8 часов

### Задача 1.1: Очистить .importlinter от неактуальных исключений

**Проблема:** Файл `application/services/chembl_extraction.py` **НЕ СУЩЕСТВУЕТ**, но в `.importlinter` есть 2 исключения для него.

**Файл:** `.importlinter`

**Текущий код:**
```ini
[contract:application_allowed_dependencies]
ignore_imports =
    # Lazy import for backward compatibility (provider registry factory)
    bioetl.application.orchestrator -> bioetl.infrastructure.provider_registry
    # ChEMBL extraction service compatibility facade
    bioetl.application.services.chembl_extraction -> bioetl.infrastructure.clients.chembl.impl.chembl_extraction_service_impl

[contract:application_avoids_infrastructure_implementations]
ignore_imports =
    bioetl.application.services.chembl_extraction -> bioetl.infrastructure.clients.chembl.impl.chembl_extraction_service_impl
```

**Целевой код:**
```ini
[contract:application_allowed_dependencies]
ignore_imports =
    # Lazy import for backward compatibility (provider registry factory)
    # TODO: Remove after Phase 1.2 completion
    bioetl.application.orchestrator -> bioetl.infrastructure.provider_registry

[contract:application_avoids_infrastructure_implementations]
# No exceptions needed after cleanup
```

### Задача 1.2: Удаление fallback в PipelineOrchestrator

**Файл:** `src/bioetl/application/orchestrator.py`

**Текущий код (строки 58-69, 92):**
```python
def _get_default_registry_factory() -> ProviderRegistryFactory:
    """Get the default provider registry factory."""
    from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry
    return InMemoryProviderRegistry

class PipelineOrchestrator:
    def __init__(
        self,
        ...
        provider_registry_factory: ProviderRegistryFactory | None = None,
    ) -> None:
        self._provider_registry_factory = (
            provider_registry_factory or _get_default_registry_factory()
        )
```

**Целевой код:**
```python
class PipelineOrchestrator:
    def __init__(
        self,
        ...
        provider_registry_factory: ProviderRegistryFactory,  # обязательный!
    ) -> None:
        self._provider_registry_factory = provider_registry_factory
```

### Задача 1.3: Фабрика провайдера в interfaces

**Создать:** `src/bioetl/interfaces/factories/provider_registry.py`

```python
"""Provider registry factory for composition root."""
from __future__ import annotations

from bioetl.domain.provider_registry import ProviderRegistryFactory


def create_provider_registry_factory() -> ProviderRegistryFactory:
    """Create the default provider registry factory.

    This is the single place where infrastructure is imported for DI.
    """
    from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry
    return InMemoryProviderRegistry
```

### Задача 1.4: TabularDataProtocol для гексагональности

**Проблема:** Application-слой использует `pandas.DataFrame` в типах результатов, что смешивает порт и инфраструктурные детали.

**Создать:** `src/bioetl/domain/data/tabular.py`

```python
"""Tabular data abstraction for hexagonal architecture."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterator, Protocol, runtime_checkable

if TYPE_CHECKING:
    pass


@runtime_checkable
class TabularDataProtocol(Protocol):
    """Protocol for tabular data abstraction.

    This allows application layer to work with tabular data
    without depending on pandas directly.
    """

    @property
    def columns(self) -> list[str]:
        """Return column names."""
        ...

    @property
    def shape(self) -> tuple[int, int]:
        """Return (rows, columns) shape."""
        ...

    def __len__(self) -> int:
        """Return number of rows."""
        ...

    def iterrows(self) -> Iterator[tuple[int, dict[str, Any]]]:
        """Iterate over rows as (index, dict) pairs."""
        ...

    def to_dict(self, orient: str = "records") -> list[dict[str, Any]] | dict[str, Any]:
        """Convert to dictionary representation."""
        ...
```

**Создать адаптер:** `src/bioetl/infrastructure/adapters/pandas_tabular.py`

```python
"""Pandas adapter for TabularDataProtocol."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterator

if TYPE_CHECKING:
    import pandas as pd

from bioetl.domain.data.tabular import TabularDataProtocol


class PandasTabularAdapter:
    """Adapter wrapping pandas DataFrame to TabularDataProtocol."""

    def __init__(self, df: "pd.DataFrame"):
        self._df = df

    @property
    def columns(self) -> list[str]:
        return list(self._df.columns)

    @property
    def shape(self) -> tuple[int, int]:
        return self._df.shape

    def __len__(self) -> int:
        return len(self._df)

    def iterrows(self) -> Iterator[tuple[int, dict[str, Any]]]:
        for idx, row in self._df.iterrows():
            yield idx, row.to_dict()

    def to_dict(self, orient: str = "records") -> list[dict[str, Any]] | dict[str, Any]:
        return self._df.to_dict(orient=orient)

    @property
    def underlying(self) -> "pd.DataFrame":
        """Access underlying DataFrame for infrastructure operations."""
        return self._df
```

### Задача 1.5: Публичный API для extract-only режима

**Добавить в:** `src/bioetl/domain/models.py`

```python
@dataclass(frozen=True)
class ExtractOnlyResult:
    """Result of extract-only pipeline execution."""
    total_rows: int
    total_chunks: int
```

**Добавить в:** `src/bioetl/application/pipelines/base.py`

```python
from bioetl.domain.models import ExtractOnlyResult


class PipelineBase(ABC):
    # ... существующие методы ...

    def run_extract_only(self, **kwargs: Any) -> ExtractOnlyResult:
        """Execute only the extract stage and return statistics.

        This method provides a clean public API for extract-only mode,
        encapsulating the internal extraction logic.

        Args:
            **kwargs: Arguments passed to the extract stage.

        Returns:
            ExtractOnlyResult with row count and chunk count.
        """
        extract_callable = self._get_extract_callable()
        iterator = self._normalize_extract_result(extract_callable(**kwargs))

        total_rows = 0
        total_chunks = 0

        for chunk in iterator:
            if chunk is None:
                continue
            total_rows += len(chunk)
            total_chunks += 1

        return ExtractOnlyResult(
            total_rows=total_rows,
            total_chunks=max(total_chunks, 1),
        )
```

**Обновить:** `src/bioetl/application/orchestrator.py` (строки 153-194)

```python
# БЫЛО:
if effective_type == PipelineType.EXTRACT_ONLY:
    context = self._build_simple_context()
    extract_callable = pipeline._get_extract_callable()  # noqa: SLF001
    iterator = pipeline._normalize_extract_result(
        extract_callable()
    )  # noqa: SLF001
    # ... подсчёт строк ...

# СТАНЕТ:
if effective_type == PipelineType.EXTRACT_ONLY:
    context = self._build_simple_context()
    extract_result = pipeline.run_extract_only()  # Публичный API!

    stage = StageResult(
        stage_name=StageName.EXTRACT,
        success=True,
        records_processed=extract_result.total_rows,
        chunks_processed=extract_result.total_chunks,
        duration_sec=0.0,
        errors=[],
    )
    # ...
```

### Критерии готовности Фазы 1

- [ ] Неактуальные исключения удалены из `.importlinter`
- [ ] В `application/orchestrator.py` нет импортов `bioetl.infrastructure.*`
- [ ] Функция `_get_default_registry_factory()` удалена
- [ ] `provider_registry_factory` — обязательный параметр конструктора
- [ ] `TabularDataProtocol` создан в `domain/data/`
- [ ] `PandasTabularAdapter` создан в `infrastructure/adapters/`
- [ ] `ExtractOnlyResult` добавлен в `domain/models.py`
- [ ] Метод `run_extract_only()` добавлен в `PipelineBase`
- [ ] Orchestrator использует публичный API (без `noqa: SLF001`)
- [ ] Все тесты проходят
- [ ] `lint-imports` проходит

---

## Фаза 2: Порты и адаптеры для interfaces

**Приоритет:** Критический
**Решает:** A3–A10, F1–F2
**Время:** ~6 часов

### Задача 2.1: Создать порты в application слое

**Структура:**
```
src/bioetl/application/ports/
├── __init__.py
├── config_loader_port.py          # ConfigLoaderPortABC
├── infrastructure_factory_port.py  # InfrastructureFactoryPortABC
└── observability_factory_port.py   # ObservabilityFactoryPortABC
```

**Файл:** `src/bioetl/application/ports/config_loader_port.py`

```python
"""Port for configuration loading operations."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from bioetl.domain.configs.pipeline import PipelineConfig


class ConfigLoaderPortABC(ABC):
    """Abstract port for loading pipeline configurations."""

    @abstractmethod
    def get_by_id(
        self,
        pipeline_id: str,
        *,
        profile: str | None = None,
        cli_overrides: dict[str, Any] | None = None,
        env_overrides: dict[str, Any] | None = None,
    ) -> PipelineConfig:
        """Load pipeline config by ID (e.g., 'chembl.activity')."""
        ...

    @abstractmethod
    def get_from_path(
        self,
        config_path: Path,
        *,
        profile: str | None = None,
        cli_overrides: dict[str, Any] | None = None,
    ) -> PipelineConfig:
        """Load pipeline config from explicit file path."""
        ...


class ConfigPathResolverPortABC(ABC):
    """Abstract port for resolving configuration paths."""

    @abstractmethod
    def get_configs_root(self) -> Path:
        """Return root directory for configurations."""
        ...

    @abstractmethod
    def resolve_pipeline_path(self, pipeline_id: str) -> Path:
        """Resolve path for a pipeline ID."""
        ...
```

**Файл:** `src/bioetl/application/ports/infrastructure_factory_port.py`

```python
"""Port for infrastructure component factories."""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.clients.base.contracts import HttpClientABC, RateLimiterABC


class InfrastructureFactoryPortABC(ABC):
    """Abstract factory for infrastructure components."""

    @abstractmethod
    def create_http_client(self, base_url: str, **kwargs) -> "HttpClientABC":
        """Create HTTP client instance."""
        ...

    @abstractmethod
    def create_rate_limiter(
        self, requests_per_second: float, **kwargs
    ) -> "RateLimiterABC":
        """Create rate limiter instance."""
        ...


class ABCRegistryResolverPortABC(ABC):
    """Abstract port for resolving ABC implementations."""

    @abstractmethod
    def resolve(self, abc_name: str) -> type:
        """Resolve implementation class for given ABC name."""
        ...

    @abstractmethod
    def resolve_instance(self, abc_name: str, **kwargs) -> object:
        """Resolve and instantiate implementation for given ABC name."""
        ...
```

**Файл:** `src/bioetl/application/ports/observability_factory_port.py`

```python
"""Port for observability component factories."""
from abc import ABC, abstractmethod

from bioetl.domain.observability.contracts import (
    LoggingPortABC,
    MetricsPortABC,
)


class ObservabilityFactoryPortABC(ABC):
    """Abstract factory for observability components."""

    @abstractmethod
    def create_logger(self) -> LoggingPortABC:
        """Create structured logger instance."""
        ...

    @abstractmethod
    def create_metrics(self) -> MetricsPortABC:
        """Create metrics collector instance."""
        ...
```

### Задача 2.2: Создать адаптеры в infrastructure слое

**Структура:**
```
src/bioetl/infrastructure/adapters/
├── __init__.py
├── config_loader_adapter.py
├── infrastructure_factory_adapter.py
├── observability_factory_adapter.py
└── pandas_tabular.py  # из Фазы 1.4
```

**Файл:** `src/bioetl/infrastructure/adapters/config_loader_adapter.py`

```python
"""Infrastructure adapter for config loading port."""
from pathlib import Path
from typing import Any

from bioetl.application.ports.config_loader_port import (
    ConfigLoaderPortABC,
    ConfigPathResolverPortABC,
)
from bioetl.domain.configs.pipeline import PipelineConfig


class ConfigLoaderAdapter(ConfigLoaderPortABC):
    """Adapter implementing config loader port."""

    def __init__(self, schema_contract_provider):
        self._provider = schema_contract_provider

    def get_by_id(
        self,
        pipeline_id: str,
        *,
        profile: str | None = None,
        cli_overrides: dict[str, Any] | None = None,
        env_overrides: dict[str, Any] | None = None,
    ) -> PipelineConfig:
        from bioetl.infrastructure.config.loader import get_pipeline_config

        return get_pipeline_config(
            pipeline_id,
            schema_contract_provider=self._provider,
            profile=profile,
            cli_overrides=cli_overrides or {},
            env_overrides=env_overrides or {},
        )

    def get_from_path(
        self,
        config_path: Path,
        *,
        profile: str | None = None,
        cli_overrides: dict[str, Any] | None = None,
    ) -> PipelineConfig:
        from bioetl.infrastructure.config.loader import get_pipeline_config_from_path

        return get_pipeline_config_from_path(
            config_path,
            schema_contract_provider=self._provider,
            profile=profile,
            cli_overrides=cli_overrides or {},
        )


class ConfigPathResolverAdapter(ConfigPathResolverPortABC):
    """Adapter implementing config path resolver port."""

    def __init__(self, base_dir: Path | None = None):
        self._base_dir = base_dir

    def get_configs_root(self) -> Path:
        from bioetl.infrastructure.config.sources import get_configs_root

        return get_configs_root(self._base_dir)

    def resolve_pipeline_path(self, pipeline_id: str) -> Path:
        from bioetl.infrastructure.config.sources import resolve_pipeline_config_path

        return resolve_pipeline_config_path(pipeline_id, self._base_dir)
```

### Задача 2.3: Рефакторинг CompositionRoot

**Файл:** `src/bioetl/interfaces/composition_root.py`

```python
# БЫЛО (26 прямых импортов infrastructure):
from bioetl.infrastructure.config.loader import SchemaContractLoader
from bioetl.infrastructure.config.sources import get_configs_root
# ... ещё импорты

# СТАНЕТ (импорты только портов из application):
from bioetl.application.ports.config_loader_port import (
    ConfigLoaderPortABC,
    ConfigPathResolverPortABC,
)
from bioetl.application.ports.infrastructure_factory_port import (
    InfrastructureFactoryPortABC,
    ABCRegistryResolverPortABC,
)
from bioetl.application.ports.observability_factory_port import (
    ObservabilityFactoryPortABC,
)


class CompositionRoot:
    """Dependency injection composition root."""

    def __init__(
        self,
        *,
        config_loader: ConfigLoaderPortABC | None = None,
        config_resolver: ConfigPathResolverPortABC | None = None,
        infrastructure_factory: InfrastructureFactoryPortABC | None = None,
        observability_factory: ObservabilityFactoryPortABC | None = None,
        abc_resolver: ABCRegistryResolverPortABC | None = None,
    ):
        # Lazy initialization - adapters created only when needed
        self._config_loader = config_loader
        self._config_resolver = config_resolver
        self._infrastructure_factory = infrastructure_factory
        self._observability_factory = observability_factory
        self._abc_resolver = abc_resolver

    def get_config_loader(self) -> ConfigLoaderPortABC:
        if self._config_loader is None:
            # Lazy import adapter only when actually needed
            from bioetl.infrastructure.adapters.config_loader_adapter import (
                ConfigLoaderAdapter,
            )
            self._config_loader = ConfigLoaderAdapter(
                self._get_schema_contract_provider()
            )
        return self._config_loader

    # ... остальные методы аналогично
```

### Задача 2.4: Рефакторинг остальных interfaces файлов

| Файл | Действие |
|------|----------|
| `bootstrap_factory.py` | Использовать `ConfigLoaderPortABC` через CompositionRoot |
| `factories/infrastructure.py` | Перенести функционал в адаптеры, использовать порты |
| `factories/observability.py` | Перенести функционал в адаптеры, использовать порты |
| `cli/app.py` | Использовать `CompositionRoot` |
| `use_case_factory.py` | Использовать порты из `CompositionRoot` |
| `application_context.py` | Получать зависимости из `CompositionRoot` |
| `monitoring/__init__.py` | Использовать `ObservabilityFactoryPortABC` |

### Критерии готовности Фазы 2

- [ ] Все порты созданы в `application/ports/`
- [ ] Все адаптеры созданы в `infrastructure/adapters/`
- [ ] `CompositionRoot` использует только порты
- [ ] Interfaces импортирует infrastructure только через lazy init адаптеров
- [ ] Количество прямых импортов infrastructure в interfaces: ≤3
- [ ] Все тесты проходят

---

## Фаза 3: Декомпозиция PipelineBase

**Приоритет:** Высокий
**Решает:** C1, F6
**Время:** ~6 часов

### Проблема

PipelineBase совмещает множество обязанностей (~15 параметров в __init__):
- Настройка логирования
- Конфигурация хешей
- Управление индексами
- Обработка метаданных
- Error policy
- Runtime manager

### Решение: Выделить конфигураторы и стадии

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         ДЕКОМПОЗИЦИЯ PIPELINEBASE                        │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  БЫЛО (монолитный класс):                                                │
│  ┌────────────────────────────────────────────────┐                      │
│  │              PipelineBase                       │                      │
│  │  ├── __init__() — ~15 параметров               │                      │
│  │  ├── _setup_logging()                          │                      │
│  │  ├── _setup_hashing()                          │                      │
│  │  ├── _setup_indexes()                          │                      │
│  │  ├── _setup_metadata()                         │                      │
│  │  ├── _setup_error_policy()                     │                      │
│  │  └── _setup_runtime_manager()                  │                      │
│  └────────────────────────────────────────────────┘                      │
│                                                                          │
│  СТАНЕТ (композиция):                                                    │
│  ┌────────────────────────────────────────────────┐                      │
│  │              PipelineBase                       │                      │
│  │  ├── config: PipelineConfiguration             │ ← Value Object       │
│  │  ├── stages: StageRegistry                     │ ← Реестр стадий      │
│  │  └── runtime: RuntimeContext                   │ ← Контекст выполнения│
│  └────────────────────────────────────────────────┘                      │
│                         │                                                │
│       ┌─────────────────┼─────────────────┐                              │
│       ↓                 ↓                 ↓                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────────┐                        │
│  │ Pipeline │    │  Stage   │    │   Runtime    │                        │
│  │ Config   │    │ Registry │    │   Context    │                        │
│  └──────────┘    └──────────┘    └──────────────┘                        │
│       │                │                 │                               │
│  ┌────┴────┐      ┌────┴────┐       ┌────┴────┐                          │
│  │HashConf │      │Extract  │       │ErrorPol │                          │
│  │IndexConf│      │Transform│       │Logger   │                          │
│  │MetaConf │      │Validate │       │Metrics  │                          │
│  └─────────┘      │Write    │       └─────────┘                          │
│                   └─────────┘                                            │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Задача 3.1: Создать PipelineConfiguration

**Создать:** `src/bioetl/domain/configs/pipeline_parts.py`

```python
"""Pipeline configuration parts for composition."""
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class HashingConfiguration:
    """Configuration for hashing behavior."""
    business_key_columns: tuple[str, ...]
    hash_algorithm: str = "sha256"
    include_nulls: bool = False


@dataclass(frozen=True)
class IndexConfiguration:
    """Configuration for index management."""
    primary_index: str | None = None
    secondary_indexes: tuple[str, ...] = ()


@dataclass(frozen=True)
class MetadataConfiguration:
    """Configuration for metadata handling."""
    include_source_timestamp: bool = True
    include_source_index: bool = True
    custom_fields: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PipelineConfiguration:
    """Aggregated pipeline configuration."""
    hashing: HashingConfiguration
    indexing: IndexConfiguration
    metadata: MetadataConfiguration
```

### Задача 3.2: Создать StageRegistry

**Создать:** `src/bioetl/application/pipelines/stages/registry.py`

```python
"""Stage registry for pipeline composition."""
from abc import ABC, abstractmethod
from typing import Any, TypeVar

T = TypeVar("T")


class StageABC(ABC):
    """Abstract base for pipeline stages."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stage name for logging and metrics."""
        ...

    @abstractmethod
    def execute(self, context: "RuntimeContext", data: T) -> T:
        """Execute stage logic."""
        ...


class StageRegistry:
    """Registry of pipeline stages."""

    def __init__(self):
        self._stages: dict[str, StageABC] = {}

    def register(self, stage: StageABC) -> None:
        self._stages[stage.name] = stage

    def get(self, name: str) -> StageABC | None:
        return self._stages.get(name)

    def all(self) -> list[StageABC]:
        return list(self._stages.values())
```

### Задача 3.3: Создать RuntimeContext

**Создать:** `src/bioetl/application/pipelines/context.py`

```python
"""Runtime context for pipeline execution."""
from dataclasses import dataclass, field
from typing import Any

from bioetl.domain.observability.contracts import LoggingPortABC, MetricsPortABC
from bioetl.domain.pipelines.error_policy import ErrorPolicyABC


@dataclass
class RuntimeContext:
    """Runtime context for pipeline execution."""

    run_id: str
    logger: LoggingPortABC
    metrics: MetricsPortABC
    error_policy: ErrorPolicyABC
    state: dict[str, Any] = field(default_factory=dict)

    def with_stage(self, stage_name: str) -> "RuntimeContext":
        """Create child context bound to specific stage."""
        return RuntimeContext(
            run_id=self.run_id,
            logger=self.logger.bind(stage=stage_name),
            metrics=self.metrics,
            error_policy=self.error_policy,
            state={**self.state, "current_stage": stage_name},
        )
```

### Задача 3.4: Рефакторинг PipelineBase

**Обновить:** `src/bioetl/application/pipelines/base.py`

```python
class PipelineBase(ABC):
    """Simplified pipeline base with composition."""

    def __init__(
        self,
        config: PipelineConfiguration,
        stages: StageRegistry,
        context_factory: Callable[[], RuntimeContext],
    ):
        self._config = config
        self._stages = stages
        self._context_factory = context_factory

    def run(self, **kwargs: Any) -> RunResult:
        """Execute all registered stages."""
        context = self._context_factory()
        data = None

        for stage in self._stages.all():
            stage_context = context.with_stage(stage.name)
            data = stage.execute(stage_context, data)

        return self._build_result(context, data)

    # Сохранить run_extract_only() из Фазы 1.5
```

### Критерии готовности Фазы 3

- [ ] `PipelineConfiguration` создан с подконфигами
- [ ] `StageRegistry` создан и используется
- [ ] `RuntimeContext` создан
- [ ] `PipelineBase.__init__` упрощён до 3-4 параметров
- [ ] Все существующие пайплайны адаптированы
- [ ] Backward compatibility через адаптеры
- [ ] Тесты проходят

---

## Фаза 4: Детерминизм и атомарность записи

**Приоритет:** Высокий
**Решает:** D1, F7
**Время:** ~5 часов

### Проблема

Политики детерминизма/атомарности не формализованы в слоях записи и QC-отчётов.

### Задача 4.1: Формализовать контракты детерминизма

**Создать:** `src/bioetl/domain/output/deterministic.py`

```python
"""Contracts for deterministic file writing."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from bioetl.domain.data.tabular import TabularDataProtocol


@dataclass(frozen=True)
class WriteResult:
    """Result of deterministic write operation."""
    path: Path
    checksum: str
    row_count: int
    is_atomic: bool


class DeterministicWriterABC(ABC):
    """Contract for deterministic file writing."""

    @abstractmethod
    def write_atomic(
        self,
        data: TabularDataProtocol,
        target_path: Path,
        *,
        sort_columns: tuple[str, ...] | None = None,
        reset_index: bool = True,
    ) -> WriteResult:
        """Write data atomically with deterministic output.

        Guarantees:
        1. Output is byte-for-byte identical for same input
        2. Write is atomic (temp file + rename)
        3. Checksum is computed and returned
        """
        ...

    @abstractmethod
    def verify_checksum(self, path: Path, expected: str) -> bool:
        """Verify file checksum matches expected value."""
        ...
```

### Задача 4.2: Реализовать детерминистичную сортировку

**Создать:** `src/bioetl/infrastructure/output/deterministic.py`

```python
"""Deterministic Parquet writer with atomic operations."""
import hashlib
import tempfile
from pathlib import Path

from bioetl.domain.data.tabular import TabularDataProtocol
from bioetl.domain.output.deterministic import DeterministicWriterABC, WriteResult


class DeterministicParquetWriter(DeterministicWriterABC):
    """Deterministic Parquet writer with atomic operations."""

    def write_atomic(
        self,
        data: TabularDataProtocol,
        target_path: Path,
        *,
        sort_columns: tuple[str, ...] | None = None,
        reset_index: bool = True,
    ) -> WriteResult:
        import pandas as pd

        # Get underlying DataFrame
        if hasattr(data, "underlying"):
            df = data.underlying
        else:
            df = pd.DataFrame(data.to_dict(orient="records"))

        # 1. Сортировка для детерминизма
        if sort_columns:
            df = df.sort_values(list(sort_columns)).reset_index(drop=True)
        elif reset_index:
            df = df.reset_index(drop=True)

        # 2. Запись во временный файл
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=target_path.parent,
            suffix=".tmp",
            delete=False,
        ) as tmp:
            temp_path = Path(tmp.name)

        df.to_parquet(temp_path, index=False)

        # 3. Вычисление checksum
        checksum = self._compute_checksum(temp_path)

        # 4. Атомарное переименование
        temp_path.rename(target_path)

        return WriteResult(
            path=target_path,
            checksum=checksum,
            row_count=len(df),
            is_atomic=True,
        )

    def verify_checksum(self, path: Path, expected: str) -> bool:
        actual = self._compute_checksum(path)
        return actual == expected

    def _compute_checksum(self, path: Path) -> str:
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
```

### Задача 4.3: Golden-тесты для детерминизма

**Создать:** `tests/golden/test_deterministic_output.py`

```python
"""Golden tests for output determinism."""
import pytest
from pathlib import Path

from bioetl.domain.output.deterministic import DeterministicWriterABC


class TestDeterministicOutput:
    """Golden tests for output determinism."""

    def test_identical_input_produces_identical_output(
        self,
        deterministic_writer: DeterministicWriterABC,
        sample_data,
        tmp_path: Path,
    ):
        """Same input should produce byte-identical output."""
        path1 = tmp_path / "output1.parquet"
        path2 = tmp_path / "output2.parquet"

        result1 = deterministic_writer.write_atomic(sample_data, path1)
        result2 = deterministic_writer.write_atomic(sample_data, path2)

        assert result1.checksum == result2.checksum
        assert path1.read_bytes() == path2.read_bytes()

    def test_shuffled_input_produces_same_sorted_output(
        self,
        deterministic_writer: DeterministicWriterABC,
        sample_data,
        shuffled_data,
        tmp_path: Path,
    ):
        """Shuffled input with same content should produce identical output."""
        path1 = tmp_path / "sorted1.parquet"
        path2 = tmp_path / "sorted2.parquet"

        result1 = deterministic_writer.write_atomic(
            sample_data, path1, sort_columns=("id",)
        )
        result2 = deterministic_writer.write_atomic(
            shuffled_data, path2, sort_columns=("id",)
        )

        assert result1.checksum == result2.checksum
```

### Критерии готовности Фазы 4

- [ ] `DeterministicWriterABC` контракт создан
- [ ] `DeterministicParquetWriter` реализован
- [ ] Атомарная запись через temp + rename
- [ ] Golden-тесты на детерминизм добавлены
- [ ] Все существующие writer'ы используют детерминистичный подход

---

## Фаза 5: Наблюдаемость и устойчивость клиентов

**Приоритет:** Средний
**Решает:** D2, F8
**Время:** ~5 часов

### Проблема

Недостаток метрик наблюдаемости и политик retries/timeout на уровне портов.

### Задача 5.1: Формализовать контракты устойчивости

**Создать:** `src/bioetl/domain/clients/resilience.py`

```python
"""Resilience contracts for external clients."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    """Policy for retry behavior."""
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    exponential_base: float = 2.0
    retryable_exceptions: tuple[type[Exception], ...] = (ConnectionError, TimeoutError)


@dataclass(frozen=True)
class TimeoutPolicy:
    """Policy for timeout behavior."""
    connect_timeout_seconds: float = 10.0
    read_timeout_seconds: float = 30.0
    total_timeout_seconds: float = 300.0


@dataclass(frozen=True)
class CircuitBreakerPolicy:
    """Policy for circuit breaker behavior."""
    failure_threshold: int = 5
    recovery_timeout_seconds: float = 60.0
    half_open_requests: int = 3


class ResilientClientABC(ABC, Generic[T]):
    """Contract for resilient external client."""

    @abstractmethod
    def execute_with_resilience(
        self,
        operation: Callable[[], T],
        *,
        retry_policy: RetryPolicy | None = None,
        timeout_policy: TimeoutPolicy | None = None,
    ) -> T:
        """Execute operation with retry and timeout handling."""
        ...
```

### Задача 5.2: Расширить метрики клиентов

**Создать:** `src/bioetl/domain/observability/client_metrics.py`

```python
"""Client metrics contracts."""
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True)
class ClientMetrics:
    """Metrics for external client operations."""
    requests_total: int
    requests_success: int
    requests_failed: int
    retries_total: int
    latency_seconds_avg: float
    latency_seconds_p95: float
    latency_seconds_p99: float


class ClientMetricsPortABC(ABC):
    """Port for collecting client metrics."""

    @abstractmethod
    def record_request(
        self,
        client_name: str,
        operation: str,
        *,
        success: bool,
        latency_seconds: float,
        retry_count: int = 0,
    ) -> None:
        """Record metrics for a single request."""
        ...

    @abstractmethod
    def get_metrics(self, client_name: str) -> ClientMetrics:
        """Get aggregated metrics for client."""
        ...

    @abstractmethod
    @contextmanager
    def timed_operation(
        self,
        client_name: str,
        operation: str,
    ) -> Iterator[None]:
        """Context manager for timing operations."""
        ...
```

### Критерии готовности Фазы 5

- [ ] `RetryPolicy`, `TimeoutPolicy`, `CircuitBreakerPolicy` созданы
- [ ] `ResilientClientABC` контракт создан
- [ ] `ClientMetricsPortABC` создан
- [ ] Существующие клиенты обёрнуты в resilient-адаптеры
- [ ] Метрики latency/error rate собираются

---

## Фаза 6: Централизация сервисов

**Приоритет:** Средний
**Решает:** F9
**Время:** ~4 часа

### Задача 6.1: ObservabilityService

**Создать:** `src/bioetl/application/services/observability_service.py`

```python
"""Unified observability service for application layer."""
from dataclasses import dataclass
from typing import Any

from bioetl.application.ports.observability_factory_port import (
    ObservabilityFactoryPortABC,
)
from bioetl.domain.observability.contracts import (
    LoggingPortABC,
    MetricsPortABC,
)


@dataclass
class ObservabilityContext:
    """Concrete observability context implementation."""

    _logger: LoggingPortABC
    _metrics: MetricsPortABC
    _bound_context: dict[str, Any]

    @property
    def logger(self) -> LoggingPortABC:
        return self._logger.bind(**self._bound_context)

    @property
    def metrics(self) -> MetricsPortABC:
        return self._metrics

    def with_context(self, **kwargs) -> "ObservabilityContext":
        new_context = {**self._bound_context, **kwargs}
        return ObservabilityContext(
            _logger=self._logger,
            _metrics=self._metrics,
            _bound_context=new_context,
        )


class ObservabilityService:
    """Service for creating and managing observability contexts."""

    def __init__(self, factory: ObservabilityFactoryPortABC):
        self._factory = factory
        self._logger: LoggingPortABC | None = None
        self._metrics: MetricsPortABC | None = None

    def create_context(self, **initial_context) -> ObservabilityContext:
        """Create new observability context with optional initial bindings."""
        if self._logger is None:
            self._logger = self._factory.create_logger()
        if self._metrics is None:
            self._metrics = self._factory.create_metrics()

        return ObservabilityContext(
            _logger=self._logger,
            _metrics=self._metrics,
            _bound_context=initial_context,
        )

    def create_pipeline_context(
        self,
        pipeline_id: str,
        run_id: str,
    ) -> ObservabilityContext:
        """Create context specifically for pipeline execution."""
        return self.create_context(
            pipeline_id=pipeline_id,
            run_id=run_id,
        )
```

### Задача 6.2: ConfigurationService

**Создать:** `src/bioetl/application/services/configuration_service.py`

```python
"""Centralized configuration service for application layer."""
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bioetl.application.ports.config_loader_port import (
    ConfigLoaderPortABC,
    ConfigPathResolverPortABC,
)
from bioetl.domain.configs.pipeline import PipelineConfig


@dataclass(frozen=True)
class ConfigurationRequest:
    """Request for loading configuration."""
    pipeline_id: str | None = None
    config_path: Path | None = None
    profile: str | None = None
    cli_overrides: dict[str, Any] | None = None
    env_overrides: dict[str, Any] | None = None


class ConfigurationService:
    """Centralized service for all configuration operations."""

    def __init__(
        self,
        loader: ConfigLoaderPortABC,
        path_resolver: ConfigPathResolverPortABC,
    ):
        self._loader = loader
        self._path_resolver = path_resolver

    def load(self, request: ConfigurationRequest) -> PipelineConfig:
        """Load configuration based on request parameters."""
        if request.config_path:
            return self._loader.get_from_path(
                request.config_path,
                profile=request.profile,
                cli_overrides=request.cli_overrides,
            )

        if request.pipeline_id:
            return self._loader.get_by_id(
                request.pipeline_id,
                profile=request.profile,
                cli_overrides=request.cli_overrides,
                env_overrides=request.env_overrides,
            )

        raise ValueError("Either pipeline_id or config_path must be provided")

    def get_configs_root(self) -> Path:
        """Get root directory for configurations."""
        return self._path_resolver.get_configs_root()

    def list_available_pipelines(self) -> list[str]:
        """List all available pipeline IDs."""
        configs_root = self.get_configs_root()
        pipelines = []

        for provider_dir in configs_root.iterdir():
            if provider_dir.is_dir() and not provider_dir.name.startswith("_"):
                for config_file in provider_dir.glob("*.yaml"):
                    pipeline_id = f"{provider_dir.name}.{config_file.stem}"
                    pipelines.append(pipeline_id)

        return sorted(pipelines)
```

### Критерии готовности Фазы 6

- [ ] `ObservabilityService` создан и интегрирован
- [ ] `ConfigurationService` создан и интегрирован
- [ ] CLI использует ConfigurationService
- [ ] Use cases используют ObservabilityService

---

## Фаза 7: Гибкость реестра моделей

**Приоритет:** Средний
**Решает:** C2
**Время:** ~3 часа

### Проблема

`ChemblEntityModelRegistry` напрямую импортирует Pydantic raw-модели из домена.

### Задача 7.1: Создать провайдер raw-моделей

**Создать:** `src/bioetl/domain/schemas/model_provider.py`

```python
"""Abstract provider for raw API models."""
from abc import ABC, abstractmethod
from typing import Type

from pydantic import BaseModel


class RawModelProviderABC(ABC):
    """Abstract provider for raw API models."""

    @abstractmethod
    def get_model(self, entity_name: str) -> Type[BaseModel]:
        """Get raw model class by entity name."""
        ...

    @abstractmethod
    def list_entities(self) -> list[str]:
        """List all available entity names."""
        ...

    @abstractmethod
    def supports(self, entity_name: str) -> bool:
        """Check if provider supports given entity."""
        ...
```

### Задача 7.2: Реализовать ChEMBL провайдер

**Создать:** `src/bioetl/infrastructure/chembl/model_provider.py`

```python
"""Provider for ChEMBL raw API models."""
from typing import Type

from pydantic import BaseModel

from bioetl.domain.schemas.model_provider import RawModelProviderABC


class ChemblRawModelProvider(RawModelProviderABC):
    """Provider for ChEMBL raw API models."""

    def __init__(self):
        self._models: dict[str, type] | None = None

    def _load_models(self) -> dict[str, type]:
        if self._models is None:
            from bioetl.domain.schemas.chembl.raw_models import (
                ActivityRaw,
                AssayRaw,
                MoleculeRaw,
                TargetRaw,
                PublicationRaw,
            )
            self._models = {
                "activity": ActivityRaw,
                "assay": AssayRaw,
                "molecule": MoleculeRaw,
                "target": TargetRaw,
                "publication": PublicationRaw,
            }
        return self._models

    def get_model(self, entity_name: str) -> Type[BaseModel]:
        models = self._load_models()
        if entity_name not in models:
            raise KeyError(f"Unknown entity: {entity_name}")
        return models[entity_name]

    def list_entities(self) -> list[str]:
        return list(self._load_models().keys())

    def supports(self, entity_name: str) -> bool:
        return entity_name in self._load_models()
```

### Критерии готовности Фазы 7

- [ ] `RawModelProviderABC` создан в domain
- [ ] `ChemblRawModelProvider` реализован
- [ ] `ChemblEntityModelRegistry` использует провайдер
- [ ] Добавление нового провайдера не требует правки реестра

---

## Фаза 8: Усиление архитектурных тестов

**Приоритет:** Высокий
**Решает:** F10, F11
**Время:** ~3 часа

### Задача 8.1: Тест на все инфраструктурные импорты в application

**Обновить:** `tests/architecture/test_layer_dependencies.py`

```python
# Whitelist: разрешённые инфраструктурные импорты (должен быть пустым!)
APPLICATION_ALLOWED_INFRA_IMPORTS: set[str] = set()


def test_application_has_no_infrastructure_imports() -> None:
    """Verify application layer has no direct infrastructure imports.

    This is stricter than test_application_avoids_infrastructure_implementations
    which only checks for 'impl' modules. This test catches ANY infrastructure
    import.
    """
    violations: list[str] = []

    for file_path in sorted(APPLICATION_ROOT.rglob("*.py")):
        for reference in _collect_imports(file_path):
            if not reference.module.startswith("bioetl.infrastructure"):
                continue

            if reference.module in APPLICATION_ALLOWED_INFRA_IMPORTS:
                continue

            violations.append(
                _format_violation(
                    file_path,
                    reference.lineno,
                    f"application must not import infrastructure "
                    f"(found {reference.module})",
                )
            )

    _assert_no_violations(violations)
```

### Задача 8.2: Тест на pandas импорты в application

```python
def test_application_has_no_pandas_imports() -> None:
    """Verify application layer doesn't import pandas directly.

    Application should use TabularDataProtocol instead of pandas.DataFrame.
    """
    violations: list[str] = []

    for file_path in sorted(APPLICATION_ROOT.rglob("*.py")):
        for reference in _collect_imports(file_path):
            if reference.module.startswith("pandas"):
                violations.append(
                    _format_violation(
                        file_path,
                        reference.lineno,
                        "application must not import pandas directly "
                        "(use TabularDataProtocol instead)",
                    )
                )

    _assert_no_violations(violations)
```

### Задача 8.3: Тест на инфраструктурные импорты в interfaces

```python
INTERFACES_ALLOWED_INFRA_IMPORTS: dict[str, set[str]] = {
    # Only adapters allowed via lazy import in composition_root.py
    "composition_root.py": {
        "bioetl.infrastructure.adapters",
    }
}


def test_interfaces_has_limited_infrastructure_imports() -> None:
    """Verify interfaces layer only imports allowed infrastructure modules."""
    violations: list[str] = []

    for file_path in sorted(INTERFACES_ROOT.rglob("*.py")):
        allowed = INTERFACES_ALLOWED_INFRA_IMPORTS.get(file_path.name, set())

        for reference in _collect_imports(file_path):
            if not reference.module.startswith("bioetl.infrastructure"):
                continue

            # Check if import is from allowed modules
            if any(reference.module.startswith(a) for a in allowed):
                continue

            violations.append(
                _format_violation(
                    file_path,
                    reference.lineno,
                    f"interfaces must not import infrastructure directly "
                    f"(found {reference.module})",
                )
            )

    _assert_no_violations(violations)
```

### Задача 8.4: Тест на приватные атрибуты

```python
import re

PRIVATE_ATTR_PATTERN = re.compile(r"(?<!self)(?<!cls)\._[a-z_]+\(")


def test_no_cross_module_private_access() -> None:
    """Verify no module accesses private attributes of other modules.

    This catches patterns like:
    - pipeline._get_extract_callable()
    - service._internal_method()
    """
    violations: list[str] = []

    for file_path in sorted(APPLICATION_ROOT.rglob("*.py")):
        content = file_path.read_text(encoding="utf-8")

        for line_no, line in enumerate(content.splitlines(), 1):
            # Skip self._ and cls._ accesses
            if "self._" in line or "cls._" in line:
                continue

            matches = PRIVATE_ATTR_PATTERN.findall(line)
            if matches:
                violations.append(
                    _format_violation(
                        file_path,
                        line_no,
                        f"cross-module private attribute access: {matches}",
                    )
                )

    _assert_no_violations(violations)
```

### Задача 8.5: Обновление .importlinter

**Файл:** `.importlinter` (после всех фаз)

```ini
[importlinter]
root_package = bioetl

[contract:domain_purity]
name = Domain depends only on itself and shared/stdlib utilities
type = forbidden
source_modules =
    bioetl.domain
forbidden_modules =
    bioetl.application
    bioetl.infrastructure
    bioetl.interfaces

[contract:application_no_infrastructure]
name = Application must not import infrastructure
type = forbidden
source_modules =
    bioetl.application
forbidden_modules =
    bioetl.infrastructure

[contract:application_no_pandas]
name = Application must not import pandas (use TabularDataProtocol)
type = forbidden
source_modules =
    bioetl.application
forbidden_modules =
    pandas

[contract:infrastructure_no_upper_layers]
name = Infrastructure imports domain (and stdlib) but not higher layers
type = forbidden
source_modules =
    bioetl.infrastructure
forbidden_modules =
    bioetl.application
    bioetl.interfaces

[contract:interfaces_uses_adapters_only]
name = Interfaces layer must import infrastructure only through adapters
type = forbidden
source_modules =
    bioetl.interfaces
forbidden_modules =
    bioetl.infrastructure.config
    bioetl.infrastructure.clients
    bioetl.infrastructure.logging
    bioetl.infrastructure.observability
    bioetl.infrastructure.validation
    bioetl.infrastructure.provider_registry
    bioetl.infrastructure.output
    bioetl.infrastructure.chembl
# Разрешены только:
# bioetl.infrastructure.adapters.*
```

### Критерии готовности Фазы 8

- [ ] Тест `test_application_has_no_infrastructure_imports` добавлен и проходит
- [ ] Тест `test_application_has_no_pandas_imports` добавлен и проходит
- [ ] Тест `test_interfaces_has_limited_infrastructure_imports` добавлен и проходит
- [ ] Тест `test_no_cross_module_private_access` добавлен и проходит
- [ ] `.importlinter` обновлён с новыми контрактами
- [ ] Количество `ignore_imports`: 0
- [ ] CI блокирует регресс

---

## Метрики и контроль

### Метрики качества кода

| Метрика | Текущее | Целевое | Команда проверки |
|---------|:-------:|:-------:|------------------|
| infrastructure импорты в application | 1 | 0 | `grep -rn "bioetl.infrastructure" src/bioetl/application/` |
| pandas импорты в application | >0 | 0 | `grep -rn "import pandas" src/bioetl/application/` |
| infrastructure импорты в interfaces | 26 | ≤3 | `grep -rn "bioetl.infrastructure" src/bioetl/interfaces/` |
| Приватные вызовы (cross-module) | 2 | 0 | `grep -rn "noqa: SLF001" src/bioetl/application/` |
| Параметры конструктора PipelineBase | ~15 | ≤5 | Ручная проверка |
| ignore_imports в .importlinter | 3 | 0 | Подсчёт строк |
| Архитектурные тесты | pass | pass | `pytest tests/architecture/ -v` |

### Метрики детерминизма

| Метрика | Текущее | Целевое |
|---------|:-------:|:-------:|
| Golden-тесты | 0 | ≥10 |
| Атомарные записи | частично | 100% |

### Полная проверка

```bash
# Все проверки одной командой
pytest tests/architecture/ tests/project_rules/ -v && \
grep -rn "bioetl.infrastructure" src/bioetl/application/ && \
grep -rn "import pandas" src/bioetl/application/ && \
grep -rn "noqa: SLF001" src/bioetl/application/ && \
lint-imports
```

---

## План выполнения

```
══════════════════════════════════════════════════════════════════════════════
                         ОБЩИЙ ПЛАН ВЫПОЛНЕНИЯ
══════════════════════════════════════════════════════════════════════════════

ФАЗА 1: Изоляция слоёв от инфраструктурных деталей        [~8 ч]
├── 1.1 Очистить .importlinter от неактуальных исключений  [0.5 ч]
├── 1.2 Удаление fallback в orchestrator                   [1.5 ч]
├── 1.3 Фабрика провайдера в interfaces                    [1 ч]
├── 1.4 TabularDataProtocol для гексагональности           [2.5 ч]
└── 1.5 Публичный API для extract-only                     [2.5 ч]

ФАЗА 2: Порты и адаптеры для interfaces                   [~6 ч]
├── 2.1 Создать порты в application/ports/                 [2 ч]
├── 2.2 Создать адаптеры в infrastructure/adapters/        [2 ч]
├── 2.3 Рефакторинг CompositionRoot                        [1.5 ч]
└── 2.4 Рефакторинг остальных interfaces файлов            [0.5 ч]

ФАЗА 3: Декомпозиция PipelineBase                         [~6 ч]
├── 3.1 Создать PipelineConfiguration                      [1.5 ч]
├── 3.2 Создать StageRegistry                              [1.5 ч]
├── 3.3 Создать RuntimeContext                             [1.5 ч]
└── 3.4 Рефакторинг PipelineBase                           [1.5 ч]

ФАЗА 4: Детерминизм и атомарность записи                  [~5 ч]
├── 4.1 Формализовать контракты детерминизма               [1.5 ч]
├── 4.2 Реализовать детерминистичную сортировку            [2 ч]
└── 4.3 Golden-тесты для детерминизма                      [1.5 ч]

ФАЗА 5: Наблюдаемость и устойчивость клиентов             [~5 ч]
├── 5.1 Формализовать контракты устойчивости               [2 ч]
└── 5.2 Расширить метрики клиентов                         [3 ч]

ФАЗА 6: Централизация сервисов                            [~4 ч]
├── 6.1 ObservabilityService                               [2 ч]
└── 6.2 ConfigurationService                               [2 ч]

ФАЗА 7: Гибкость реестра моделей                          [~3 ч]
├── 7.1 Создать провайдер raw-моделей                      [1 ч]
└── 7.2 Реализовать ChEMBL провайдер                       [2 ч]

ФАЗА 8: Усиление архитектурных тестов                     [~3 ч]
├── 8.1 Тест на все инфраструктурные импорты               [0.5 ч]
├── 8.2 Тест на pandas импорты                             [0.5 ч]
├── 8.3 Тест на инфраструктурные импорты в interfaces      [0.5 ч]
├── 8.4 Тест на приватные атрибуты                         [0.5 ч]
└── 8.5 Обновление .importlinter                           [1 ч]

══════════════════════════════════════════════════════════════════════════════
                     ИТОГО: ~40 часов
══════════════════════════════════════════════════════════════════════════════

РЕКОМЕНДУЕМЫЙ ПОРЯДОК:
──────────────────────────────────────────────────────────────────────────────
  Фаза 1 → Фаза 2 → Фаза 8 (частично) → Фаза 3 → Фаза 4 → Фаза 5 → Фаза 6 → Фаза 7 → Фаза 8

  Логика:
  1. Критические нарушения слоистости (Фазы 1-2)
  2. Архитектурные тесты для фиксации (Фаза 8.1-8.4)
  3. Декомпозиция для упрощения дальнейших изменений (Фаза 3)
  4. Операционные гарантии (Фазы 4-5)
  5. Сервисы и гибкость (Фазы 6-7)
  6. Финализация тестов и .importlinter (Фаза 8.5)
```

---

## Ожидаемые результаты

### Прогноз изменения оценок

| Категория | Текущая | После фаз 1-2 | После фаз 1-4 | После всех фаз | Δ |
|-----------|:-------:|:-------------:|:-------------:|:--------------:|:-:|
| Слоистая архитектура | 6.5 | 8 | 8.5 | 9 | +2.5 |
| Ports & Adapters | 6 | 7.5 | 8 | 8.5 | +2.5 |
| Модульность и связность | 6.5 | 7 | 8 | 8.5 | +2 |
| Доменная модель | 7 | 7.5 | 7.5 | 8 | +1 |
| Конфигурация и детерминизм | 6 | 6.5 | 8 | 8 | +2 |
| Наблюдаемость | 6 | 6 | 6.5 | 7.5 | +1.5 |
| Тестирование и QA | 6.5 | 7 | 7.5 | 8 | +1.5 |
| Сопровождаемость | 6.5 | 7.5 | 8 | 8.5 | +2 |

### Прогноз интегрального балла

| Этап | Балл | Изменение |
|------|:----:|:---------:|
| Текущий | 6.43 | — |
| После Фазы 1 | ~6.9 | +0.47 |
| После Фаз 1-2 | ~7.3 | +0.87 |
| После Фаз 1-4 | ~7.7 | +1.27 |
| После всех фаз | **≥8.0** | +1.57 |

---

## Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|:-----------:|:-------:|-----------|
| Поломка пайплайнов при изменении PipelineBase | Высокая | Высокое | Поэтапная миграция, адаптеры совместимости |
| Поломка вызовов orchestrator | Высокая | Среднее | Deprecation warnings на 1-2 релиза |
| Регрессия детерминизма | Средняя | Высокое | Golden-тесты, CI блокирует изменения хешей |
| Ложные срабатывания архитектурных тестов | Средняя | Низкое | Whitelist для допустимых случаев |
| Несовместимость с internal CLI | Средняя | Среднее | Обновить CLI вместе с composition root |
| Усложнение DI | Низкая | Низкое | Документирование графа зависимостей |
| Потеря производительности | Низкая | Низкое | Lazy initialization адаптеров |

### Стратегия миграции

1. **Фаза deprecation:** Добавить warnings в устаревший код
   ```python
   warnings.warn(
       "Using default registry factory is deprecated. "
       "Pass provider_registry_factory explicitly.",
       DeprecationWarning,
       stacklevel=3,
   )
   ```

2. **Фаза обновления:** Обновить все точки входа на явный DI

3. **Фаза удаления:** Удалить deprecated код, сделать параметры обязательными

---

## Ссылки

- [REFACTORING_PLAN_MERGED.md](./REFACTORING_PLAN_MERGED.md) — предыдущая объединённая версия
- [REFACTORING_PLAN_v5.md](./REFACTORING_PLAN_v5.md) — план v5 (application layer)
- [architecture.md](./architecture.md) — текущая архитектура
- [DEPENDENCY_FLOW.md](./DEPENDENCY_FLOW.md) — граф зависимостей
- [PipelineOrchestrator](../../src/bioetl/application/orchestrator.py)
- [PipelineBase](../../src/bioetl/application/pipelines/base.py)
- [CompositionRoot](../../src/bioetl/interfaces/composition_root.py)
- [test_layer_dependencies.py](../../tests/architecture/test_layer_dependencies.py)
