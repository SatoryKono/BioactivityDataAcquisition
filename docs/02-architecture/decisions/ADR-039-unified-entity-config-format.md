______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-039: Unified Entity Configuration Format

**Date:** 2026-02-24
**Status:** Accepted
**Decision makers:** @BioETL-Team
**Supersedes:** [ADR-025](ADR-025-pipeline-config-unification.md) (partial: active unified entity config format)
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
1. **Рассинхронизация**: изменения в schema не синхронизировались с DQ rules (разные PR)
1. **Именование без иерархии**: файлы не группированы по принадлежности к entity
1. **Дублирование provider/entity**: поля `provider` и `entity` повторялись в каждом файле
1. **Сложность тестирования**: тест для одного pipeline нуждался в фикстурах из 11 путей
1. **`config_loader.py` перегружен**: множество ad-hoc merge функций вместо единого механизма

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
  business_primary_keys: [activity_id]
  batch_size: 1000

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
    exclude_fields: [_dq_*, _source_batch_id, _index]
    alias_policy: canonical

quality:
  version: 1.1.0
  provider: chembl
  entity: activity
  entity_field_validations: [...]
  entity_cross_field_validations: [...]
  entity_conditional_validations: [...]
  key_nullability: [...]

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

| Секция        | Назначение                                             | Соответствует                             |
| ------------- | ------------------------------------------------------ | ----------------------------------------- |
| `pipeline`    | Execution settings, batch_size, DQ overrides           | legacy `pipelines/{p}/{e}.yaml`           |
| `schema`      | Column groups, content_hash, Silver/Gold layer filters | legacy `schemas/{p}/{e}.yaml`             |
| `quality`     | Field/cross/conditional validations, key nullability   | legacy `quality/entities/{p}/{e}.yaml`    |
| `filters`     | Input filter, extraction params, Silver/Gold filters   | legacy `filters/entities/{p}/{e}.yaml`    |
| `contracts`   | PK, merge keys, rename map, hash config                | legacy `contracts/pipelines/{p}/{e}.yaml` |
| `hash_policy` | Hash algorithm details and field selection             | legacy `hash_policy/{p}/{e}.yaml`         |

### 3. Приоритет загрузки в `load_pipeline_config()`

```
Base defaults (configs/base/pipeline.yaml)
    ↓ deep-merge
Provider defaults (configs/providers/{p}.yaml, optional)
    ↓
Unified entity pipeline section (configs/entities/{p}/{e}.yaml → pipeline:)
    ↓
Convention defaults (ADR-029): paths, table names, sink defaults
    ↓
Hierarchical filter config (ADR-028)
    ↓
Schema normalization from unified inline schema (no schema_file branch)
    ↓
Source section merged from provider defaults (no source_file branch)
    ↓
Payload normalization (canonical-only *_file handling; coerces hyphenated aliases)
```

**Текущее правило слияния**: `load_pipeline_config()` читает только canonical unified path
`configs/entities/{provider}/{entity}.yaml`. Legacy file-path fallback удалён; обратная
совместимость ограничена нормализацией payload для hyphenated aliases. Ключи
`schema_file`/`data_schema_file`/`column_groups_file`/`source_file` считаются legacy
migration-only и в active runtime contract должны отбрасываться из документации и fixtures,
а не silently приниматься loader'ом.

### 4. Изменения в loader/normalization boundary

#### Read-stage helpers в `config_loader.py`

```python
def _load_unified_entity_raw(path: Path) -> dict[str, Any]:
    """Load unified entity YAML file, returning empty dict when absent."""


def _get_unified_section(
    unified_raw: dict[str, Any], section: str
) -> dict[str, Any] | None:
    """Get a dict section from unified entity config if present."""
```

`config_loader.py` остаётся orchestration boundary для стадий:

- `read_pipeline_config_payload()`
- `validate_pipeline_config_payload()`
- `map_pipeline_config()`
- `load_pipeline_config()` / `load_pipeline_config_uncached()`

#### Extracted normalization module

Normalization concerns вынесены в
`src/bioetl/infrastructure/config/pipeline_payload_normalization.py`.

Этот модуль теперь владеет:

- convention defaults для file references / layer paths;
- hierarchical filter merge;
- schema normalization bridge через `pipeline_normalizers.py`;
- source section merge;
- transitional payload normalization для legacy/new field shapes.

`config_loader.py` сохраняет compatibility wrappers для test-facing private helpers
(`_apply_file_reference_defaults()`, `_apply_layer_defaults()`,
`_load_source_section()`, `normalize_pipeline_config_payload()`), но их
реализация делегирована в extracted normalization module.

#### Алгоритм `load_pipeline_config()`

```python
config_path = Path(f"configs/entities/{provider}/{entity}.yaml")
unified_raw = _load_unified_entity_raw(config_path)
unified_pipeline = _get_unified_section(unified_raw, "pipeline")
unified_schema = _get_unified_section(unified_raw, "schema")

if not unified_pipeline:
    raise ValueError(...)

defaults = _load_base_config(config_path)
merged = _deep_merge(defaults, unified_pipeline)
payload = PipelineConfigReadPayload(
    config=merged,
    entity_config=unified_pipeline,
    config_path=config_path,
    unified_schema=unified_schema,
)

normalized = normalize_pipeline_config_payload(payload, filter_loader=...)
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

Архитектурный тест использует только canonical unified location:

```python
def _find_pipeline_config(provider: str, entity_type: str) -> Path | None:
    """Find pipeline config in canonical unified location."""
    unified = Path("configs/entities") / provider / f"{entity_type}.yaml"
    if unified.exists():
        return unified
    return None
