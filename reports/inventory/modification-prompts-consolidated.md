# Промпты для модификации кода — BioETL Refactoring

**Дата:** 2026-02-15 (обновлено после мержа main)
**Источник:** consolidated-refactoring-plan.md

Каждый промпт самодостаточен и может быть передан агенту для автономного выполнения.
Порядок соответствует фазам из плана рефакторинга.

---

## Фаза 1: Quick Wins

---

### PROMPT 1.1 — DEAD-001: Удалить 9 мёртвых объектов

```
Задача: Удалить 9 верифицированных мёртвых объектов из кодовой базы BioETL.
Каждый объект имеет 0 ссылок за пределами строки определения (перепроверено grep-ом).

Удалить ТОЛЬКО указанные строки. НЕ трогать окружающий код, импорты, функции.

1. src/bioetl/domain/validation.py — строка ~412
   Удалить: `VALIDATION_API = (validate_publication_year, validate_inchi_key)`
   Это последняя строка файла. Оставить trailing newline.
   НЕ удалять сами функции validate_publication_year и validate_inchi_key — они активны.

2. src/bioetl/application/core/entity_id.py — строки ~36-51
   Удалить: всю функцию `compute_subcellular_fraction_entity_id` (def + docstring + body).
   Это последняя функция в файле. Оставить trailing newline.
   Если функция упомянута в `__all__` этого файла или в
   application/core/__init__.py — удалить оттуда тоже.

3. src/bioetl/application/pipelines/pubmed/xml_parser.py — строка ~79
   Удалить: `PARSER_HELPERS = (get_text, get_int)`
   Это последняя строка файла. НЕ удалять функции get_text и get_int.

4. src/bioetl/infrastructure/adapters/http/circuit_breaker.py — строка ~235
   Удалить: `CIRCUIT_BREAKER_HELPERS = (is_circuit_breaker_error,)`
   Это последняя строка файла.

5. src/bioetl/infrastructure/observability/metrics.py — строки ~220-221
   Удалить 2 строки:
     # Expose for tooling to avoid false dead-code flags.
     METRICS_COLLECTOR = MetricsCollector
   Это последние 2 строки файла.

6. src/bioetl/infrastructure/observability/logging.py — строка ~52
   Удалить: `LOGGING_API = (create_logger,)`
   Расположена между функцией create_logger и классом StructlogLogger.
   Оставить пустую строку между функцией и классом.

7. src/bioetl/composition/bootstrap_logger.py — строка ~140
   Удалить: `BOOTSTRAP_LOGGER_EXPORTS = (BootstrapLogger, reset_bootstrap_logger)`
   Расположена между классом BootstrapLogger и списком __all__.
   Оставить пустую строку между классом и __all__.

8. src/bioetl/interfaces/cli/exit_codes.py — строка ~120
   Удалить: `EXIT_CODE_HELPERS = (get_exit_code_for_exception,)`
   Расположена между функцией и __all__.
   Оставить пустую строку между функцией и __all__.

9. src/bioetl/interfaces/http/health_server.py — строка ~305
   Удалить: `RUN_HEALTH_SERVER = run_health_server`
   Расположена между функцией run_health_server и __all__.
   Оставить пустую строку между функцией и __all__.

Верификация после удаления:
  ruff check src/bioetl/ --select F401
  pytest tests/architecture/ -v
  pytest tests/ -x --timeout=120

Для каждого удалённого имени проверить что 0 оставшихся ссылок:
  grep -rn "VALIDATION_API\|PARSER_HELPERS\|CIRCUIT_BREAKER_HELPERS" src/bioetl/ tests/
  grep -rn "METRICS_COLLECTOR\|LOGGING_API\|BOOTSTRAP_LOGGER_EXPORTS" src/bioetl/ tests/
  grep -rn "EXIT_CODE_HELPERS\|RUN_HEALTH_SERVER" src/bioetl/ tests/
  grep -rn "compute_subcellular_fraction_entity_id" src/bioetl/ tests/

Commit message:
  refactor: remove 9 verified dead objects (INV-20260213, DEAD-001)
```

