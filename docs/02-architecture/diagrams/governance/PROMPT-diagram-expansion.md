______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Промт: Расширение Диаграмм Проекта BioETL

> **Status:** Historical expansion prompt artifact.
> Before reuse, align the execution plan with the current canonical diagram policy
> in [policy.md](policy.md), the measured index in [diagrams-index.md](diagrams-index.md),
> and the current `.mmd`/`views/*.mermaid` split.

*Дата создания: 2026-02-17*

______________________________________________________________________

## Контекст для AI-агента

Ты — архитектурный документатор проекта **BioETL** — ETL-системы для сбора
биоактивных данных из 7 научных API-провайдеров. Проект построен на
Hexagonal Architecture (Ports & Adapters) с 5 слоями и Medallion Architecture
для хранения данных (Bronze → Silver → Gold).

______________________________________________________________________

## Часть 0: Обязательное изучение проекта

Перед началом генерации диаграмм ты **MUST** последовательно изучить:

### 0.1 Документация (читай файлы целиком)

```
docs/00-project/RULES.md                     — Главный документ проекта (правила, архитектура, слои)
docs/00-project/glossary.md                  — Глоссарий терминов
docs/00-project/01-domain-objects.md         — Доменные объекты
docs/00-project/02-etl-layers.md             — ETL-слои
docs/00-project/03-data-flow.md              — Потоки данных
docs/00-project/05-physical-layout.md        — Физическая структура проекта
docs/00-project/architecture-index.md        — Индекс архитектуры
docs/02-architecture/00-overview.md          — Обзор архитектуры
docs/02-architecture/01-domain-layer.md      — Domain Layer
docs/02-architecture/02-application-layer.md — Application Layer
docs/02-architecture/03-infrastructure-layer.md — Infrastructure Layer
docs/02-architecture/04-interfaces-layer.md  — Interfaces Layer
docs/02-architecture/05-composition-layer.md — Composition Layer
docs/02-architecture/diagrams/guide/data-flow-reference.md            — Data Flow
docs/02-architecture/data-layers.md          — Data Layers
docs/02-architecture/system-context.md       — System Context
docs/02-architecture/observability-layers.md — Observability
```

### 0.2 ADR (Architecture Decision Records) — все 38

```
docs/02-architecture/decisions/ADR-001-delta-lake-vs-parquet.md
docs/02-architecture/decisions/ADR-002-medallion-architecture.md
docs/02-architecture/decisions/ADR-003-in-memory-locking-strategy.md
docs/02-architecture/decisions/ADR-004-pydantic-vs-dataclasses.md
docs/02-architecture/decisions/ADR-005-composition-layer-separation.md
docs/02-architecture/decisions/ADR-006-logger-metrics-ports.md
docs/02-architecture/decisions/ADR-007-circuit-breaker-implementation.md
docs/02-architecture/decisions/ADR-008-graceful-shutdown-strategy.md
docs/02-architecture/decisions/ADR-009-paginated-fetcher-mixin.md
docs/02-architecture/decisions/ADR-010-local-only-deployment.md
docs/02-architecture/decisions/ADR-011-remove-watermark-mechanism.md
docs/02-architecture/decisions/ADR-012-storage-clear-contract-and-run-id.md
docs/02-architecture/decisions/ADR-013-async-storage-cleanup.md
docs/02-architecture/decisions/ADR-014-deterministic-writes.md
docs/02-architecture/decisions/ADR-015-pipeline-services-lifecycle.md
docs/02-architecture/decisions/ADR-016-error-handling-strategy.md
docs/02-architecture/decisions/ADR-017-observability-architecture.md
docs/02-architecture/decisions/ADR-018-gold-strict-validation.md
docs/02-architecture/decisions/ADR-019-observability-port-enforcement.md
docs/02-architecture/decisions/ADR-020-basepipeline-decomposition.md
docs/02-architecture/decisions/ADR-021-ddd-aggregates-adoption.md
docs/02-architecture/decisions/ADR-022-tracing-noop.md
docs/02-architecture/decisions/ADR-023-entity-type-patterns.md
docs/02-architecture/decisions/ADR-024-entity-naming-unification.md
docs/02-architecture/decisions/ADR-025-pipeline-config-unification.md
docs/02-architecture/decisions/ADR-026-composite-pipeline-pattern.md
docs/02-architecture/decisions/ADR-027-dq-rules-externalization.md
docs/02-architecture/decisions/ADR-028-filter-rules-externalization.md
docs/02-architecture/decisions/ADR-029-output-metadata-unification.md
docs/02-architecture/decisions/ADR-030-publication-pagination-strategy.md
docs/02-architecture/decisions/ADR-031-loading-strategy-formalization.md
docs/02-architecture/decisions/ADR-032-unified-http-client.md
docs/02-architecture/decisions/ADR-033-publication-validation-strategy.md
docs/02-architecture/decisions/ADR-034-schema-domain-pairs.md
docs/02-architecture/decisions/ADR-035-json-field-typing-policy.md
docs/02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md
docs/02-architecture/decisions/ADR-037-canonical-schema-generation.md
docs/02-architecture/decisions/ADR-038-enum-externalization.md
```

