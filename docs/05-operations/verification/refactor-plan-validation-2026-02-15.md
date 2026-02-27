# Валидация плана рефакторинга (PROMPT 1.2–4.2, CFG-001)

Дата проверки: 2026-02-15
Репозиторий: BioETL

## Краткий вывод

План в целом **актуален**, но требует корректировок по приоритетам и ожидаемым результатам:

1. **LINT-001** в текущем состоянии не нужен как отдельный change-set (F401 уже 0).
1. **VERIFY-блоки (3.3/3.4/3.5/4.1/4.2/CFG-001)** — это исследование/диагностика, их нужно выделить в отдельный трек от кодовых рефакторингов.
1. Для части задач нужно уточнить acceptance criteria, чтобы исключить ложные срабатывания:
   - проверять импорты только в `*.py` (без `--pycache--`),
   - для orphan-статуса учитывать регистрацию через фабрики/конфиги,
   - для TEST-ONLY различать «не используется в runtime» и «публичный API re-export».

----------------------------------------------------------------------

## Проверка актуальности по каждому промпту

### Phase 1

- **PROMPT 1.2 (NAME-001)** — актуален.
  - В проекте действительно есть 2 `CleanupResult` (core + bronze).
- **PROMPT 1.3 (NAME-002)** — актуален.
  - В проекте действительно есть 2 `RateLimitConfig` (domain + composition).
- **PROMPT 1.4 (LINT-001)** — **неактуален как отдельный обязательный рефакторинг**.
  - `ruff check src/bioetl/ --select F401` уже возвращает `All checks passed!`.

### Phase 2

- **PROMPT 2.1 (RF-DUP-001)** — актуален.
  - `-load-yaml` в `BaseConfigLoader` и `DQConfigLoader` идентичен.
- **PROMPT 2.2 (RF-DUP-002)** — актуален.
  - `SilverMetadataBuilder.__init__` и `GoldMetadataBuilder.__init__` идентичны.
- **PROMPT 2.3 (RF-DUP-003)** — актуален.
  - `get-source-metadata` идентичен в 3 классах.
- **PROMPT 2.4 (RF-NAME-003)** — актуален.
  - В проекте действительно 2 `LineageMetadata` (domain.models и domain.composite).
- **PROMPT 2.5 (RF-CROSS-001)** — актуален.
  - Есть 2 разные реализации `-get-bioetl-version`, файл `domain/version.py` отсутствует.

### Phase 3

- **PROMPT 3.2 (DOC-001)** — актуален.
- **PROMPT 3.3 (VERIFY-001)** — требует корректировки формулировки статуса.
  - Модуль `subcellular-fraction-data-source.py` связан с production-пайплайном через `subcellular-fraction-transformer`, фабрики и pipeline config.
  - Нельзя рассматривать как orphan без проверки связки «config → factory → transformer → wrapper».
- **PROMPT 3.4 (VERIFY-002)** — актуален как аудит.
  - Предварительно: `TransformerPort`, `PIPELINE-HEALTH-CHECK-PASSED`, `DataClassification` выглядят как test-only/runtime-unused, но нужен формализованный отчёт.
- **PROMPT 3.5 (ANALYSIS-001)** — актуален как диагностика.

### Phase 4

- **PROMPT 4.1 (RF-INV-001)** — актуален как исследование.
- **PROMPT 4.2 (RF-INV-002)** — актуален как исследование.

### CFG-001

- Актуален как пост-рефакторинговая валидация.
- Рекомендуется запускать после каждого батча переименований (Phase 1 + 2).

----------------------------------------------------------------------

## Корректированный план (execution order)

### Track A — Low-risk naming fixes (сначала)

1. NAME-001 (`CleanupResult` → `BronzeCleanupResult`).
1. NAME-002 (`RateLimitConfig` → `RateLimitContext`).
1. RF-NAME-003 (`LineageMetadata` → `CompositeLineageMetadata`).

### Track B — Controlled deduplication

4. RF-DUP-001 (`-load-yaml-file` shared utility).
1. RF-DUP-002 (`-MetadataBuilderBase`).
1. RF-DUP-003 (`SourceMetadataDelegationMixin`).
1. RF-CROSS-001 (`domain/version.py` + unified `get-version`).

### Track C — Documentation

8. DOC-001 (ADR schema↔domain pairs).

### Track D — Verification & analysis (без код-изменений)

9. VERIFY-001 (orphan status).
1. VERIFY-002 (test-only objects).
1. ANALYSIS-001 (cycles).
1. RF-INV-001 (cross-provider extractors).
1. RF-INV-002 (facade re-export audit).
1. CFG-001 (pipeline configs + CLI smoke checks).

----------------------------------------------------------------------

## Набор задач для реализации (готово к постановке в backlog)

## EPIC A — Naming collision cleanup

### TASK A1 — NAME-001 Bronze CleanupResult rename

- **Scope**:
  - `src/bioetl/application/services/bronze-cleanup-service.py`
  - `src/bioetl/application/services/__init__.py`
  - все импорты `CleanupResult` из bronze-сервиса в `src/bioetl/` и `tests/`.
- **Rules**:
  - не менять `application/core/cleanup-service.py`.
- **DoD**:
  - `class CleanupResult` остаётся только в core cleanup.
  - тесты bronze/core cleanup проходят.

### TASK A2 — NAME-002 RateLimitContext rename

- **Scope**:
  - `src/bioetl/composition/bootstrap-contexts.py`
  - `src/bioetl/composition/types.py`
  - все импорты старого имени.
