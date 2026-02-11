# Набор Промтов для Модификации Кода — BioETL

**Сформирован на основе:** `reports/inventory/inventory-report.md` (2026-02-11)
**Порядок выполнения:** QW-1 → QW-8 (quick wins), затем RF-* (рефакторинги)
**Субагент по умолчанию:** `py-code-bot` (если не указано иное)

---

## Группа 1: Quick Wins — Удаление мёртвого кода

### QW-1: Удаление мёртвых domain events

**Субагент:** `py-code-bot`

```
Удали 4 мёртвых domain event класса из src/bioetl/domain/aggregates/events.py.

Мёртвые классы (0 ссылок в production и tests):
- PipelineStarted (строка 48)
- StageCompleted (строка 103)
- DQThresholdExceeded (строка 233)
- SchemaEvolutionDetected (строка 249)

Сохраняемые классы (они АКТИВНЫ, НЕ ТРОГАТЬ):
- DomainEvent (базовый, строка 29)
- PipelineCompleted (строка 60)
- PipelineFailed (строка 75)
- PipelineShutdown (строка 90)
- BatchCreated (строка 123)
- BatchSealed (строка 135)
- BatchWritten (строка 150)
- BatchFailed (строка 163)
- RecordQuarantined (строка 183)
- QuarantineEntryCreated (строка 199)
- QuarantineEntryResolved (строка 214)

Действия:
1. Удалить 4 мёртвых класса из events.py
2. Проверить __all__ в domain/aggregates/__init__.py — убрать удалённые классы
3. Проверить domain/events.py — убрать re-export если есть
4. Сохранить секционные комментарии (# Pipeline Run Events, # Batch Events, и т.д.)
5. Запусти: grep -rn "PipelineStarted\|StageCompleted\|DQThresholdExceeded\|SchemaEvolutionDetected" src/bioetl/ tests/ --include="*.py" — убедись что ссылок нет

НЕ удаляй комментарий "# Data Quality Events" если секция станет пустой — удали всю секцию целиком.
```

---

### QW-2: Удаление мёртвых Pandera схем

**Субагент:** `py-code-bot`

```
Удали 2 мёртвых Pandera-схемы, являющихся orphan-модулями (0 импортов).

Файлы на удаление:
1. src/bioetl/domain/schemas/chembl/molecule_form.py (35 LOC)
   - Содержит MoleculeFormSchema — 0 ссылок в production и tests
2. src/bioetl/domain/schemas/chembl/target_relation.py (38 LOC)
   - Содержит TargetRelationSchema — 0 ссылок в production и tests

Действия:
1. Удалить оба файла
2. Проверить и почистить импорты в src/bioetl/domain/schemas/chembl/__init__.py:
   - Убрать re-export MoleculeFormSchema если есть
   - Убрать re-export TargetRelationSchema если есть
3. Проверить: grep -rn "MoleculeFormSchema\|TargetRelationSchema\|molecule_form\|target_relation" src/bioetl/ tests/ --include="*.py"
4. Запустить тесты: pytest tests/architecture/ -x -q
```

---

### QW-3: Удаление мёртвых exception классов

**Субагент:** `py-code-bot`

```
Удали 3 мёртвых exception класса (0 ссылок в production и tests).

Мёртвые классы:
1. ConfigurationError — src/bioetl/domain/exceptions/infrastructure.py:57 (~22 строки, 57-79)
2. FileSystemError — src/bioetl/domain/exceptions/infrastructure.py:82 (~32 строки, 82-114)
3. InternalError — src/bioetl/domain/exceptions/internal.py:24 (~11 строк, 24-34)

ВНИМАНИЕ: InternalError — базовый класс, но у него 0 наследников и 0 ссылок.
Проверь: InvalidStateError наследует CriticalError НАПРЯМУЮ (строка 42), не InternalError.
Все остальные классы в internal.py тоже наследуют CriticalError, не InternalError.

Действия:
1. Удалить ConfigurationError из infrastructure.py
2. Удалить FileSystemError из infrastructure.py
3. Удалить InternalError из internal.py
4. Обновить src/bioetl/domain/exceptions/__init__.py:
   - Убрать из импортов: ConfigurationError, FileSystemError, InternalError
   - Убрать из __all__: "ConfigurationError", "FileSystemError", "InternalError"
5. Проверить: grep -rn "ConfigurationError\|FileSystemError\|\bInternalError\b" src/bioetl/ tests/ --include="*.py"
6. Запустить тесты: pytest tests/architecture/ tests/unit/domain/ -x -q
```

