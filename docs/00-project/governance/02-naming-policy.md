______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Политика именования сущностей

*Синхронизировано с RULES.md v6.1.2 и ADR-024 | Последнее обновление: 2026-04-09*

______________________________________________________________________

## 1. Общие принципы

Все имена в проекте BioETL должны быть самодокументированными, следовать стандартам Ubiquitous Language (см. `glossary.md`) и соответствовать архитектурному паттерну `{Provider}{CanonicalTerm}`.

### 1.1. Канонические термины (Canonical Terms)

Согласно ADR-024, для обеспечения согласованности между провайдерами используются следующие канонические термины:

| Концепт              | Канонический термин | Примеры (ChEMBL, PubChem, PubMed)        |
| :------------------- | :------------------ | :--------------------------------------- |
| Научная публикация   | **Publication**     | `ChemblPublication`, `PubMedPublication` |
| Химическая структура | **Molecule**        | `ChemblMolecule`, `PubchemMolecule`      |
| Биологическая мишень | **Target**          | `ChemblTarget`, `UniprotTarget`          |
| Результат анализа    | **Activity**        | `ChemblActivity`                         |

### 1.2. Две поверхности именования

BioETL использует два согласованных, но не всегда одинаковых naming surface:

| Поверхность                     | Назначение                                                                                   | Примеры                                                                                      |
| :------------------------------ | :------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------- |
| **Canonical domain names**      | Domain entities, domain DTOs, часть domain schemas и терминология Ubiquitous Language        | `PubchemMolecule`, `UniprotTarget`, `ChemblPublication`                                      |
| **Stable external identifiers** | CLI `--pipeline`, `pipeline.pipeline_name`, часть pipeline/transformer/schema public surface | `pubchem_compound`, `uniprot_protein`, `PubChemCompoundPipeline`, `UniProtProteinGoldSchema` |

Правило по умолчанию: использовать canonical term. Исключения допустимы только
для stable external/public surface и должны быть зафиксированы в
`configs/naming_exceptions.yaml`.

______________________________________________________________________

## 2. Правила именования по категориям

### 2.1. Доменные сущности (Domain Entities)

**Формат:** `{Provider}{CanonicalTerm}` (PascalCase)
**Место:** `src/bioetl/domain/entities/`

- **MUST**: Использовать канонический термин вместо API-специфичного (напр., `Molecule` вместо `Compound`).
- **MUST**: Использовать префикс провайдера для предотвращения коллизий.
- **Исключения**: Общие сущности, не привязанные к провайдеру (напр., `Bioactivity`).

### 2.2. Пайплайны (Pipelines)

#### 2.2.1. Идентификаторы пайплайнов (Pipeline IDs)

**Формат:** `{provider}_{entity}` (snake_case)
**Используется в:** YAML конфигах (`pipeline_name`), CLI (`--pipeline`).

Pipeline ID — это **stable external identifier**, а не обязательно canonical
domain term. Поэтому `pubchem_compound` и `uniprot_protein` допустимы как
policy-backed external IDs, хотя domain использует `PubchemMolecule` и
`UniprotTarget`.

#### 2.2.2. Классы пайплайнов

**Формат:** `{Provider}{EntitySurfaceTerm}Pipeline` (PascalCase)
**Место:** `src/bioetl/application/pipelines/{provider}/`

- **SHOULD**: По умолчанию использовать canonical term.
- **MAY**: Для stable external/public surface использовать provider-facing term,
  если он зафиксирован в `configs/naming_exceptions.yaml`.
- **Примеры**: `ChemblPublicationPipeline`, `PubChemCompoundPipeline`, `UniProtProteinPipeline`.

### 2.3. Трансформеры (Transformers)

**Формат:** `{Provider}{EntitySurfaceTerm}Transformer` (PascalCase)
**Место:** `src/bioetl/application/pipelines/{provider}/`

- **MUST**: Наследовать от `BaseTransformer` или `BaseChemblTransformer`.
- **SHOULD**: Использовать canonical term по умолчанию.
- **MAY**: Использовать stable public surface term для provider-facing pipeline layers,
  если это policy-backed exception.

### 2.4. Схемы валидации (Pandera/PyArrow)

#### 2.4.1. Pandera Schemas (Gold)

**Формат:** `{Provider}{EntitySurfaceTerm}GoldSchema` (PascalCase)
**Место:** `src/bioetl/domain/contracts/gold/`

- **SHOULD**: Canonical term по умолчанию.
- **MAY**: Stable public surface term для generated/public contract names,
  если это зафиксировано в exception registry.

