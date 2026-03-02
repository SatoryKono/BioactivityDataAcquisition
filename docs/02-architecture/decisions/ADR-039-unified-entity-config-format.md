# ADR-039: Unified Entity Configuration Format

**Status:** Accepted
**Date:** 2026-02-24
**Decision makers:** @BioETL-Team
**Related:** ADR-025 (Pipeline Config Unification), ADR-027 (DQ Rules Externalization), ADR-028 (Filter Rules Externalization), ADR-029 (Convention-based Config)

## Context

До рефакторинга конфигурация одного стандартного pipeline была распределена по **11 файлам**
в 9 разных директориях:

```
configs/
├── pipelines/{provider}/{entity}.yaml        # Pipeline execution settings
├── schemas/{provider}/{entity}.yaml          # Column groups, content_hash
├── quality/entities/{provider}/{entity}.yaml # DQ rules
├── filters/entities/{provider}/{entity}.yaml # Silver/Gold filter rules
├── contracts/pipelines/{provider}/{entity}.yaml  # PK, merge_keys
├── hash_policy/{provider}/{entity}.yaml      # Hash algorithm config
├── enums/{provider}/{entity}.yaml            # Enum values (post ADR-038)
├── sources/{provider}.yaml                   # Provider API settings
├── quality/providers/{provider}.yaml         # Provider DQ defaults
├── filters/providers/{provider}.yaml         # Provider filter defaults
└── pipelines/_base.yaml                      # Global execution defaults
```

### Проблемы

1. **Навигационная нагрузка**: изменение одного pipeline требует редактирования 5–7 файлов
2. **Рассинхронизация**: изменения в schema не синхронизировались с DQ rules (разные PR)
3. **Именование без иерархии**: файлы не группированы по принадлежности к entity
4. **Дублирование provider/entity**: поля `provider` и `entity` повторялись в каждом файле
5. **Сложность тестирования**: тест для одного pipeline нуждался в фикстурах из 11 путей
6. **`config_loader.py` перегружен**: множество ad-hoc merge функций вместо единого механизма

### Катализатор

ADR-037 унифицировал механизм deep-merge через `config_merge()`. После этого стало
возможным объединить файлы с гарантированной семантикой слияния.

## Decision

### 1. Unified Entity Config (`configs/entities/{provider}/{entity}.yaml`)

Все конфигурации одного entity объединяются в один файл с явными секциями:

```yaml
# configs/entities/chembl/activity.yaml
version: 1.0.0
provider: chembl
entity: activity

pipeline:
  pipeline_name: chembl_activity
  provider: chembl
  entity_type: activity
  description: Extract biological activity records from ChEMBL API
  business_primary_keys: [activity-id]
  batch_size: 1000
  dq_overrides:
    field_validations: [...]

schema:
  content_hash:
    include: []
    exclude: []
  column_groups: [...]
  silver:
    include_groups: [system, business, dq]
    exclude_fields: []
    alias_policy: preserve
  gold:
    include_groups: [system, business]
    exclude_fields: [-dq-*, -source-batch-id, -index]
    alias_policy: canonical

quality:
  version: 1.1.0
  provider: chembl
  entity: activity
  field_validations: [...]
  cross-field_validations: [...]
  conditional_validations: [...]
  key-nullability: [...]

filters:
  version: 1.0.0
  provider: chembl
  entity: activity
  input_filter: {...}
  extraction_params: {...}
  silver_filters: {...}
  gold_filters: {...}

contracts:
  primary_key: [activity-id]
  merge_keys: [activity-id]
  rename_map: {...}
  hash_include: []
  hash_exclude: [...]

hash_policy:
  algorithm: sha256
  canonicalization: provider + canonical_json_dumps(normalized_record)
  include_fields: [...]
  exclude_fields: [...]
  normalization: {...}
```

### 2. Секции Unified Entity Config

| Секция | Назначение | Соответствует |
|--------|-----------|---------------|
| `pipeline` | Execution settings, batch_size, DQ overrides | legacy `pipelines/{p}/{e}.yaml` |
| `schema` | Column groups, content_hash, Silver/Gold layer filters | legacy `schemas/{p}/{e}.yaml` |
| `quality` | Field/cross/conditional validations, key nullability | legacy `quality/entities/{p}/{e}.yaml` |
| `filters` | Input filter, extraction params, Silver/Gold filters | legacy `filters/entities/{p}/{e}.yaml` |
| `contracts` | PK, merge keys, rename map, hash config | legacy `contracts/pipelines/{p}/{e}.yaml` |
| `hash_policy` | Hash algorithm details and field selection | legacy `hash_policy/{p}/{e}.yaml` |

### 3. Приоритет загрузки в `load_pipeline_config()`

