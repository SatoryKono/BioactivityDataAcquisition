# ADR-023: Паттерны передачи entity_type в трансформерах

**Status:** Accepted
**Date:** 2026-01-06
**Decision makers:** @BioETL-Team
**Relates to:** ADR-006 (Logger and Metrics Ports), ADR-017 (Observability Architecture)

## Context

При анализе интерфейсов трансформеров выявлено 3 паттерна передачи `entity_type`:

### Исходная Проблема

`BaseTransformer.__init__()` принимает опциональный параметр `entity_type`:

```python
def __init__(
    self,
    provider: str,
    entity_type: str | None = None,  # Default: "unknown"
    ...
) -> None:
    self.entity_type = entity_type or "unknown"
```

Параметр `entity_type` используется для:
- **Metrics labels**: `transform_duration_seconds{entity_type="..."}`, `transform_errors_total{entity_type="..."}`
- **Tracing attributes**: `bioetl.entity_type` в span
- **Entity ID generation**: `compute_entity_id()` формирует `{provider}:{entity_type}:{source_id}`

### Выявленные Паттерны

| Паттерн | Описание | Количество | Итоговый entity_type |
|---------|----------|------------|----------------------|
| **A** | ChEMBL через `BaseChemblTransformer` (не передаёт entity_type) | 12 | `"unknown"` |
| **B** | Явная передача entity_type в `super().__init__()` | 6 | Корректный |
| **C** | Нет entity_type, нет entity_class (PubMed) | 1 | `"unknown"` |

**Проблема**: 13 из 19 трансформеров имели `entity_type = "unknown"`, что приводило к потере ценной информации в метриках и трейсинге.

### Паттерн A: ChEMBL (BaseChemblTransformer)

```python
class BaseChemblTransformer(BaseTransformer):
    entity_class: ClassVar[type[BaseEntity]]  # ✅ Определён

    def __init__(self, provider: str = "chembl", ...):
        super().__init__(
            provider,
            # entity_type НЕ передаётся! → "unknown"
            tracer=tracer,
            ...
        )
```

Все 12 ChEMBL трансформеров наследуют `BaseChemblTransformer` и получают `entity_type = "unknown"`.

### Паттерн B: Явная передача

```python
class CrossRefPublicationTransformer(BaseTransformer):
    def __init__(self, provider: str = "crossref", ...):
        super().__init__(
            provider,
            entity_type="publication",  # ✅ Явно передано
            ...
        )
```

### Паттерн C: PubMed

```python
class PubMedPublicationTransformer(BaseTransformer):
    def __init__(self, provider: str = "pubmed", ...):
        super().__init__(
            provider,
            # entity_type НЕ передаётся → "unknown"
            ...
        )
```

## The Decision

### 1. Auto-derive entity_type в BaseChemblTransformer

`BaseChemblTransformer` автоматически выводит `entity_type` из `entity_class.__name__.lower()`:

```python
class BaseChemblTransformer(BaseTransformer):
    entity_class: ClassVar[type[BaseEntity]]

    def __init__(self, provider: str = "chembl", ...):
        # Auto-derive entity_type from entity_class ClassVar
        entity_type = self.entity_class.__name__.lower()

        super().__init__(
            provider,
            entity_type=entity_type,  # ✅ Автоматически
            ...
        )
```

### 2. Явная передача для non-ChEMBL трансформеров

Трансформеры, не использующие `entity_class` ClassVar, должны явно передавать `entity_type`:

```python
class PubMedPublicationTransformer(BaseTransformer):
    def __init__(self, provider: str = "pubmed", ...):
        super().__init__(
            provider,
            entity_type="publication",  # ✅ Явно
            ...
        )
```

## Justification

### 1. Backward Compatibility

Auto-derive подход не требует изменений в существующих ChEMBL трансформерах:

```python
# До: entity_type = "unknown"
class ActivityTransformer(BaseChemblTransformer):
    entity_class = Bioactivity
    ...

# После: entity_type = "bioactivity" (автоматически)
# Код трансформера не изменился
```

### 2. Консистентность с DRY

`entity_class` уже определён как ClassVar в каждом ChEMBL трансформере. Дублирование `entity_type` нарушало бы DRY:

```python
# ❌ DRY violation
class ActivityTransformer(BaseChemblTransformer):
    entity_class = Bioactivity
    entity_type = "bioactivity"  # Дублирование!
```