```

Для unified формата тест проверяет инлайн `schema:` секцию вместо external schema file.

### 7. LOC Exemption

Исторически `config_loader.py` рос во время миграции unified configs, но текущая
реализация уже существенно компактнее и больше не содержит dual file-path lookup.
После extraction-шагов orchestration осталось в `config_loader.py`, а payload
normalization и schema/filter/source assembly вынесены в отдельный infra-module.

## Consequences

### Positive

1. **5-в-1**: Один unified entity config заменяет 5–6 отдельных файлов (pipeline, schema, quality, filters, contracts)
1. **Навигация**: Изменение entity требует редактирования одного файла вместо поиска по 9 директориям
1. **Atomic changes**: PR для добавления поля — один файл с изменениями schema + DQ + filters
1. **Backward compatible**: Transitional payload normalization сохраняет совместимость
   для legacy key shapes без возврата к legacy file-path lookup
1. **DRY**: `provider` и `entity` объявляются один раз на уровне файла
1. **Тестируемость**: Фикстуры для теста одного pipeline в одном файле

### Negative

1. **Большие файлы**: Unified entity config может достигать 400+ строк для сложных entity (activity: ~350 строк)
1. **Секционный конфликт**: При merge из нескольких источников приоритет секций требует понимания алгоритма
1. **Нормализация остаётся сложной**: Поддержка legacy/new payload shapes всё ещё
   увеличивает когнитивную нагрузку на normalization module и schema normalizers,
   хотя сам `config_loader.py` после extraction стал проще

### Neutral

1. **Legacy file-path fallback удалён**: `load_pipeline_config()` использует только
   `configs/entities/{provider}/{entity}.yaml`; transitional compatibility остаётся
   в payload normalization, alias handling и provider/source coercion
1. **21 standard pipelines** полностью переведены на unified format; composite pipelines (5) используют `configs/composites/` (ADR-026)
1. **`_deep_merge()` делегирует в `config_merge()`** — унифицировано с ADR-037

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

| Файл                                                                            | Изменение                                                                                                          |
| ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `src/bioetl/infrastructure/config_loader.py`                                    | Сохраняет read/validate/map orchestration и compatibility wrappers для test-facing private helpers                 |
| `src/bioetl/infrastructure/config/pipeline_payload_normalization.py`            | Новый normalization boundary: convention defaults, filter/source merge, schema bridge, legacy/new payload coercion |
| `tests/architecture/test_pipeline_external_schema_non_empty.py`                 | Добавлена `find_pipeline_config()`, поддержка unified формата                                                      |
| `tests/unit/infrastructure/config/test_pipeline_config_legacy_normalization.py` | Закрепляет явный `read -> normalize -> validate -> map` pipeline и compatibility surface                           |
| `configs/entities/{p}/{e}.yaml`                                                 | 21 unified entity configs (all standard pipelines)                                                                 |

### Deleted Directories (RF-CFG-035)

- legacy provider/entity pipeline directory (21 файлов)
- `configs/schemas/{providers}/` (21 файлов) <!-- doc-lint: allow-legacy -->
- legacy `quality/entities` directory (21 файлов)
- legacy `filters/entities` directory (21 файлов)
- `configs/contracts/` (21 файлов)

## Rollout

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
- Archive index: repository path `docs/99-archive/README.md` — historical planning and migration context *(archived)*

## Changelog

| Date       | Author      | Change                                                 |
| ---------- | ----------- | ------------------------------------------------------ |
| 2026-02-24 | Claude Code | Initial version — documenting completed implementation |

## Compliance

| Control      | Requirement                                                                | Status     | Evidence                                  |
| ------------ | -------------------------------------------------------------------------- | ---------- | ----------------------------------------- |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass`     | `ADR-039-unified-entity-config-format.md` |
| Status       | ADR status MUST be explicit and consistent                                 | `pass`     | `Accepted`                                |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `declared` | `metadata block`                          |
| Verification | Implementation and validation expectations MUST be documented              | `pass`     | `Verification / Acceptance Criteria`      |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass`     | `References`                              |

## Rollback

- Rollback MUST identify the last known-good behavior or artifact set.
- If the decision changes contracts, configuration, or storage semantics, rollback SHOULD include data and compatibility checks.
- Rollback triggers SHOULD be observable through tests, runtime signals, or regression symptoms.

## Verification

- Verify architecture, configuration, and documentation changes against the current codebase.
- Run the relevant tests, validators, or parity checks before considering the ADR fully adopted.
- Confirm downstream docs and contracts reflect the same decision boundaries.

## Acceptance Criteria

- [ ] The decision is documented with current status, date, and owner metadata.
- [ ] The implementation path or adoption boundary is testable and linked from the ADR.
- [ ] Supersession or migration impact is documented when the decision changes an earlier posture.
- [ ] Related docs, contracts, and operational guidance are aligned with this ADR.