### 0.3 Существующий corpus диаграмм (НЕ дублировать!)

Не опирайся на старую модель `docs/02-architecture/diagrams/*.mermaid` как на
current canonical corpus. Актуальный baseline измеряется через:

- `docs/02-architecture/diagrams/governance/diagrams-index.md`
- `docs/02-architecture/diagrams/governance/diagram-views-inventory.md`
- `docs/02-architecture/diagrams/governance/policy.md`

Текущая naming/model split:

- canonical source diagrams: `docs/02-architecture/diagrams/**/*.mmd`
- decomposed views only: `docs/02-architecture/diagrams/views/*.mermaid`

Перед созданием новых диаграмм сверяй measured inventory, а не historical
списки из этого prompt.

### 0.4 Исходный код (ключевые модули для чтения)

**Обязательно прочитай исходный код** следующих ключевых модулей для точности
отображения классов, методов и связей на диаграммах:

```
# Domain Layer — Aggregates
src/bioetl/domain/aggregates/pipeline-run.py
src/bioetl/domain/aggregates/batch.py
src/bioetl/domain/aggregates/quarantine-entry.py
src/bioetl/domain/aggregates/events.py

# Domain Layer — Ports (все 24 порта)
src/bioetl/domain/ports/__init__.py
src/bioetl/domain/ports/data-source.py
src/bioetl/domain/ports/storage.py
src/bioetl/domain/ports/locking.py
src/bioetl/domain/ports/checkpoint.py
src/bioetl/domain/ports/quarantine.py
src/bioetl/domain/ports/observability.py
src/bioetl/domain/ports/resilience.py
src/bioetl/domain/ports/health_check.py
src/bioetl/domain/ports/validation.py
src/bioetl/domain/ports/audit.py
src/bioetl/domain/ports/metadata.py
src/bioetl/domain/ports/shutdown.py
src/bioetl/domain/ports/runner.py
src/bioetl/domain/ports/pii.py

# Domain Layer — Config
src/bioetl/domain/config/pipeline.py
src/bioetl/domain/config/runtime.py
src/bioetl/domain/config/dq.py
src/bioetl/domain/config/validation.py

# Domain Layer — Value Objects
src/bioetl/domain/value-objects/activity.py
src/bioetl/domain/value-objects/dq-metrics.py
src/bioetl/domain/value-objects/run-context.py
src/bioetl/domain/value-objects/compound-ids.py
src/bioetl/domain/value-objects/taxonomy-id.py

# Domain Layer — Entities
src/bioetl/domain/entities/base.py
src/bioetl/domain/entities/chembl_activity.py
src/bioetl/domain/entities/pubchem.py
src/bioetl/domain/entities/uniprot.py
src/bioetl/domain/entities/crossref.py
src/bioetl/domain/entities/pubmed.py

# Domain Layer — Services
src/bioetl/domain/behavior/data-normalization-service.py
src/bioetl/domain/behavior/identity-service.py
src/bioetl/domain/behavior/unit-converter.py
src/bioetl/domain/behavior/activity-aggregator.py
src/bioetl/domain/behavior/value-validator.py
src/bioetl/domain/behavior/dq-serializer.py

# Domain Layer — Exceptions & Types
src/bioetl/domain/exceptions/__init__.py
src/bioetl/domain/exceptions/base.py
src/bioetl/domain/exceptions/network.py
src/bioetl/domain/exceptions/data-quality.py
src/bioetl/domain/types.py
src/bioetl/domain/error-classifier.py
src/bioetl/domain/medallion.py
src/bioetl/domain/resilience.py

# Domain Layer — Schemas (Pandera)
src/bioetl/domain/schemas/base.py
src/bioetl/domain/schemas/chembl/activity.py
src/bioetl/domain/schemas/chembl/molecule.py
src/bioetl/domain/schemas/pubchem/compound.py
src/bioetl/domain/schemas/uniprot/protein.py

# Domain Layer — Filtering
src/bioetl/domain/filtering/gold-config.py
src/bioetl/domain/filtering/silver-config.py
src/bioetl/domain/filtering/column-filter.py

# Domain Layer — Composite
src/bioetl/domain/composite/config.py
src/bioetl/domain/composite/state.py
src/bioetl/domain/composite/strategy.py
src/bioetl/domain/composite/lineage.py

# Domain Layer — Gold Contracts
src/bioetl/domain/contracts/gold/-base.py
src/bioetl/domain/contracts/gold/chembl.py

# Application Layer — Core
src/bioetl/application/core/runner.py
src/bioetl/application/core/batch-executor.py
src/bioetl/application/core/record-processor.py
src/bioetl/application/core/batch-transformer.py
src/bioetl/application/core/batch-writer.py
src/bioetl/application/core/batch-metrics.py
src/bioetl/application/core/base-transformer.py
src/bioetl/application/core/pipeline-services.py
src/bioetl/application/core/lock-manager.py
src/bioetl/application/core/checkpoint-manager.py
src/bioetl/application/core/preflight-service.py
src/bioetl/application/core/postrun-service.py
src/bioetl/application/core/lifecycle/heartbeat.py
src/bioetl/application/core/lifecycle/shutdown.py
src/bioetl/application/core/quarantine-manager.py
src/bioetl/application/core/cleanup-service.py
src/bioetl/application/core/filtered-data-source.py

# Application Layer — Composite Pipeline
src/bioetl/application/composite/coordinator.py
src/bioetl/application/composite/runner_pkg/runner.py
src/bioetl/application/composite/merger.py
src/bioetl/application/composite/aggregator.py
src/bioetl/application/composite/dependency-coordinator.py
src/bioetl/application/composite/cross-validator.py
src/bioetl/application/composite/deduplication.py

# Application Layer — Pipeline Transformers (примеры)
src/bioetl/application/pipelines/chembl/activity-transformer.py
src/bioetl/application/pipelines/chembl/molecule-transformer.py
src/bioetl/application/pipelines/chembl/base-chembl-transformer.py
src/bioetl/application/pipelines/pubmed/transformer.py
src/bioetl/application/pipelines/crossref/transformer.py

# Application Layer — Observability
src/bioetl/application/observability/observer.py

# Infrastructure Layer — Storage
src/bioetl/infrastructure/storage/bronze-writer.py
src/bioetl/infrastructure/storage/silver-writer.py
src/bioetl/infrastructure/storage/gold-writer.py
src/bioetl/infrastructure/storage/base-delta-writer.py
src/bioetl/infrastructure/storage/delta-reader.py
src/bioetl/infrastructure/storage/metadata-writer.py
src/bioetl/infrastructure/storage/retention-manager.py

# Infrastructure Layer — HTTP
src/bioetl/infrastructure/adapters/http/client.py
src/bioetl/infrastructure/adapters/http/circuit-breaker.py
src/bioetl/infrastructure/adapters/http/rate-limiter.py
src/bioetl/infrastructure/adapters/http/health-monitor.py
src/bioetl/infrastructure/adapters/http/pagination.py

# Infrastructure Layer — Provider Adapters
src/bioetl/infrastructure/adapters/base.py
src/bioetl/infrastructure/adapters/chembl/client.py
src/bioetl/infrastructure/adapters/pubchem/client.py
src/bioetl/infrastructure/adapters/uniprot/client.py
src/bioetl/infrastructure/adapters/crossref/client.py
src/bioetl/infrastructure/adapters/pubmed/pubmed-client.py
src/bioetl/infrastructure/adapters/openalex/client.py
src/bioetl/infrastructure/adapters/semanticscholar/adapter.py

# Infrastructure Layer — Other
src/bioetl/infrastructure/locking/memory-lock.py
src/bioetl/infrastructure/checkpoint/local-checkpoint.py
src/bioetl/infrastructure/quarantine/unified.py
src/bioetl/infrastructure/observability/logging.py
src/bioetl/infrastructure/observability/metrics.py
src/bioetl/infrastructure/observability/tracing.py
src/bioetl/infrastructure/observability/anomaly/detector.py
src/bioetl/infrastructure/validation/pandera-validator.py
src/bioetl/infrastructure/security/pii-hasher.py
src/bioetl/infrastructure/config/pipeline-config-loader.py
src/bioetl/infrastructure/config/dq-config-loader.py
src/bioetl/infrastructure/config/filter-config-loader.py

# Composition Layer
src/bioetl/composition/entrypoints.py
src/bioetl/composition/bootstrap/runtime/assembly.py
src/bioetl/composition/bootstrap/runtime/pipeline.py
src/bioetl/composition/bootstrap/runtime/runner.py
src/bioetl/composition/bootstrap/runtime/composite.py
src/bioetl/composition/bootstrap/runtime/observability.py
src/bioetl/composition/factories/pipeline-factory.py
src/bioetl/composition/factories/runner-factory.py
src/bioetl/composition/factories/services-factory.py
src/bioetl/composition/factories/storage-factory.py
src/bioetl/composition/factories/http-client-factory.py
src/bioetl/composition/factories/data-source-factory.py
src/bioetl/composition/factories/transformer-factory.py
src/bioetl/composition/factories/dq-factory.py
src/bioetl/composition/providers/provider-registry.py
src/bioetl/composition/providers/registration.py
src/bioetl/composition/registry_api.py

# Interfaces Layer
src/bioetl/interfaces/cli/main.py
src/bioetl/interfaces/cli/commands/run.py
src/bioetl/interfaces/cli/commands/run-all.py
src/bioetl/interfaces/cli/commands/run-composite.py
src/bioetl/interfaces/cli/commands/health.py
src/bioetl/interfaces/cli/commands/export.py
src/bioetl/interfaces/cli/commands/quarantine.py
src/bioetl/interfaces/cli/commands/maintenance.py
src/bioetl/interfaces/http/health-server.py
```