---

### PROMPT 1.2 — NAME-001: Rename CleanupResult → BronzeCleanupResult

```
Задача: Переименовать класс CleanupResult в bronze_cleanup_service.py
в BronzeCleanupResult для устранения коллизии имён с core/cleanup_service.py.

В проекте BioETL есть два класса CleanupResult:
- application/core/cleanup_service.py:47 — для Silver/Gold (оставить как есть)
- application/services/bronze_cleanup_service.py:21 — для Bronze (переименовать)

Файлы для модификации:

1. src/bioetl/application/services/bronze_cleanup_service.py
   - Переименовать: `class CleanupResult:` → `class BronzeCleanupResult:`
   - Обновить ВСЕ ссылки внутри файла:
     - Аннотации возвращаемого типа: `-> CleanupResult` → `-> BronzeCleanupResult`
     - Вызовы конструктора: `CleanupResult(` → `BronzeCleanupResult(`
     - Type hints в параметрах методов

2. src/bioetl/application/services/__init__.py
   - Обновить import: `from .bronze_cleanup_service import CleanupResult`
     → `from .bronze_cleanup_service import BronzeCleanupResult`
   - Обновить __all__ если CleanupResult там присутствует

3. Найти все остальные файлы, импортирующие CleanupResult из bronze_cleanup_service:
   grep -rn "from.*bronze_cleanup_service.*import.*CleanupResult" src/bioetl/ tests/
   grep -rn "from.*application.services.*import.*CleanupResult" src/bioetl/ tests/
   Обновить каждый найденный импорт.

НЕ ТРОГАТЬ:
- src/bioetl/application/core/cleanup_service.py — это core CleanupResult
- src/bioetl/application/core/__init__.py — core export
- Любой файл, импортирующий CleanupResult из application.core

Верификация:
  grep -rn "class CleanupResult" src/bioetl/
  # Ожидаем ровно 1 результат: core/cleanup_service.py
  grep -rn "class BronzeCleanupResult" src/bioetl/
  # Ожидаем ровно 1 результат: services/bronze_cleanup_service.py
  pytest tests/unit/application/services/test_bronze_cleanup_service.py -v
  pytest tests/unit/application/core/test_cleanup_service.py -v
  pytest tests/ -x --timeout=120

Commit message:
  refactor: rename bronze CleanupResult → BronzeCleanupResult (NAME-001)
```

---

### PROMPT 1.3 — NAME-002: Rename RateLimitConfig → RateLimitContext

```
Задача: Переименовать класс RateLimitConfig в composition/bootstrap_contexts.py
в RateLimitContext для устранения коллизии с domain/configs/base.py.

В проекте BioETL есть два класса RateLimitConfig:
- domain/configs/base.py:20 — domain value object (requests_per_second, burst) — оставить
- composition/bootstrap_contexts.py:107 — bootstrap DTO (rate, capacity) — переименовать

Файлы для модификации:

1. src/bioetl/composition/bootstrap_contexts.py
   - Переименовать: `class RateLimitConfig:` → `class RateLimitContext:`
   - Обновить docstring если содержит старое имя
   - Обновить __all__ если там есть "RateLimitConfig"

2. src/bioetl/composition/types.py
   - Обновить import и __all__

3. Найти ВСЕ остальные импорты:
   grep -rn "from.*bootstrap_contexts.*import.*RateLimitConfig" src/bioetl/ tests/
   grep -rn "from.*composition.*import.*RateLimitConfig" src/bioetl/ tests/
   Обновить каждый найденный. Типичные места:
   - composition/providers/_config_helpers.py
   - тесты

НЕ ТРОГАТЬ:
- src/bioetl/domain/configs/base.py — domain RateLimitConfig
- src/bioetl/domain/configs/__init__.py — domain export
- src/bioetl/domain/__init__.py — domain re-export
- Любой файл, импортирующий RateLimitConfig из bioetl.domain

Верификация:
  grep -rn "class RateLimitConfig" src/bioetl/
  # Ожидаем ровно 1 результат: domain/configs/base.py
  grep -rn "class RateLimitContext" src/bioetl/
  # Ожидаем ровно 1 результат: composition/bootstrap_contexts.py
  pytest tests/unit/composition/ -v
  pytest tests/ -x --timeout=120

Commit message:
  refactor: rename composition RateLimitConfig → RateLimitContext (NAME-002)
```

---

### PROMPT 1.4 — LINT-001: Удалить unused imports

```
Задача: Найти и удалить неиспользуемые импорты в BioETL.

Шаги:

1. Запустить линтер:
   ruff check src/bioetl/ --select F401 --output-format=full

2. Для каждого найденного:
   - Если импорт в __init__.py и является re-export (есть в __all__):
     ОСТАВИТЬ, добавить `# noqa: F401` если ruff ругается
   - Если импорт в блоке TYPE_CHECKING:
     ОСТАВИТЬ
   - Если импорт действительно не используется:
     УДАЛИТЬ строку импорта

3. Повторно проверить:
   ruff check src/bioetl/ --select F401
   Ожидаем 0 нарушений.

4. Запустить тесты:
   pytest tests/ -x --timeout=120

Commit message:
  chore: remove unused imports (LINT-001)
```

---

## Фаза 2: Дедупликация кода

---

### PROMPT 2.1 — RF-DUP-001: Извлечь shared _load_yaml_file utility

```
Задача: Устранить дупликацию _load_yaml между BaseConfigLoader и DQConfigLoader.

Контекст (проверено 2026-02-15):
- BaseConfigLoader (infrastructure/config/base_config_loader.py:70) — ABC Generic[T]
- DQConfigLoader (infrastructure/config/dq_config_loader.py:24) — standalone class,
  НЕ наследует от BaseConfigLoader
- Оба имеют идентичный метод _load_yaml(self, path: Path) -> dict[str, Any]
  (line 70 и line 139 соответственно)

Оба метода:
  def _load_yaml(self, path: Path) -> dict[str, Any]:
      if not path.exists():
          return {}
      with open(path, encoding="utf-8") as f:
          content = yaml.safe_load(f)
          return content if content is not None else {}

Шаги:

1. Прочитать оба файла и подтвердить идентичность методов.

2. Создать module-level утилиту в base_config_loader.py:

   def _load_yaml_file(path: Path) -> dict[str, Any]:
       """Load YAML file, returning empty dict if missing or empty."""
       if not path.exists():
           return {}
       with open(path, encoding="utf-8") as f:
           content = yaml.safe_load(f)
           return content if content is not None else {}

3. В BaseConfigLoader._load_yaml:
   - Делегировать: return _load_yaml_file(path)

4. В dq_config_loader.py:
   - Добавить import: from .base_config_loader import _load_yaml_file
   - В DQConfigLoader._load_yaml:
     Делегировать: return _load_yaml_file(path)
   - Или (проще): удалить _load_yaml из DQConfigLoader и использовать
     _load_yaml_file напрямую в вызывающих методах

5. Проверить что FilterConfigLoader и PipelineConfigLoader не имеют
   аналогичного дубликата:
   grep -rn "def _load_yaml" src/bioetl/infrastructure/config/

Верификация:
  pytest tests/ -k "config_loader or dq_config" -v
  pytest tests/ -x --timeout=120

Commit message:
  refactor: extract shared _load_yaml_file utility (RF-DUP-001)
```

---

### PROMPT 2.2 — RF-DUP-002: Извлечь _MetadataBuilderBase

```
Задача: Извлечь общий базовый класс для SilverMetadataBuilder и GoldMetadataBuilder.

Файл: src/bioetl/infrastructure/storage/metadata_builder.py

Текущее состояние:
- SilverMetadataBuilder (строка ~185) и GoldMetadataBuilder (строка ~321)
  имеют ИДЕНТИЧНЫЕ конструкторы:

  def __init__(
      self,
      transform_version: str | None = None,
      transform_steps: tuple[str, ...] | None = None,
  ) -> None:
      self._transform_version = transform_version
      self._transform_steps = transform_steps or ()

Шаги:

1. Создать private базовый класс в том же файле (перед SilverMetadataBuilder):

   class _MetadataBuilderBase:
       """Shared initialization for Silver/Gold metadata builders."""

       def __init__(
           self,
           transform_version: str | None = None,
           transform_steps: tuple[str, ...] | None = None,
       ) -> None:
           self._transform_version = transform_version
           self._transform_steps = transform_steps or ()

2. Сделать оба класса наследниками (в дополнение к существующим базовым классам):
   class SilverMetadataBuilder(_MetadataBuilderBase):
   class GoldMetadataBuilder(_MetadataBuilderBase):

3. Удалить __init__ из обоих подклассов (теперь наследуется).

4. НЕ менять никакие другие методы или поведение.

Верификация:
  pytest tests/ -k metadata_builder -v
  pytest tests/ -x --timeout=120

Архитектурные правила:
- _MetadataBuilderBase остаётся в infrastructure слое (тот же файл)
- Single underscore prefix — внутренний класс (NAME-004)
- НЕ добавлять в __all__

Commit message:
  refactor: extract _MetadataBuilderBase for shared init (RF-DUP-002)
```

---

### PROMPT 2.3 — RF-DUP-003: Извлечь mixin для get_source_metadata

```
Задача: Извлечь общий метод get_source_metadata в mixin.

Три класса содержат идентичную реализацию метода get_source_metadata:
- FilteredDataSource (application/core/filtered_data_source.py:353)
- PublicationTermDataSource (application/core/publication_term_data_source.py:574)
- SubcellularFractionDataSource (application/core/subcellular_fraction_data_source.py:289)

Реализация (одинаковая во всех трёх):
  def get_source_metadata(self, api_version: str | None = None) -> Any:
      get_metadata = getattr(self._data_source, "get_source_metadata", None)
      if get_metadata is not None and callable(get_metadata):
          return get_metadata(api_version)
      return None

Шаги:

1. Проверить что все три класса имеют атрибут self._data_source.

2. Создать mixin в application/core/:
   Вариант A — добавить в существующий base файл (если есть общий base для data sources)
   Вариант B — создать application/core/_data_source_mixins.py:

   from typing import Any

   class SourceMetadataDelegationMixin:
       """Mixin для делегирования get_source_metadata к wrapped data source."""

       _data_source: Any  # defined in concrete class

       def get_source_metadata(self, api_version: str | None = None) -> Any:
           """Delegate get_source_metadata to wrapped data source if supported."""
           get_metadata = getattr(self._data_source, "get_source_metadata", None)
           if get_metadata is not None and callable(get_metadata):
               return get_metadata(api_version)
           return None

3. Добавить mixin к трём классам:
   class FilteredDataSource(SourceMetadataDelegationMixin):
   class PublicationTermDataSource(SourceMetadataDelegationMixin):
   class SubcellularFractionDataSource(SourceMetadataDelegationMixin):

4. Удалить get_source_metadata из каждого из трёх классов.

Верификация:
  pytest tests/ -k "filtered_data_source or publication_term or subcellular" -v
  pytest tests/ -x --timeout=120

Архитектурные правила:
- Mixin остаётся в application слое
- Имя с суффиксом Mixin (NAME-001)
- Добавить mixin в __all__ соответствующего __init__.py если он публичный,
  или использовать underscore prefix если приватный

Commit message:
  refactor: extract SourceMetadataDelegationMixin (RF-DUP-003)
```

---

### PROMPT 2.4 — RF-NAME-003: Rename LineageMetadata → CompositeLineageMetadata

```
Задача: Переименовать LineageMetadata в domain/composite/lineage.py
в CompositeLineageMetadata для устранения коллизии с domain/models/metadata.py.

В проекте BioETL есть два класса LineageMetadata:
- domain/models/metadata.py:461 — BaseModel для Medallion layers — ОСТАВИТЬ
- domain/composite/lineage.py:34 — frozen dataclass для composite merging — ПЕРЕИМЕНОВАТЬ

Шаги:

1. Прочитать оба файла, подтвердить разное назначение.

2. В src/bioetl/domain/composite/lineage.py:
   - Переименовать: `class LineageMetadata:` → `class CompositeLineageMetadata:`
   - Обновить все ссылки внутри файла

3. Найти ВСЕ импорты:
   grep -rn "from.*composite.*lineage.*import.*LineageMetadata" src/bioetl/ tests/
   grep -rn "from.*domain.composite.*import.*LineageMetadata" src/bioetl/ tests/
   Обновить каждый найденный.

4. Обновить __all__ в:
   - domain/composite/lineage.py (если есть)
   - domain/composite/__init__.py (если re-exported)
   - domain/__init__.py (если re-exported)

НЕ ТРОГАТЬ:
- domain/models/metadata.py — Medallion LineageMetadata
- Любой файл, импортирующий LineageMetadata из domain.models

Верификация:
  grep -rn "class LineageMetadata" src/bioetl/
  # Ожидаем 1 результат: domain/models/metadata.py
  grep -rn "class CompositeLineageMetadata" src/bioetl/
  # Ожидаем 1 результат: domain/composite/lineage.py
  pytest tests/ -k lineage -v
  pytest tests/ -x --timeout=120

Commit message:
  refactor: rename composite LineageMetadata → CompositeLineageMetadata (RF-NAME-003)
```

---

### PROMPT 2.5 — RF-CROSS-001: Вынести get_version() в domain/version.py

```
Задача: Консолидировать _get_bioetl_version в единый источник в domain слое.

Текущее состояние — две независимые реализации:
- infrastructure/storage/metadata_builder.py:27 — с try/except → "unknown"
- composition/services/metadata_coordinator.py:59 — без error handling

ARCH-001 запрещает cross-import между infrastructure и composition,
но оба могут импортировать из domain.

Шаги:

1. Проверить существование src/bioetl/domain/version.py.
   Если не существует — создать.

2. Создать/обновить src/bioetl/domain/version.py:

   """BioETL version utilities."""
   from __future__ import annotations

   from importlib.metadata import PackageNotFoundError, version as _pkg_version

   __all__ = ["get_version"]

   def get_version() -> str:
       """Get BioETL package version.

       Returns:
           Version string or 'unknown' if package is not installed.
       """
       try:
           return _pkg_version("bioetl")
       except PackageNotFoundError:
           return "unknown"

3. В metadata_builder.py:
   - Заменить определение _get_bioetl_version на:
     from bioetl.domain.version import get_version as _get_bioetl_version
   - Удалить тело старой функции

4. В metadata_coordinator.py:
   - Заменить определение _get_bioetl_version на:
     from bioetl.domain.version import get_version as _get_bioetl_version
   - Удалить тело старой функции и локальный import

5. Добавить get_version в domain/__init__.py re-exports если уместно.

Верификация:
  pytest tests/ -k "metadata_builder or metadata_coordinator" -v
  pytest tests/architecture/ -v  # проверить ARCH-001
  pytest tests/ -x --timeout=120

Commit message:
  refactor: consolidate _get_bioetl_version to domain/version.py (RF-CROSS-001)
```

---

## Фаза 3: Инфраструктура качества

---

### ~~PROMPT 3.1 — CI-001: Настроить import-linter~~ ✅ ВЫПОЛНЕНО

```
СТАТУС: УЖЕ ВЫПОЛНЕНО в main.

import-linter уже настроен:
- Конфигурация: .importlinter (INI-формат, 5 контрактов)
- CI: .github/workflows/import-linter.yml → job `arch-tests` → step `lint-imports --config .importlinter`
- Контракты покрывают:
  - domain-independence (domain ⊄ application/composition/infrastructure/interfaces)
  - application-independence (application ⊄ composition/infrastructure/interfaces)
  - infrastructure-independence (infrastructure ⊄ application/interfaces)
  - composition-no-interfaces (composition ⊄ interfaces)
  - no-direct-instantiation-in-application (application ⊄ concrete adapters)

Никаких действий не требуется. Пропустить этот промпт.
```

---

### PROMPT 3.2 — DOC-001: ADR для schema↔domain pair convention

```
Задача: Создать ADR документирующий паттерн schema↔domain pairs в BioETL.

Шаги:

1. Определить следующий номер ADR:
   ls docs/02-architecture/decisions/
   Найти максимальный номер и прибавить 1.

2. Создать файл docs/02-architecture/decisions/ADR-NNN-schema-domain-pairs.md:

   # ADR-NNN: Schema↔Domain Configuration Pairs

   ## Status
   Accepted

   ## Context
   BioETL использует Hexagonal Architecture. Domain слой определяет immutable
   value objects (frozen dataclasses) для конфигурации. Infrastructure слой
   определяет Pydantic модели для десериализации YAML файлов.

   Оба слоя имеют классы с одинаковыми именами (например, DQConfig, BaseClientConfig),
   что создаёт видимость дупликации.

   ## Decision
   Разрешить одноимённые классы в domain и infrastructure при условии:
   1. Domain класс — immutable value object (frozen dataclass) с бизнес-валидацией
   2. Infrastructure класс — Pydantic model для YAML десериализации
   3. Infrastructure модель имеет метод `to_domain()` для конвертации
   4. Импорты всегда fully qualified (bioetl.domain.X vs bioetl.infrastructure.X)

   ## Known Pairs
   | Domain | Infrastructure | Purpose |
   |--------|---------------|---------|
   | BaseClientConfig (domain/configs/base.py) | BaseClientConfig (infrastructure/schemas/base_schemas.py) | HTTP client config |
   | CircuitBreakerConfig (domain/resilience.py) | CircuitBreakerConfig (infrastructure/schemas/pipeline_config.py) | Circuit breaker |
   | DQConfig (domain/config/dq.py) | DQConfig (infrastructure/schemas/pipeline_config.py) | Data Quality |
   | DQReportConfig (domain/config/dq.py) | DQReportConfig (infrastructure/schemas/pipeline_config.py) | DQ Reports |
   | InputFilterConfig (domain/filtering/) | BaseInputFilterConfig (infrastructure/schemas/pipeline_config.py) | Input filters |

   ## Consequences
   - grep по имени класса вернёт несколько результатов — это нормально
   - Разработчик должен проверять import path для определения нужного класса
   - Новые config objects должны следовать паттерну: Pydantic schema → to_domain() → dataclass

   ## Alternatives Considered
   - Yaml prefix для infrastructure (YamlDQConfig) — отвергнуто, избыточно
   - Schema suffix (DQConfigSchema) — возможная альтернатива для будущих пар

НЕ переименовывать существующие классы. Только документация.

Commit message:
  docs: ADR for schema-domain pair convention (DOC-001)
```

---

### PROMPT 3.3 — VERIFY-001: Проверить orphan module subcellular_fraction_data_source

```
Задача: Определить статус файла
src/bioetl/application/core/subcellular_fraction_data_source.py (297 LOC).

У файла есть тесты, но прямой import в production коде не найден.

Шаги:

1. Искать все ссылки:
   grep -rn "subcellular_fraction_data_source\|SubcellularFractionDataSource" src/bioetl/
   grep -rn "subcellular.*fraction" src/bioetl/composition/ src/bioetl/interfaces/

2. Искать динамическую регистрацию (string-based):
   grep -rn '"subcellular"' src/bioetl/composition/
   grep -rn "subcellular" src/bioetl/composition/factories/

3. Проверить pipeline configs:
   grep -rn "subcellular" configs/

4. Проверить __init__.py re-exports:
   grep -rn "subcellular" src/bioetl/application/core/__init__.py

Результат: отчёт со статусом:
  - ACTIVE (найдена динамическая регистрация или import chain)
  - TEST_ONLY (только тесты)
  - DEAD (ни тестов, ни production)

НЕ удалять файл без подтверждения.
```

---

### PROMPT 3.4 — VERIFY-002: Проверить TEST_ONLY объекты

```
Задача: Определить статус TEST_ONLY объектов (используются только в тестах).

Проверить каждый:

1. TransformerPort в src/bioetl/application/core/protocols.py
   grep -rn "TransformerPort" src/bioetl/ --include="*.py" | grep -v "tests/"

2. PIPELINE_HEALTH_CHECK_PASSED в infrastructure
   grep -rn "PIPELINE_HEALTH_CHECK_PASSED" src/bioetl/

3. DataClassification в src/bioetl/domain/types.py
   grep -rn "DataClassification" src/bioetl/ --include="*.py" | grep -v "tests/"

Для каждого объекта определить:
  - ACTIVE (есть production ссылки)
  - TEST_ONLY (только тесты) → кандидат на перемещение в tests/
  - DEAD → кандидат на удаление

НЕ модифицировать файлы. Только отчёт.
```

---

### PROMPT 3.5 — ANALYSIS-001: Анализ циклических зависимостей

```
Задача: Провести анализ циклических зависимостей в BioETL.

Шаги:

1. import-linter уже настроен (.importlinter). Запустить:
   lint-imports --config .importlinter

2. Установить grimp для графового анализа:
   pip install grimp

3. Python скрипт для детекции циклов:

   import grimp
   graph = grimp.build_graph("bioetl")

   # Проверить intra-layer циклы
   for layer in ["domain", "application", "infrastructure", "composition", "interfaces"]:
       modules = [m for m in graph.modules if f".{layer}." in m or m.endswith(f".{layer}")]
       for mod in modules:
           try:
               chains = graph.find_illegal_dependencies_for_module(mod)
               if chains:
                   print(f"CYCLE: {mod} -> {chains}")
           except Exception as e:
               print(f"ERROR checking {mod}: {e}")

4. Отчёт:
   - Список найденных циклов (module A → B → ... → A)
   - Слой и severity каждого цикла
   - Рекомендации (без исправлений)

НЕ исправлять циклы — только диагностика.
```

---

## Фаза 4: Исследование

---

### PROMPT 4.1 — RF-INV-001: Анализ cross-provider extractors

```
Задача: Проанализировать extract_* функции в провайдерах публикаций
для оценки возможности консолидации.

Провайдеры:
- application/pipelines/semanticscholar/extractors/
- application/pipelines/openalex/extractors/
- application/pipelines/crossref/extractors/
- application/pipelines/pubmed/extractors/ (если есть)

Функции для сравнения:
- extract_authors
- extract_author_orcids
- extract_affiliations
- extract_journal_info
- extract_external_ids
- extract_open_access_info

Для каждой пары:

1. Прочитать обе реализации side by side
2. Классифицировать:
   a) IDENTICAL — true copy-paste → консолидировать
   b) SIMILAR_STRUCTURE — тот же паттерн, разные поля API →
      можно параметризовать (field mappings)
   c) DIFFERENT — разная логика → оставить раздельно

