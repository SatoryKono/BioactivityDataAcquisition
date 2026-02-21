# Политика именования сущностей

*Синхронизировано с RULES.md v5.21 и ADR-024 | Последнее обновление: 2026-02-21*

---

## 1. Общие принципы

Все имена в проекте BioETL должны быть самодокументированными, следовать стандартам Ubiquitous Language (см. `glossary.md`) и соответствовать архитектурному паттерну `{Provider}{CanonicalTerm}`.

### 1.1. Канонические термины (Canonical Terms)

Согласно ADR-024, для обеспечения согласованности между провайдерами используются следующие канонические термины:

| Концепт | Канонический термин | Примеры (ChEMBL, PubChem, PubMed) |
| :--- | :--- | :--- |
| Научная публикация | **Publication** | `ChemblPublication`, `PubMedPublication` |
| Химическая структура | **Molecule** | `ChemblMolecule`, `PubchemMolecule` |
| Биологическая мишень | **Target** | `ChemblTarget`, `UniprotTarget` |
| Результат анализа | **Activity** | `ChemblActivity` |

---

## 2. Правила именования по категориям

### 2.1. Доменные сущности (Domain Entities)

**Формат:** `{Provider}{CanonicalTerm}` (PascalCase)
**Место:** `src/bioetl/domain/entities/`

- **MUST**: Использовать канонический термин вместо API-специфичного (напр., `Molecule` вместо `Compound`).
- **MUST**: Использовать префикс провайдера для предотвращения коллизий.
- **Исключения**: Общие сущности, не привязанные к провайдеру (напр., `Bioactivity`).

### 2.2. Пайплайны (Pipelines)

#### 2.2.1. Идентификаторы пайплайнов (Pipeline IDs)
**Формат:** `{provider}-{entity}` (snake-case)
**Используется в:** YAML конфигах (`pipeline-name`), CLI (`--pipeline`).

#### 2.2.2. Классы пайплайнов
**Формат:** `{Provider}{CanonicalTerm}Pipeline` (PascalCase)
**Место:** `src/bioetl/application/pipelines/{provider}/`

### 2.3. Трансформеры (Transformers)

**Формат:** `{Provider}{CanonicalTerm}Transformer` (PascalCase)
**Место:** `src/bioetl/application/pipelines/{provider}/`

- **MUST**: Наследовать от `BaseTransformer` или `BaseChemblTransformer`.

### 2.4. Схемы валидации (Pandera/PyArrow)

#### 2.4.1. Pandera Schemas (Gold)
**Формат:** `{Provider}{CanonicalTerm}GoldSchema` (PascalCase)
**Место:** `src/bioetl/domain/contracts/gold/`

#### 2.4.2. PyArrow Schemas (Silver)
**Формат:** `CHEMBL-{CANONICAL-TERM}-SCHEMA` (UPPER-SNAKE-CASE)
**Место:** `src/bioetl/infrastructure/schemas/silver.py`

---

## 3. Таблицы и Файлы

### 3.1. Имена таблиц (Silver/Gold)

**Формат:** `{provider}-{entity}` (snake-case)
- Должны совпадать с идентификатором пайплайна.
- **Пример**: `chembl-publication`.

### 3.2. Файлы конфигурации

**Путь**: `configs/pipelines/{provider}/{entity}.yaml`
- Имя файла должно совпадать с именем сущности (entity).
- **Пример**: `configs/pipelines/chembl/publication.yaml`.

---

## 4. Исключения (Naming Exceptions)

Полный список разрешенных отклонений от правил (напр., `README.md`, `LICENSE`) зафиксирован в файле:
`configs/naming-exceptions.yaml`

Добавление нового исключения требует обоснования в PR и обновления этого файла.

---

## 5. Связанные документы

- [ADR-024: Entity Naming Unification](../../02-architecture/decisions/ADR-024-entity-naming-unification.md)
- [03-file-policy.md](03-file-policy.md) — Политика файлов и директорий
- [glossary.md](../glossary.md) — Ubiquitous Language