### 0.5 Diagram Policy (стандарты)

Прочитай `docs/02-architecture/diagrams/governance/policy.md`
(канонический policy; historical context хранится в
`docs/02-architecture/diagrams/governance/00-diagramming-policy.md`).
Ключевые правила:

- **Формат**: новые canonical diagrams создаются как Mermaid `.mmd`;
  `.mermaid` используется для decomposed views в `docs/02-architecture/diagrams/views/`
- **Naming**: `NN-topic-name.mmd` (kebab-case, NN-prefix для сортировки)
- **Theme init**:
  ```
  %%{init: {'layout': 'elk', 'theme': 'base', 'themeVariables': {'fontFamily': 'Inter, Roboto, sans-serif'}, 'elk': {'mergeEdges': true, 'nodePlacementStrategy': 'BRANDES_KOEPF', 'edgeRouting': 'ORTHOGONAL'}}}%%
  ```
- **Цвета**: Domain=#7c3aed, Application=#16a34a, Infrastructure=#dc2626, Composition=#f59e0b, Interfaces=#2563eb; Medallion palette см. policy
- **Каждая диаграмма MUST** содержать: Title (как comment), Legend (если нужна), RULES.md reference

______________________________________________________________________

## Часть 1: Генерация 500 НОВЫХ диаграмм