### 3. Observability (O1 Requirements)

Осмысленные метки `entity_type` критичны для observability:

```promql
# До: все ChEMBL трансформеры неразличимы
transform_duration_seconds{provider="chembl", entity_type="unknown"}

# После: гранулярные метрики
transform_duration_seconds{provider="chembl", entity_type="bioactivity"}
transform_duration_seconds{provider="chembl", entity_type="assay"}
transform_duration_seconds{provider="chembl", entity_type="molecule"}
```

### 4. Tracing Attributes

Span атрибуты становятся информативными:

```json
{
  "name": "transform_record",
  "attributes": {
    "bioetl.provider": "chembl",
    "bioetl.entity_type": "bioactivity"  // ← Вместо "unknown"
  }
}
```

## Implementation

### Изменённые Файлы

| Файл | Изменение |
|------|-----------|
| `application/pipelines/chembl/base_chembl_transformer.py` | Auto-derive `entity_type` из `entity_class` |
| `application/pipelines/pubmed/transformer.py` | Явная передача `entity_type="publication"` |

### Результирующие entity_type

| Трансформер | entity_class | entity_type |
|-------------|--------------|-------------|
| ActivityTransformer | Bioactivity | `"bioactivity"` |
| AssayTransformer | Assay | `"assay"` |
| MoleculeTransformer | Molecule | `"molecule"` |
| TargetTransformer | Target | `"target"` |
| DocumentTransformer | Document | `"document"` |
| TargetComponentTransformer | TargetComponent | `"targetcomponent"` |
| CellLineTransformer | CellLine | `"cellline"` |
| CompoundRecordTransformer | CompoundRecord | `"compoundrecord"` |
| ProteinClassTransformer | ProteinClassification | `"proteinclassification"` |
| AssayParametersTransformer | AssayParameters | `"assayparameters"` |
| DocumentSimilarityTransformer | DocumentSimilarity | `"documentsimilarity"` |
| DocumentTermTransformer | DocumentTerm | `"documentterm"` |
| PubMedPublicationTransformer | — | `"publication"` |

## Alternatives Considered

### 1. Explicit entity_type in each transformer

```python
class ActivityTransformer(BaseChemblTransformer):
    entity_class = Bioactivity
    entity_type = "activity"  # Explicit
```

**Rejected** because:
- Requires changes to all 12 ChEMBL transformers
- Duplicates information (entity_class already provides this)
- Prone to inconsistencies (typos, naming variations)

### 2. Mapping dictionary

```python
_ENTITY_TYPE_MAP = {
    "Bioactivity": "activity",
    "ProteinClassification": "protein_class",
    ...
}
```

**Rejected** because:
- Additional maintenance burden
- Must be updated when new entities added
- Simple `.lower()` is sufficient for now

### 3. entity_type parameter with default

```python
class BaseChemblTransformer(BaseTransformer):
    def __init__(self, entity_type: str | None = None, ...):
        derived = entity_type or self.entity_class.__name__.lower()
        super().__init__(entity_type=derived, ...)
```

**Rejected** because:
- Over-engineering for no clear benefit
- Nobody needs to override entity_type for ChEMBL transformers

## Consequences

### Positive

- **(+) Meaningful metrics labels**: All transformers now have informative `entity_type`
- **(+) Better tracing**: Span attributes identify exact entity being transformed
- **(+) Zero code changes in transformers**: Auto-derive approach is transparent
- **(+) DRY principle**: No duplication of entity information
- **(+) Backward compatible**: Existing ChEMBL transformers work unchanged

### Negative

- **(-) Lowercase names**: `"bioactivity"` instead of `"activity"` (differs from pipeline naming)
- **(-) Long names**: `"proteinclassification"`, `"documentsimilarity"`

### Future Considerations

If more readable names needed, a mapping dictionary can be added later without breaking changes.

## Related ADRs

- **ADR-006**: Logger and Metrics Ports — defines MetricsPort used for observability
- **ADR-017**: Observability Architecture — establishes O1 requirements for tracing and metrics
- **ADR-020**: BasePipeline Decomposition — related transformer architecture decisions
- **ADR-022**: NoOp Tracing — TracingPort and span attributes mentioned here

## Related Documents

- **Audit Report**: `docs/audits/entity_type_audit.md` — detailed analysis of all 19 transformers