3. Для случаев (a) и (b) оценить:
   - Экономия LOC
   - Риск сломать provider-specific edge cases
   - Подходит ли общая функция в application/core/

Результат: Decision document с одним из:
  - "Консолидировать X функций в application/core/publication_extractors.py"
  - "Оставить раздельно — различия provider-specific"
  - "Частичная консолидация: объединить A+B, оставить C+D"

НЕ модифицировать код. Только анализ и рекомендации.
```

---

### PROMPT 4.2 — RF-INV-002: Аудит facade re-exports

```
Задача: Аудит всех __init__.py facade re-exports в BioETL.

Шаги:

1. Найти все __init__.py с __all__:
   grep -rln "__all__" src/bioetl/**/__init__.py

2. Для каждого:
   - Подсчитать количество экспортов
   - Проверить что все экспортируемые имена реально importable
   - Проверить что нет DEAD экспортов (имя в __all__ но никем не импортируется)
   - Проверить что важные публичные объекты НЕ пропущены

3. Найти крупнейшие facades (>20 экспортов):
   - Можно ли разбить на sub-facades?
   - Все ли экспорты действительно часть public API?

4. Результат: таблица:
   | Module | Exports | Dead Exports | Missing | Recommendation |

НЕ модифицировать файлы. Только отчёт.
```

---

## Промпты для конфигурационных файлов

---

### PROMPT CFG-001: Валидация pipeline configs после рефакторинга

```
Задача: После рефакторинга Фаз 1-2 проверить что все pipeline configs
корректно загружаются.