После изучения проекта предложи **500 новых уникальных диаграмм**, которых
**ещё нет** в текущем canonical/view corpus. Для каждой диаграммы укажи:

1. **Порядковый номер** (1–500)
1. **Название** (англ.)
1. **Тип диаграммы** (одно из: `classDiagram`, `sequenceDiagram`, `flowchart`,
   `stateDiagram`, `erDiagram`, `C4Context`, `C4Container`, `C4Component`,
   `mindmap`, `timeline`, `gantt`, `pie`, `gitgraph`, `block-beta`,
   `architecture-beta`, `sankey-beta`, `xychart-beta`)
1. **Категория** (одна из: Architecture, DataFlow, Pattern, Component,
   Interaction, Lifecycle, Configuration, Provider, Testing, Security,
   Observability, Composite, DomainModel, ErrorHandling, Performance)
1. **Краткое описание** (1 предложение)

Распредели диаграммы по категориям равномерно, но с акцентом на:

- **Architecture** (~60): высокоуровневая архитектура, C4, deployment
- **DataFlow** (~60): потоки данных через Bronze/Silver/Gold
- **Pattern** (~50): паттерны проектирования, применённые в проекте
- **Component** (~50): внутреннее устройство ключевых компонентов
- **Interaction** (~50): взаимодействия между компонентами
- **Lifecycle** (~40): жизненные циклы и state machines
- **Provider** (~50): специфика каждого из 7 провайдеров
- **Configuration** (~30): конфигурация, schemas, YAML
- **DomainModel** (~30): доменная модель, entities, value objects
- **Composite** (~20): composite pipeline паттерн
- **Observability** (~20): tracing, metrics, logging
- **ErrorHandling** (~20): ошибки, retry, circuit breaker
- **Testing** (~10): тестирование, VCR, architecture tests
- **Security** (~5): PII hashing, secrets
- **Performance** (~5): memory monitoring, adaptive batching