```
Base defaults (configs/base/pipeline.yaml)
    ↓ deep-merge
Unified entity pipeline section (configs/entities/{p}/{e}.yaml → pipeline:)
    ↓ deep-merge (legacy has priority if exists)
Legacy pipeline config (legacy layout path, removed in RF-CFG-035)
    ↓
Convention defaults (ADR-029): paths, table names, file references
    ↓
Hierarchical filter config (ADR-028)
    ↓
Column groups: unified schema section OR schema_file
    ↓
Source section: configs/providers/{provider}.yaml
```

**Правило слияния**: если оба файла существуют (legacy и unified), unified section
предоставляет defaults, legacy — overrides. Legacy имеет приоритет.

### 4. Изменения в `config_loader.py`

#### Новые вспомогательные функции

```python
def load_unified_entity_raw(path: Path) -> dict[str, Any]:
    """Load unified entity YAML file, returning empty dict when absent."""

def get_unified_section(
    unified_raw: dict[str, Any], section: str
) -> dict[str, Any] | None:
    """Get a dict section from unified entity config if present."""
```

#### Обновлённые функции

- `load_column_groups_section()`: принимает `unified_schema` параметр для инлайн-схемы
- `deep_merge()`: делегирует в `config_merge()` (ADR-037)
- `load_base_config()`: упрощён, только один canonical путь

#### Алгоритм `load_pipeline_config()`

```python
unified_raw = load_unified_entity_raw(unified_path)      # configs/entities/
unified_pipeline = get_unified_section(unified_raw, "pipeline")
unified_schema = get_unified_section(unified_raw, "schema")

if legacy_path.exists():
    # Legacy present — legacy overrides unified
    entity_config = deep_merge(unified_pipeline, legacy-entity_config)
elif unified_pipeline:
    # No legacy — unified is sole source
    entity_config = unified_pipeline
else:
    raise ValueError(...)
```

### 5. Архитектура директорий после рефакторинга

```
configs/
├── base/
│   └── pipeline.yaml                # Global execution defaults
├── entities/
│   ├── chembl/                      # 14 entity configs
│   │   ├── activity.yaml
│   │   ├── assay.yaml
│   │   └── ...
│   ├── pubchem/compound.yaml
│   ├── uniprot/
│   ├── pubmed/publication.yaml
│   ├── crossref/publication.yaml
│   ├── openalex/publication.yaml
│   └── semanticscholar/publication.yaml
├── composites/                      # Composite pipeline configs (ADR-026)
│   ├── activity.yaml
│   ├── assay.yaml
│   ├── molecule.yaml
│   ├── publication.yaml
│   └── target.yaml
├── providers/
│   └── {provider}.yaml              # Provider API + quality + filters (unified)
├── base/
│   ├── pipeline.yaml                # Global pipeline/filter defaults
│   └── quality.yaml                 # Global DQ defaults
├── enums/
│   └── chembl.yaml                  # Enum values (ADR-038)
├── composites/
│   ├── {entity}.yaml                # Composite pipeline configs (ADR-026)
│   └── field_groups/publication.yaml
└── naming_exceptions.yaml
```

**Удалённые директории** (RF-CFG-035):
- legacy provider/entity pipeline directory — перенесено в `configs/entities/`
- `configs/schemas/{providers}/` — поглощено в `configs/entities/{p}/{e}.yaml#schema` <!-- doc-lint: allow-legacy -->
- legacy `quality/entities` directory — поглощено в `configs/entities/{p}/{e}.yaml#quality`
- legacy `filters/entities` directory — поглощено в `configs/entities/{p}/{e}.yaml#filters`
- `configs/contracts/` — поглощено в `configs/entities/{p}/{e}.yaml#contracts`

### 6. Test Guard (`test_pipeline_external_schema_non_empty.py`)

Архитектурный тест обновлён для поддержки обоих форматов:

```python
def find_pipeline_config(provider: str, entity_type: str) -> tuple[Path | None, str]:
    """Find pipeline config in legacy or unified location."""
    legacy = Path("<legacy-removed-layout>") / provider / f"{entity_type}.yaml"
    if legacy.exists():
        return legacy, "legacy"
    unified = Path("configs/entities") / provider / f"{entity_type}.yaml"
    if unified.exists():
        return unified, "unified"
    return None, ""
```

Для unified формата тест проверяет инлайн `schema:` секцию вместо external schema file.

### 7. LOC Exemption

`config_loader.py` освобождён от архитектурного лимита до **725 LOC** (было 680) в
`tests/architecture/test_code_metrics.py` — рост обусловлен добавлением `load_unified_entity_raw()`,
`get_unified_section()` и обновлённой логики `load_pipeline_config()`.