---

### QW-4: Удаление мёртвых infrastructure классов

**Субагент:** `py-code-bot`

```
Удали 4 мёртвых класса из infrastructure layer (0 ссылок в production и tests).

Мёртвые классы:
1. ChemblStatusResponse — src/bioetl/infrastructure/adapters/chembl/models.py:611
   Pydantic модель для ChEMBL status API. Не используется.
   Удалить только класс, НЕ весь файл.

2. HasProviderName — src/bioetl/infrastructure/adapters/filterable_mixin.py:23
   Protocol интерфейс. 0 ссылок.
   Удалить класс. Если файл содержит только этот Protocol — проверь есть ли другие классы.

3. HealthCheckObservability — src/bioetl/infrastructure/adapters/health_check_mixin.py:40
   Protocol для health check observability. 0 ссылок.
   Удалить класс. Если файл содержит другие классы — оставить остальные.

4. PageFetcher — src/bioetl/infrastructure/adapters/http/pagination.py:14
   Protocol[T] для pagination. 0 ссылок.
   Удалить класс. Если файл содержит другие классы — оставить остальные.

Для каждого файла:
1. Удалить класс
2. Убрать неиспользуемые импорты, возникшие после удаления
3. Проверить __init__.py в директории — убрать re-export если есть
4. Запустить: pytest tests/architecture/ tests/unit/infrastructure/ -x -q
```

---

### QW-5: Удаление orphan-модуля config_types.py

**Субагент:** `py-code-bot`

```
Проведи анализ и удали orphan-модуль src/bioetl/domain/config_types.py (446 LOC).

ПЕРЕД УДАЛЕНИЕМ — проверка:
1. Прочитай файл целиком (cat)
2. Для каждого публичного типа/класса из файла найди usage:
   grep -rn "ТипName" src/bioetl/ tests/ --include="*.py" | grep -v "config_types.py"
3. Единственная ссылка — комментарий в domain/configs/base.py:26:
   "- domain/config_types.py:RateLimitDict"
   Если это только комментарий — удалить и его.

Действия:
1. Если все типы действительно не используются:
   - Удалить файл src/bioetl/domain/config_types.py
   - Убрать re-export из domain/__init__.py если есть
   - Убрать комментарий-ссылку из domain/configs/base.py
2. Если какие-то типы ИСПОЛЬЗУЮТСЯ:
   - НЕ удалять файл
   - Отметить используемые типы в комментарии к коммиту
3. Запустить: pytest tests/architecture/ -x -q
```

---

### QW-6: Удаление orphan-модуля _field_orders.py

**Субагент:** `py-code-bot`

```
Проведи анализ и удали orphan-модуль src/bioetl/domain/schemas/_field_orders.py (223 LOC).

ПЕРЕД УДАЛЕНИЕМ — проверка:
1. Прочитай файл целиком
2. Для каждой константы из файла найди usage в других файлах:
   grep -rn "CONSTANT_NAME" src/bioetl/ tests/ --include="*.py" | grep -v "_field_orders.py"
3. Проверь — не заменён ли этот модуль на:
   - src/bioetl/domain/schemas/column_order.py
   - src/bioetl/domain/value_objects/column_order.py
   Если да — это deprecated версия, безопасно удалять.

Действия:
1. Если все константы не используются — удалить файл
2. Убрать re-export из schemas/__init__.py если есть
3. Запустить: pytest tests/ -x -q --timeout=60
```

---

### QW-7: Удаление orphan-шима dq_metrics_calculator.py (application)

**Субагент:** `py-code-bot`