#### 2.4.2. PyArrow Schemas (Silver)

**Формат:** `CHEMBL-{CANONICAL-TERM}-SCHEMA` (UPPER-SNAKE-CASE)
**Место:** `src/bioetl/infrastructure/schemas/silver.py`

#### 2.4.3. Assembler Services

**Формат:** `{Entity}Assembler` (PascalCase)
**Место:** `src/bioetl/application/services/`

- **MAY**: Использовать суффикс `Assembler` для сервисов, которые собирают или агрегируют данные из нескольких источников.
- **SHOULD**: Предпочитать `*Service` для стандартных сервисов.
- **MUST**: Быть зафиксированным в `configs/naming_exceptions.yaml`, если используется вместо `*Service`.

### 2.5. Layer-Aware Suffix Contract

ADR-041 naming governance дополняется явным layer-aware suffix contract. Новые
first-party символы **MUST** укладываться в разрешённую матрицу слоя и в
canonical family registry, опубликованные в machine-readable policy:
`configs/quality/layered_suffix_policy.yaml`.

| Слой | Разрешённые суффиксы | Запрещённые first-party суффиксы |
| :--- | :--- | :--- |
| `domain` | `Port`, `Protocol`, `ABC`, `Schema`, `ValueObject` | `Service`, `Manager`, `Handler`, `Adapter`, `Factory`, `Runner` |
| `application` | `Service`, `RuntimeService`, `Runner`, `Coordinator`, `Handler` | `Adapter`, `Client` |
| `infrastructure` | `Adapter`, `Client`, `Factory`, `Writer`, `Reader` | `Service`, `Manager`, `Runner` |
| `composition` | `Factory`, `Builder`, `Module`, `Registry` | `Adapter`, `Client` |
| `interfaces` | `Command`, `Handler`, `Adapter`, `Registry` | `Service`, `Manager`, `Runner` |

### 2.6. Canonical Family Registry

Для naming-debt семейств, где исторически сосуществовали разные суффиксы,
canonical owner фиксируется отдельно. Новый символ из такого семейства
**MUST NOT** появляться без обновления canonical family registry и
архитектурных тестов.

| Family ID | Канонические символы | Разрешённый legacy/compatibility след |
| :--- | :--- | :--- |
| `pipeline_execution` | `PipelineRunner`, `PipelineService`, `PipelineRunnerService` | временные dependency shims и doc aliases до удаления |
| `composite_execution` | `CompositePipelineRunner`, `MergeService` | исторические `*Builder`/`*Join*` helper-модули только по registry |
| `lock_runtime_admin` | `LockRuntimeService`, `LockService` | constructor kwargs и helper seams до закрытия migration window |
| `storage_boundary` | `BronzeStoragePort`, `SilverStoragePort`, `GoldStoragePort`, `MergedStoragePort`, `*Adapter`, `*Client` | compatibility re-exports only if registry-backed |

______________________________________________________________________

## 3. Таблицы и Файлы

### 3.1. Имена таблиц (Silver/Gold)

**Формат:** `{provider}_{entity}` (snake_case)

- Должны совпадать с идентификатором пайплайна.
- **Пример**: `chembl_publication`.

### 3.2. Файлы конфигурации

**Путь**: `configs/entities/{provider}/{entity}.yaml`

- Имя файла должно совпадать с именем сущности (entity).
- **Пример**: `configs/entities/chembl/publication.yaml`.

______________________________________________________________________

## 4. Исключения (Naming Exceptions)

Полный список разрешенных отклонений от правил (напр., `README.md`, `LICENSE`) зафиксирован в файле:
`configs/naming_exceptions.yaml`

Этот реестр также фиксирует различие между canonical domain names и stable
external/public IDs. Если имя намеренно сохраняет provider API term для
CLI/pipeline/schema surface, это должно быть оформлено именно там.

Legacy ADR-024 domain aliases `Document`, `Compound`, and `Protein` не имеют
активной compatibility export surface в `bioetl.domain.entities` и **MUST NOT**
появляться там повторно без явной registry-записи с точным списком экспортируемых
символов и ограниченным окном удаления.

Добавление нового исключения требует обоснования в PR и обновления этого файла.

______________________________________________________________________

## 5. Связанные документы

- [ADR-024: Entity Naming Unification](../../02-architecture/decisions/ADR-024-entity-naming-unification.md)
- [03-file-policy.md](03-file-policy.md) — Политика файлов и директорий
- [glossary.md](../glossary.md) — Ubiquitous Language