- **Rules**:
  - не менять `domain/configs/base.py` и доменные re-export’ы.
- **DoD**:
  - `class RateLimitConfig` остаётся только в domain/configs/base.py.

### TASK A3 — RF-NAME-003 CompositeLineageMetadata rename

- **Scope**:
  - `src/bioetl/domain/composite/lineage.py`
  - `src/bioetl/domain/composite/__init__.py`
  - импорты в `src/bioetl/` и `tests/`.
- **Rules**:
  - не менять `domain/models/metadata.py`.
- **DoD**:
  - `class LineageMetadata` остаётся только в `domain/models/metadata.py`.

## EPIC B — Deduplication and cross-layer utility

### TASK B1 — RF-DUP-001 shared YAML loader

- **Scope**:
  - `src/bioetl/infrastructure/config/base-config-loader.py`
  - `src/bioetl/infrastructure/config/dq-config-loader.py`
- **DoD**:
  - общая утилита `-load-yaml-file(path: Path)` создана.
  - дублирование удалено.

### TASK B2 — RF-DUP-002 metadata builder base

- **Scope**:
  - `src/bioetl/infrastructure/storage/metadata-builder.py`
- **DoD**:
  - введён `-MetadataBuilderBase`.
  - поведение `SilverMetadataBuilder` / `GoldMetadataBuilder` неизменно.

### TASK B3 — RF-DUP-003 source metadata mixin

- **Scope**:
  - `src/bioetl/application/core/filtered-data-source.py`
  - `src/bioetl/application/core/publication-term-data-source.py`
  - `src/bioetl/application/core/subcellular-fraction-data-source.py`
  - новый mixin-модуль (рекомендуется private `-data-source-mixins.py`).
- **DoD**:
  - дубликат `get-source-metadata` устранён.
  - сигнатура и runtime-поведение сохранены.

### TASK B4 — RF-CROSS-001 unified version source

- **Scope**:
  - `src/bioetl/domain/version.py` (new)
  - `src/bioetl/infrastructure/storage/metadata-builder.py`
  - `src/bioetl/composition/services/metadata-coordinator.py`
  - `src/bioetl/domain/__init__.py` (если нужен публичный re-export).
- **DoD**:
  - единый `get-version()` в domain.
  - локальные `-get-bioetl-version` удалены/заменены алиасом.
  - ARCH-тесты не нарушены.

## EPIC C — Architecture/quality documentation

### TASK C1 — DOC-001 ADR schema-domain pairs

- **Scope**:
  - новый ADR в `docs/02-architecture/decisions/`.
- **DoD**:
  - ADR номер корректный (следующий по порядку).
  - перечислены пары и последствия для разработки.

## EPIC D — Verification research tasks (report-only)

### TASK D1 — VERIFY-001 orphan module status

- **Output**:
  - отчёт со статусом `ACTIVE` / `TEST-ONLY` / `DEAD`.
- **Correction**:
  - учитывать pipeline factory registration и pipeline yaml, не только прямые import’ы.

### TASK D2 — VERIFY-002 test-only objects

- **Objects**: `TransformerPort`, `PIPELINE-HEALTH-CHECK-PASSED`, `DataClassification`.
- **Output**:
  - таблица статусов + рекомендация (оставить / переместить / удалить).

### TASK D3 — ANALYSIS-001 cycles

- **Output**:
  - список циклов + severity + рекомендации без фиксов.

### TASK D4 — RF-INV-001 extractors consolidation study

- **Output**:
  - decision document по консолидации extract\-\* функций.

### TASK D5 — RF-INV-002 facade re-exports audit

- **Output**:
  - таблица `Module | Exports | Dead Exports | Missing | Recommendation`.

### TASK D6 — CFG-001 config validation

- **Output**:
  - протокол загрузки всех pipeline config файлов.
  - проверка CLI help команд после рефакторинга.

----------------------------------------------------------------------

## Рекомендованная стратегия коммитов

1. `refactor: rename bronze CleanupResult → BronzeCleanupResult (NAME-001)`
1. `refactor: rename composition RateLimitConfig → RateLimitContext (NAME-002)`
1. `refactor: rename composite LineageMetadata → CompositeLineageMetadata (RF-NAME-003)`
1. `refactor: extract shared -load-yaml-file utility (RF-DUP-001)`
1. `refactor: extract -MetadataBuilderBase for shared init (RF-DUP-002)`
1. `refactor: extract SourceMetadataDelegationMixin (RF-DUP-003)`
1. `refactor: consolidate -get-bioetl-version to domain/version.py (RF-CROSS-001)`
1. `docs: ADR for schema-domain pair convention (DOC-001)`
1. отдельные report-коммиты для VERIFY/ANALYSIS (без кода).

----------------------------------------------------------------------

## Команды, использованные для валидации

- `rg -n "class CleanupResult|class RateLimitConfig|class LineageMetadata" src/bioetl`
- `ruff check src/bioetl/ --select F401 --output-format=full`
- `rg -n "def -load-yaml\(|def get-source-metadata\(|-get-bioetl-version" src/bioetl`
- `rg -n "subcellular-fraction-data-source|SubcellularFractionDataSource" src/bioetl --glob '*.py'`
- `grep -rn "from.*composite.*lineage.*import.*LineageMetadata" src/bioetl tests`
- `test -f src/bioetl/domain/version.py && echo exists || echo missing`