```
Удали orphan-модуль src/bioetl/application/services/dq_metrics_calculator.py (25 LOC).

Контекст:
- Этот файл — либо re-export шим, либо заглушка после рефакторинга
- Основной DQ metrics calculator: src/bioetl/domain/services/dq_metrics_calculator.py
- 0 импортов этого модуля из остального кода

Действия:
1. Прочитай файл
2. Проверь: grep -rn "dq_metrics_calculator\|DqMetricsCalculator\|DQMetricsCalculator" src/bioetl/application/ --include="*.py" | grep -v "dq_metrics_calculator.py"
3. Если 0 ссылок — удалить файл
4. Убрать из application/services/__init__.py если есть re-export
5. Запустить: pytest tests/unit/application/ -x -q
```

---

### QW-8: Исправление конфликта DriftLevel enum (CRITICAL)

**Субагент:** `py-code-bot`

```
КРИТИЧЕСКАЯ ПРОБЛЕМА: Enum DriftLevel определён ДВАЖДЫ с РАЗНЫМИ значениями.

Определение A (domain/types.py:83):
  class DriftLevel(StrEnum):
      INFO = "INFO"        # UPPERCASE
      WARN = "WARN"
      CRITICAL = "CRITICAL"

Определение B (domain/value_objects/dq_report.py:41):
  class DriftLevel(StrEnum):
      INFO = "info"        # lowercase
      WARN = "warn"
      CRITICAL = "critical"

Анализ:
- domain/types.py:DriftLevel используется в domain/transformations.py и тестах
- domain/value_objects/dq_report.py:DriftLevel re-экспортируется через value_objects/__init__.py

Исправление:
1. Определи каноническое определение — domain/types.py (UPPERCASE, соответствует другим
   enum'ам в types.py: HealthStatus="HEALTHY", RunType="incremental").

   РЕШЕНИЕ: Посмотри какое значение фактически используется в сравнениях по коду:
   grep -rn "DriftLevel\." src/bioetl/ tests/ --include="*.py"

2. Удали дублирующий DriftLevel из domain/value_objects/dq_report.py
3. В domain/value_objects/dq_report.py добавь импорт:
   from bioetl.domain.types import DriftLevel
4. В domain/value_objects/__init__.py — обнови re-export если нужно
5. Если где-то сравниваются строки "info"/"warn"/"critical" напрямую —
   поменяй на DriftLevel.INFO / DriftLevel.WARN / DriftLevel.CRITICAL
6. Запустить: pytest tests/ -x -q --timeout=120
```

---

## Группа 2: Рефакторинги (RF-*)

### RF-NOOP: Консолидация NoOp реализаций

**Субагент:** `py-code-bot`

```
Консолидируй две параллельные иерархии NoOp-реализаций.

ТЕКУЩЕЕ СОСТОЯНИЕ:
A) domain/ports/noop.py (470 LOC) — содержит:
   - NoOpTracing (77 refs через "from bioetl.domain.ports import NoOpTracing")
   - NoOpMetrics (60 refs через "from bioetl.domain.ports import NoOpMetrics")
   - NoOpAudit (7 refs)
   - NoOpPiiHasher (10 refs)
   - NoOpMemoryMonitor (4 refs)
   - NoOpMetadataWriter (19 refs)

B) infrastructure/observability/ — содержит:
   - noop_logger.py: NoOpLogger (51 LOC, 30+ refs из composition/ и tests/)
   - noop_metrics.py: NoOpMetrics (88 LOC, 15+ refs из composition/ и tests/)
   - noop_tracing.py: NoOpTracing (60 LOC, 20+ refs из composition/ и tests/)

ДУБЛИРОВАНИЕ: NoOpTracing и NoOpMetrics существуют в ОБОИХ местах.

ПЛАН:
1. Каноническое расположение: infrastructure/observability/noop_*.py
   (NoOp — это infrastructure concern, не domain)
2. domain/ports/noop.py оставить как ТОНКИЙ re-export:
   from bioetl.infrastructure.observability.noop_logger import NoOpLogger
   from bioetl.infrastructure.observability.noop_metrics import NoOpMetrics
   from bioetl.infrastructure.observability.noop_tracing import NoOpTracing

СТОП — ПРОВЕРЬ ARCH-001 ПЕРЕД РЕАЛИЗАЦИЕЙ:
Domain НЕ МОЖЕТ импортировать из infrastructure (матрица импортов).
Значит, нужен ОБРАТНЫЙ подход:
- Каноническое расположение: domain/ports/noop.py (domain layer)
- infrastructure/observability/noop_*.py → re-export из domain/ports
  ИЛИ
- Перенести общий NoOp в domain, а infra-specific (NoOpLogger) оставить в infra

РЕШЕНИЕ:
1. NoOpMetrics, NoOpTracing — убрать дубли из infrastructure/observability/
2. В infrastructure/observability/noop_metrics.py и noop_tracing.py заменить на:
   from bioetl.domain.ports.noop import NoOpMetrics  # re-export
   from bioetl.domain.ports.noop import NoOpTracing  # re-export
3. NoOpLogger оставить в infrastructure (LoggerPort — domain port, NoOpLogger — infra impl)
4. Обновить infrastructure/observability/__init__.py
5. Не менять ни одного import statement в потребителях
6. Запустить: pytest tests/ -x -q --timeout=120
```