### Требования к качеству предложений

- **Уникальность**: каждая диаграмма должна покрывать отдельный аспект,
  не повторяя текущий measured corpus и не дублируя другие предложения
- **Конкретность**: название и описание должны быть конкретными,
  а не общими ("Data Flow" — плохо, "ChEMBL Activity Bronze→Silver Transformation
  Including Field Mapping and Content Hash Calculation" — хорошо)
- **Привязка к коду**: каждая диаграмма должна отражать реальные классы,
  методы и модули из кодовой базы (534 Python файла)
- **Разнообразие типов**: используй минимум 10 разных типов Mermaid-диаграмм

______________________________________________________________________

## Часть 2: Выбор 50 наиболее важных

Из 500 предложенных выбери **50 наиболее информативных** диаграмм.

### Критерии оценки (каждый 1–10 баллов)

| Критерий     | Вес  | Описание                                                             |
| ------------ | ---- | -------------------------------------------------------------------- |
| **Arch**     | ×2.0 | Архитектурная важность: насколько критична для понимания архитектуры |
| **Doc**      | ×1.5 | Документационная ценность: полезность для нового разработчика        |
| **Freq**     | ×1.5 | Частота использования: как часто нужна при работе с проектом         |
| **Complex**  | ×2.0 | Сложность без диаграммы: насколько сложно понять без визуализации    |
| **Coverage** | ×1.0 | Охват кодовой базы: сколько компонентов покрывает                    |

**Формула**: `Priority = (Arch×2 + Doc×1.5 + Freq×1.5 + Complex×2 + Coverage×1) / 8`

### Ограничения при выборе

- Минимум 3 типа диаграмм из: `classDiagram`, `sequenceDiagram`, `flowchart`,
  `stateDiagram`
- Минимум 5 разных категорий должны быть представлены
- Минимум 2 диаграммы для composite pipeline
- Минимум 3 provider-specific диаграммы
- Минимум 2 диаграммы observability
- Не более 15 диаграмм одной категории

______________________________________________________________________

## Часть 3: Таблица 50 диаграмм

Выведи результат в формате Markdown-таблицы, отсортированной
по Priority (убывание):

```markdown
| # | Название | Тип | Категория | Priority | Arch | Doc | Freq | Complex | Coverage | Обоснование важности | Классы/компоненты на диаграмме |
|---|----------|-----|-----------|----------|------|-----|------|---------|----------|----------------------|-------------------------------|
| 1 | ... | classDiagram | Architecture | 9.75 | 10 | 10 | 9 | 10 | 9 | ... | `Class1`, `Class2`, ... |
```

Для столбца **«Классы/компоненты»** перечисли конкретные имена классов,
функций, модулей или файлов из кодовой базы, которые отображены на диаграмме.
Минимум 3, максимум 15 для каждой диаграммы.

Для столбца **«Обоснование важности»** напиши 2–3 предложения:
почему эта диаграмма попала в TOP-50, какую проблему понимания она решает,
и кому из участников проекта она наиболее полезна.

______________________________________________________________________

## Часть 4: Создание и рендер TOP-25 диаграмм

Из TOP-50 возьми первые **25** (с наивысшим Priority) и для каждой:

### 4.1 Создание Mermaid-файла

- Создай файл в каноническом `.mmd`-каталоге под `docs/02-architecture/diagrams/`
  (`architecture/`, `class-diagrams/` или `foundation/` по смыслу)
- Формат именования: `NN-topic-name.mmd` (NN = следующий свободный номер в выбранной family)
- Каждый файл начинается с:
  ```
  %%{init: {'theme': 'neutral', 'themeVariables': {'fontFamily': 'Inter, system-ui', 'lineWidth': '2'}}}%%
  ```
- Используй **реальные имена классов** из кода (не выдуманные!)
- Для class diagrams: указывай реальные публичные методы и атрибуты
- Для sequence diagrams: используй реальные вызовы методов
- Для flowcharts: указывай реальные условия и ветвления
- Минимальный размер: 30 строк (диаграмма должна быть содержательной)
- Максимальный размер: 300 строк (не перегружать)

### 4.2 Рендер в PNG

После создания всех 25 `.mmd`-файлов, отрендери каждый в PNG:

```bash
# Установка (если не установлен)
npm install -g @mermaid-js/mermaid-cli

# Создай puppeteer config для высокого DPI
cat > /tmp/puppeteer-config.json << 'EOF'
{
  "executablePath": "",
  "args": ["--no-sandbox"]
}
EOF

# Рендер каждой диаграммы
# Используй scale=3 для ~300 DPI (base 96 DPI × 3 = 288 DPI)
# Для сложных диаграмм с мелким текстом — scale=4 (384 DPI)
for f in docs/02-architecture/diagrams/foundation/2[6-9]-*.mmd \
         docs/02-architecture/diagrams/foundation/3[0-9]-*.mmd \
         docs/02-architecture/diagrams/foundation/4[0-9]-*.mmd \
         docs/02-architecture/diagrams/foundation/50-*.mmd; do
    base=$(basename "$f" .mmd)
    mmdc -i "$f" \
         -o "docs/02-architecture/diagrams/png/${base}.png" \
         -s 3 \
         -w 2400 \
         -b white \
         -p /tmp/puppeteer-config.json
done
```

**Критерий читаемости**: после рендера открой каждый PNG и проверь,
что все надписи свободно читаются при 100% масштабе. Если текст мелкий:

- Увеличь `--scale` до 4 или 5
- Или увеличь `--width` до 3200+
- Или упрости диаграмму, разбив на 2 отдельных

### 4.3 Обновление индекса

После создания всех файлов обнови:

1. `docs/02-architecture/diagrams/governance/diagrams-index.md` — добавь новые диаграммы
1. Создай директорию `docs/02-architecture/diagrams/png/` если не существует

______________________________________________________________________

## Часть 5: Проверка качества (self-review)

После завершения выполни самопроверку:

### 5.1 Корректность имён

```bash
# Проверь, что все классы из диаграмм существуют в коде
# Для каждого имени класса на каждой диаграмме:
grep -rn "class ИмяКласса" src/bioetl/ --include="*.py"
```

### 5.2 Соответствие архитектуре

- Проверь, что зависимости на диаграммах соответствуют реальной матрице импортов (ARCH-001)
- domain НЕ зависит от infrastructure
- application НЕ зависит от infrastructure
- infrastructure НЕ зависит от application/composition/interfaces

### 5.3 Полнота

- Все 24 порта должны быть отражены хотя бы на 1 диаграмме
- Все 7 провайдеров должны быть отражены хотя бы на 1 диаграмме
- Все 3 aggregate (PipelineRun, Batch, QuarantineEntry) должны быть отражены
- Medallion layers (Bronze, Silver, Gold) должны быть отражены

### 5.4 Рендер

- Все 25 PNG файлов существуют в `docs/02-architecture/diagrams/png/`
- Каждый PNG весит > 50KB (не пустой/битый)
- Текст на каждой диаграмме читаем при 100% масштабе

______________________________________________________________________

## Справочная информация

### Архитектура проекта (5 слоёв)

```
Interfaces  → CLI (Click), HTTP health server
Composition → Bootstrap, Factories, Registry (DI)
Application → PipelineRunner, BatchExecutor, BatchProcessingService, Transformers, Services
Domain      → Ports (24 Protocol), Entities, VOs, Aggregates, Config, Schemas, Services
Infrastructure -> Adapters (7 external APIs + ID mapping provider seam), Storage (Bronze/Silver/Gold), HTTP, Locking, Observability
```

### Матрица импортов

| From \\ To     | domain | application | infrastructure | composition | interfaces |
| -------------- | ------ | ----------- | -------------- | ----------- | ---------- |
| domain         | ✅     | ❌          | ❌             | ❌          | ❌         |
| application    | ✅     | ✅          | ❌             | ❌          | ❌         |
| infrastructure | ✅     | ❌          | ✅             | ❌          | ❌         |
| composition    | ✅     | ✅          | ✅             | ✅          | ❌         |
| interfaces     | ✅     | ✅          | ✅             | ✅          | ✅         |

### 7 провайдеров

| Provider        | Entity Types                                                                                                                                                                                          | Adapter                  |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| ChEMBL          | activity, molecule, target, assay, compound-record, cell-line, protein-class, tissue, publication, publication-term, publication-similarity, subcellular-fraction, assay-parameters, target-component | `ChemblClient`           |
| PubChem         | compound                                                                                                                                                                                              | `PubChemClient`          |
| UniProt         | protein, idmapping                                                                                                                                                                                    | `UniProtClient`          |
| CrossRef        | publication                                                                                                                                                                                           | `CrossRefClient`         |
| PubMed          | publication                                                                                                                                                                                           | `PubMedClient`           |
| OpenAlex        | publication                                                                                                                                                                                           | `OpenAlexClient`         |
| SemanticScholar | publication                                                                                                                                                                                           | `SemanticScholarAdapter` |

### 24 доменных порта

```
DataSourcePort, FilterableDataSourcePort, BronzeStoragePort, SilverStoragePort, GoldStoragePort, MergedStoragePort, LockPort,
CheckpointPort, QuarantinePort, TracingPort, MetricsPort, LoggerPort,
HealthCheckPort, AuditPort, DQMonitorPort, DQReportWriterPort,
PIIHasherPort, DataNormalizationPort, ValidationPort, MetadataPort,
MetadataCoordinatorPort, DeltaReaderPort, MemoryMonitorPort,
ShutdownPort, SerializationPort, DQConfigLoaderPort, FilterConfigLoaderPort
```

### 3 DDD Aggregates

| Aggregate       | States                                         | Key Methods                                                   |
| --------------- | ---------------------------------------------- | ------------------------------------------------------------- |
| PipelineRun     | PENDING → RUNNING → COMPLETED/FAILED/CANCELLED | start(), complete-stage(), fail(), cancel()                   |
| Batch           | OPEN → SEALED → WRITING → COMMITTED/FAILED     | add-record(), seal(), mark-writing(), commit(), mark-failed() |
| QuarantineEntry | NEW → UNDER-REVIEW → RESOLVED/DISCARDED        | start-review(), resolve(), discard()                          |

### Ключевые параметры

| Parameter                        | Value        |
| -------------------------------- | ------------ |
| Lock TTL                         | 90s          |
| Heartbeat Interval               | 30s          |
| Circuit Breaker Threshold        | 5 failures   |
| Circuit Breaker Recovery Timeout | 300s         |
| DQ Soft Threshold                | 5%           |
| DQ Hard Threshold                | 20%          |
| Bronze Retention                 | 90 days      |
| Quarantine Retention             | 30 days      |
| Max Retry Attempts               | 3            |
| Batch Size (default)             | 1000 records |

### Статистика кодовой базы

| Слой           | Python файлов |
| -------------- | ------------- |
| domain         | ~170          |
| application    | ~100          |
| infrastructure | ~85           |
| composition    | ~55           |
| interfaces     | ~25           |
| **Всего**      | **~534**      |