Шаги:

1. Найти все pipeline config файлы:
   find configs/ -name "*.yaml" -o -name "*.yml" | sort

2. Для каждого файла:
   python -c "
   from bioetl.infrastructure.config import load_pipeline_config
   config = load_pipeline_config('путь/к/файлу')
   print(f'OK: {config.pipeline_name}')
   "

3. Проверить что RateLimitConfig переименование (PROMPT 1.3) не сломало
   загрузку конфигов:
   grep -rn "rate_limit\|RateLimitConfig" configs/

4. Проверить что CleanupResult переименование (PROMPT 1.2) не повлияло
   на CLI команды:
   python -m bioetl --help
   python -m bioetl cleanup --help (если есть)

Ожидаемый результат: все configs загружаются без ошибок.
```

---

### ~~PROMPT CFG-002: Обновить pyproject.toml после добавления import-linter~~ ✅ ВЫПОЛНЕНО

```
СТАТУС: УЖЕ ВЫПОЛНЕНО в main.

import-linter настроен через .importlinter (INI-формат, не pyproject.toml).
CI workflow запускает: lint-imports --config .importlinter.
Никаких действий не требуется.
```

---

## Порядок выполнения (рекомендуемый)

```
1. PROMPT 1.1 (DEAD-001)     ─── параллельно ──── PROMPT 1.4 (LINT-001)
2. PROMPT 1.2 (NAME-001)     ─── параллельно ──── PROMPT 1.3 (NAME-002)
3. PROMPT CFG-001             ─── верификация после Phase 1
4. PROMPT 2.1 (RF-DUP-001)   ┐
5. PROMPT 2.2 (RF-DUP-002)   ├── параллельно (независимые файлы)
6. PROMPT 2.3 (RF-DUP-003)   ┘
7. PROMPT 2.4 (RF-NAME-003)  ─── после 4-6
8. PROMPT 2.5 (RF-CROSS-001) ─── после 4-6
9. PROMPT 3.1 (CI-001)       ✅ DONE
10. PROMPT 3.2 (DOC-001)     ─── независимо
11. PROMPT 3.3-3.5            ─── исследование
12. PROMPT 4.1-4.2            ─── опционально
```

---

*Каждый промпт содержит commit message. После каждого commit выполняйте
`pytest tests/ -x --timeout=120` для защиты от регрессий.*