---

### RF-NORM: Очистка нормализационной иерархии

**Субагент:** `py-code-bot`

```
Удали 5 мёртвых Port-протоколов из domain/ports/normalization.py.

Мёртвые порты (0 import refs, 0 impl refs через Port):
1. UnitConverterPort (строки 29-107)
2. ValueValidatorPort (строки 111-167)
3. OutlierFilterPort (строки 171-209)
4. ActivityAggregatorPort (строки 213-275)
5. NormalizationServicePort (строки 279-342)

Контекст:
- Конкретные сервисы существуют (UnitConverter, ValueValidator, ActivityAggregator, NormalizationService)
- Но они используются НАПРЯМУЮ, а не через эти Port-протоколы
- Все 5 портов = 0 import refs вне определения

Действия:
1. Удалить все 5 Port-классов из domain/ports/normalization.py
2. Если файл станет пустым — удалить файл целиком
3. Обновить domain/ports/__init__.py — убрать re-export этих портов
4. Проверить: grep -rn "UnitConverterPort\|ValueValidatorPort\|OutlierFilterPort\|ActivityAggregatorPort\|NormalizationServicePort" src/bioetl/ tests/ --include="*.py"
5. Запустить: pytest tests/architecture/ -x -q
```

---

### RF-ENTITY: Анализ дублирования entity/model

**Субагент:** `py-audit-bot` (исследование, не модификация)

```
Сравни попарно дублирующиеся Pydantic модели domain vs infrastructure:

Пара 1:
- src/bioetl/domain/entities/chembl.py:511 — class ChemblPublicationRecord(BaseModel)
- src/bioetl/infrastructure/adapters/chembl/models.py:467 — class ChemblPublicationRecord(BaseModel)

Пара 2:
- src/bioetl/domain/entities/pubchem.py:24 — class PubchemMoleculeRecord(BaseModel)
- src/bioetl/infrastructure/adapters/pubchem/models.py:19 — class PubchemMoleculeRecord(BaseModel)

Для каждой пары:
1. Прочитай оба определения полностью
2. Сравни поля: какие совпадают, какие уникальны
3. Проверь usage каждой версии:
   grep -rn "ChemblPublicationRecord" src/bioetl/ --include="*.py" | grep "import"
   grep -rn "PubchemMoleculeRecord" src/bioetl/ --include="*.py" | grep "import"
4. Определи: кто импортирует какую версию
5. Сформируй рекомендацию:
   a) Удалить одну из версий и перенаправить импорты
   b) Переименовать одну для ясности (например, ChemblPublicationApiResponse vs ChemblPublicationRecord)
   c) Оставить как есть с обоснованием
```

---

### RF-CBCFG: Унификация CircuitBreakerConfig

**Субагент:** `py-audit-bot` (исследование), затем `py-code-bot` (реализация)