## Consequences

### Positive

1. **5-в-1**: Один unified entity config заменяет 5–6 отдельных файлов (pipeline, schema, quality, filters, contracts)
2. **Навигация**: Изменение entity требует редактирования одного файла вместо поиска по 9 директориям
3. **Atomic changes**: PR для добавления поля — один файл с изменениями schema + DQ + filters
4. **Backward compatible**: Fallback на legacy paths сохраняет обратную совместимость для composites
5. **DRY**: `provider` и `entity` объявляются один раз на уровне файла
6. **Тестируемость**: Фикстуры для теста одного pipeline в одном файле

### Negative

1. **Большие файлы**: Unified entity config может достигать 400+ строк для сложных entity (activity: ~350 строк)
2. **Секционный конфликт**: При merge из нескольких источников приоритет секций требует понимания алгоритма
3. **`config_loader.py` растёт**: Поддержка двух форматов увеличивает LOC до 721

### Neutral

1. **Legacy fallback остаётся**: `load_pipeline_config()` продолжает проверять legacy layout перед `configs/entities/` для composites и нестандартных конфигов
2. **21 standard pipelines** полностью переведены на unified format; composite pipelines (5) используют `configs/composites/` (ADR-026)
3. **`deep_merge()` делегирует в `config_merge()`** — унифицировано с ADR-037

## Alternatives Considered

### A. Только внешние файлы с ссылками

Сохранить раздельные файлы, но добавить `entity.yaml` как манифест со ссылками:
```yaml
# entity.yaml (manifest only)
includes:
  pipeline: ./pipeline.yaml
  schema: ./schema.yaml
  quality: ./quality.yaml
```

**Rejected**: Не уменьшает количество файлов, добавляет уровень косвенности.

### B. Single YAML с YAML anchors

Использовать YAML-якоря для переиспользования значений внутри файла.

**Rejected**: YAML anchors не переносятся между файлами; ограниченная поддержка в editors.

### C. Полная миграция без fallback

Удалить legacy paths сразу без backward-compat периода.

**Rejected**: Composite pipelines имеют иную структуру конфигов; их migration в рамках этого ADR не проводилась.

## Implementation

### Files Modified

| Файл | Изменение |
|------|-----------|
| `src/bioetl/infrastructure/config_loader.py` | Добавлены `load_unified_entity_raw()`, `get_unified_section()`; обновлены `load_pipeline_config()`, `load_column_groups_section()`, `load_base_config()`, `deep_merge()` |
| `tests/architecture/test_pipeline_external_schema_non_empty.py` | Добавлена `find_pipeline_config()`, поддержка unified формата |
| `tests/architecture/test_code_metrics.py` | Exemption для `config_loader.py`: 680 → 725 LOC |
| `configs/entities/{p}/{e}.yaml` | 21 unified entity configs (all standard pipelines) |

### Deleted Directories (RF-CFG-035)

- legacy provider/entity pipeline directory (21 файлов)
- `configs/schemas/{providers}/` (21 файлов) <!-- doc-lint: allow-legacy -->
- legacy `quality/entities` directory (21 файлов)
- legacy `filters/entities` directory (21 файлов)
- `configs/contracts/` (21 файлов)

## Migration Guide

### Добавление нового entity

Создать один файл `configs/entities/{provider}/{entity}.yaml` со всеми секциями:

```yaml
version: 1.0.0
provider: {provider}
entity: {entity}

pipeline:
  pipeline_name: {provider}-{entity}
  provider: {provider}
  entity_type: {entity}
  # ... execution settings

schema:
  column_groups: [...]
  silver:
    include_groups: [system, business, dq]
  gold:
    include_groups: [system, business]

quality:
  field_validations: [...]

filters:
  silver_filters: {...}
  gold_filters: {...}

contracts:
  primary_key: [...]
  merge_keys: [...]
```

## References

- [ADR-025: Pipeline Config Unification](ADR-025-pipeline-config-unification.md) — исходная унификация paths
- [ADR-027: DQ Rules Externalization](ADR-027-dq-rules-externalization.md) — иерархические DQ правила
- [ADR-028: Filter Rules Externalization](ADR-028-filter-rules-externalization.md) — иерархические filter правила
- [ADR-029: Convention-based Config](ADR-029-output-metadata-unification.md) — convention defaults
- [ADR-037: config_merge() unification](ADR-037-canonical-schema-generation.md) — deep-merge делегирование
- [ADR-038: Enum Externalization](ADR-038-enum-externalization.md) — enum values в YAML
- [Config Unification Plan](../../plans/config-unification-plan.md) — полный план рефакторинга

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-02-24 | Claude Code | Initial version — documenting completed implementation |