```
Проанализируй тройное определение CircuitBreakerConfig и предложи унификацию.

3 определения:
1. src/bioetl/domain/resilience.py — dataclass
2. src/bioetl/infrastructure/schemas/pipeline_config.py — Pydantic BaseModel
3. src/bioetl/composition/bootstrap_contexts.py — NamedTuple (?)

Для каждого:
1. Прочитай определение
2. Сравни поля
3. Проверь usage (кто импортирует)
4. Определи: можно ли свести к одному domain dataclass + Pydantic adapter в infrastructure

Принципы:
- Domain: CircuitBreakerConfig(dataclass, frozen=True) — каноническое определение
- Infrastructure: Pydantic модель для YAML-парсинга → .to_domain() → domain CircuitBreakerConfig
- Composition: НЕ должна определять свой CircuitBreakerConfig
```

---

### RF-RUNST: Унификация RunStatus

**Субагент:** `py-code-bot`

```
Разреши дублирование RunStatus enum.

Определение A (domain/aggregates/pipeline_run.py):
  class RunStatus(StrEnum):
      PENDING, RUNNING, COMPLETED, FAILED, SHUTDOWN

Определение B (application/services/pipeline_runner_service.py):
  class RunStatus(StrEnum):
      SUCCESS, SHUTDOWN, FAILED, DRY_RUN

Анализ: Это РАЗНЫЕ enum'ы с РАЗНОЙ семантикой.
- A: состояние пайплайна в процессе выполнения (lifecycle state)
- B: результат завершения пайплайна (completion result)

Только B импортируется в composition/:
  from bioetl.application.services import RunStatus

Решение:
1. Переименуй A → PipelineRunState в domain/aggregates/pipeline_run.py
   (если A используется, иначе — проверь, может A тоже мёртвый)
2. Обнови все imports/references на новое имя
3. Запустить: pytest tests/ -x -q
```

---

### RF-DRIFT: Удаление дубля DriftLevel (если не сделано в QW-8)

Смотри QW-8 выше.

---

### RF-PAGES: Консолидация parse_page_range

**Субагент:** `py-code-bot`

```
Консолидируй две реализации parse_page_range.

Реализация A: src/bioetl/domain/normalization.py:160
- Обрабатывает: electronic pages (e-xxx), supplements (S1-S15), стандартные ranges
- НЕ обрабатывает: abbreviated ranges (737-9 → 737-739)

Реализация B: src/bioetl/application/pipelines/semanticscholar/_page_parsing.py:124
- Обрабатывает: abbreviated ranges (737-9 → 737-739, 737-39 → 737-739)
- Более сложная логика расширения коротких page ranges

Решение:
1. Объедини логику: возьми реализацию A как базу, добавь обработку abbreviated ranges из B
2. Обнови тесты для domain/normalization.py:parse_page_range с новыми кейсами
3. В semanticscholar/_page_parsing.py замени parse_page_range на вызов:
   from bioetl.domain.normalization import parse_page_range
4. Если в _page_parsing.py есть другие уникальные функции — оставить файл,
   удалив только дублирующую parse_page_range
5. Запустить: pytest tests/unit/application/pipelines/semanticscholar/ tests/unit/domain/ -x -q
```

---

### RF-HASH: Консолидация normalize_for_hash

**Субагент:** `py-audit-bot` (исследование), затем `py-code-bot`

```
Найди и консолидируй реализации normalize-for-hash.

Известные локации (проверить):
1. src/bioetl/domain/transformations.py:81 — _normalize_for_hash
2. src/bioetl/domain/services/identity_service.py:119 — нормализация для хеширования
3. src/bioetl/composition/services/versioning.py:65 — normalize_for_hash

Для каждой:
1. Прочитай реализацию
2. Сравни алгоритм (strip, lower, sort keys, etc.)
3. Определи семантические отличия
4. Если алгоритмы идентичны — вынеси каноническую реализацию в domain/transformations.py
5. Обнови остальные вызовы
```

---

### RF-ORPHAN-SCHEMAS: Решение по orphan-схемам

**Субагент:** `py-audit-bot` (исследование)

```
Определи судьбу 3 orphan Pandera-схем.

Orphan-модули:
1. src/bioetl/domain/schemas/crossref/author.py (86 LOC)
   - Содержит AuthorBronzeSchema, AuthorSilverSchema, AuthorGoldSchema
2. src/bioetl/domain/schemas/crossref/funder.py (68 LOC)
   - Содержит FunderBronzeSchema, FunderSilverSchema, FunderGoldSchema
3. src/bioetl/domain/schemas/uniprot/isoform.py (81 LOC)
   - Содержит IsoformBronzeSchema, IsoformSilverSchema, IsoformGoldSchema

Проверки:
1. Есть ли entity_type "author"/"funder"/"isoform" в конфигах?
   grep -rn "author\|funder\|isoform" configs/ --include="*.yaml" --include="*.yml"
2. Есть ли pipeline для этих entities?
   grep -rn "author\|funder\|isoform" src/bioetl/application/pipelines/ --include="*.py"
3. Есть ли упоминание в ADR или roadmap?
   grep -rn "author\|funder\|isoform" docs/ --include="*.md"

Рекомендация:
- Если entity запланирован (есть в roadmap/docs) — оставить, добавить TODO
- Если не запланирован — удалить файл
```

---

## Группа 3: Дополнительный анализ (исследование без модификации кода)

### AUDIT-INFRA-ORPHAN: Проверка adapter_error_logging.py

**Субагент:** `py-audit-bot`

```
Проверь, является ли src/bioetl/infrastructure/adapters/adapter_error_logging.py (56 LOC)
мёртвым модулем или декоратор применяется неявно.

1. Прочитай файл
2. Если это декоратор — ищи паттерн применения: @adapter_error_logging или @log_adapter_errors
   grep -rn "adapter_error_logging\|log_adapter_errors" src/bioetl/ --include="*.py"
3. Если 0 применений — это orphan, рекомендовать удаление
4. Если применяется — это НЕ orphan, мой анализ был ошибочным
```

---

### AUDIT-COMPOSITION-FACTORIES: Анализ factory-путаницы

**Субагент:** `py-audit-bot`

```
Проанализируй путаницу в composition/factories/:

1. pipeline_factories.py vs pipeline_factory.py — почему два файла?
   - Прочитай оба
   - Определи: один = registry/registration, другой = actual factory logic?
   - Рекомендация по объединению

2. storage.py vs storage_adapter.py vs storage_factory.py — три storage-файла:
   - Прочитай каждый
   - Определи назначение каждого
   - Нет ли пустого/заглушки?
   - Рекомендация по консолидации

3. Для каждого файла: кто его импортирует?
   grep -rn "from bioetl.composition.factories.pipeline_factories" src/bioetl/ --include="*.py"
   grep -rn "from bioetl.composition.factories.pipeline_factory" src/bioetl/ --include="*.py"
   grep -rn "from bioetl.composition.factories.storage " src/bioetl/ --include="*.py"
   grep -rn "from bioetl.composition.factories.storage_adapter" src/bioetl/ --include="*.py"
   grep -rn "from bioetl.composition.factories.storage_factory" src/bioetl/ --include="*.py"
```

---

## Порядок Выполнения

```
Фаза 1 (Quick Wins, параллельно):
  QW-1 + QW-2 + QW-3 + QW-4    → удаление мёртвого кода

Фаза 2 (Quick Wins, зависят от Фазы 1):
  QW-5 + QW-6 + QW-7            → удаление orphan-модулей

Фаза 3 (CRITICAL bug fix):
  QW-8                            → DriftLevel enum conflict

Фаза 4 (Исследование, параллельно):
  RF-ENTITY + RF-CBCFG + RF-HASH + AUDIT-INFRA-ORPHAN + AUDIT-COMPOSITION-FACTORIES + RF-ORPHAN-SCHEMAS

Фаза 5 (Рефакторинги, по результатам Фазы 4):
  RF-NOOP                         → NoOp consolidation
  RF-NORM                         → Dead ports removal
  RF-RUNST                        → RunStatus rename
  RF-PAGES                        → parse_page_range merge
```

---

## Тестовый Прогон После Всех Изменений

**Субагент:** `py-test-bot`

```
Выполни финальный тестовый прогон после всех модификаций:

1. pytest tests/architecture/ -v          → архитектурные инварианты
2. pytest tests/unit/ -x -q --timeout=60  → unit тесты
3. pytest tests/ --co -q                  → проверка что все тесты собираются
4. mypy --strict src/bioetl/ 2>&1 | tail -20  → type check

Если есть падения — создай FAIL-* тикет для py-debug-bot.
```
