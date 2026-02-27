# ADR-023: Паттерны передачи entity-type в трансформерах

**Status:** Accepted
**Date:** 2026-01-06
**Decision makers:** @BioETL-Team
**Relates to:** ADR-006 (Logger and Metrics Ports), ADR-017 (Observability Architecture)

## Context

При анализе интерфейсов трансформеров выявлено 3 паттерна передачи `entity-type`:

### Исходная Проблема

`BaseTransformer.__init__()` принимает опциональный параметр `entity-type`:

```python
def __init__(
    self,
    provider: str,
    entity-type: str | None = None,  # Default: "unknown"
    ...
) -> None:
    self.entity-type = entity-type or "unknown"
```

Параметр `entity-type` используется для:
- **Metrics labels**: `transform-duration-seconds{entity-type="..."}`, `transform-errors-total{entity-type="..."}`
- **Tracing attributes**: `bioetl.entity-type` в span
- **Entity ID generation**: `compute-entity-id()` формирует `{provider}:{entity-type}:{source-id}`

### Выявленные Паттерны

| Паттерн | Описание | Количество | Итоговый entity-type |
|---------|----------|------------|----------------------|
| **A** | ChEMBL через `BaseChemblTransformer` (не передаёт entity-type) | 12 | `"unknown"` |
| **B** | Явная передача entity-type в `super().__init__()` | 6 | Корректный |
| **C** | Нет entity-type, нет entity-class (PubMed) | 1 | `"unknown"` |

**Проблема**: 13 из 19 трансформеров имели `entity-type = "unknown"`, что приводило к потере ценной информации в метриках и трейсинге.

### Паттерн A: ChEMBL (BaseChemblTransformer)

```python
class BaseChemblTransformer(BaseTransformer):
    entity-class: ClassVar[type[BaseEntity]]  # ✅ Определён

    def __init__(self, provider: str = "chembl", ...):
        super().__init__(
            provider,
            # entity-type НЕ передаётся! → "unknown"
            tracer=tracer,
            ...
        )
```

Все 12 ChEMBL трансформеров наследуют `BaseChemblTransformer` и получают `entity-type = "unknown"`.

### Паттерн B: Явная передача

```python
class CrossRefPublicationTransformer(BaseTransformer):
    def __init__(self, provider: str = "crossref", ...):
        super().__init__(
            provider,
            entity-type="publication",  # ✅ Явно передано
            ...
        )
```

### Паттерн C: PubMed

```python
class PubMedPublicationTransformer(BaseTransformer):
    def __init__(self, provider: str = "pubmed", ...):
        super().__init__(
            provider,
            # entity-type НЕ передаётся → "unknown"
            ...
        )
```

## The Decision

### 1. Auto-derive entity-type в BaseChemblTransformer

`BaseChemblTransformer` автоматически выводит `entity-type` из `entity-class.--name--.lower()`:

```python
class BaseChemblTransformer(BaseTransformer):
    entity-class: ClassVar[type[BaseEntity]]

    def __init__(self, provider: str = "chembl", ...):
        # Auto-derive entity-type from entity-class ClassVar
        entity-type = self.entity-class.--name--.lower()

        super().__init__(
            provider,
            entity-type=entity-type,  # ✅ Автоматически
            ...
        )
```

### 2. Явная передача для non-ChEMBL трансформеров

Трансформеры, не использующие `entity-class` ClassVar, должны явно передавать `entity-type`:

```python
class PubMedPublicationTransformer(BaseTransformer):
    def __init__(self, provider: str = "pubmed", ...):
        super().__init__(
            provider,
            entity-type="publication",  # ✅ Явно
            ...
        )
```

## Justification

### 1. Backward Compatibility

Auto-derive подход не требует изменений в существующих ChEMBL трансформерах:

```python
# До: entity-type = "unknown"
class ActivityTransformer(BaseChemblTransformer):
    entity-class = Bioactivity
    ...

# После: entity-type = "bioactivity" (автоматически)
# Код трансформера не изменился
```

### 2. Консистентность с DRY

`entity-class` уже определён как ClassVar в каждом ChEMBL трансформере. Дублирование `entity-type` нарушало бы DRY:

```python
# ❌ DRY violation
class ActivityTransformer(BaseChemblTransformer):
    entity-class = Bioactivity
    entity-type = "bioactivity"  # Дублирование!
```

### 3. Observability (O1 Requirements)

Осмысленные метки `entity-type` критичны для observability:

```promql
# До: все ChEMBL трансформеры неразличимы
transform-duration-seconds{provider="chembl", entity-type="unknown"}

# После: гранулярные метрики
transform-duration-seconds{provider="chembl", entity-type="bioactivity"}
transform-duration-seconds{provider="chembl", entity-type="assay"}
transform-duration-seconds{provider="chembl", entity-type="molecule"}
```

### 4. Tracing Attributes

Span атрибуты становятся информативными:

```json
{
  "name": "transform-record",
  "attributes": {
    "bioetl.provider": "chembl",
    "bioetl.entity-type": "bioactivity"  // ← Вместо "unknown"
  }
}
```

## Implementation

### Изменённые Файлы

| Файл | Изменение |
|------|-----------|
| `application/pipelines/chembl/base-chembl-transformer.py` | Auto-derive `entity-type` из `entity-class` |
| `application/pipelines/pubmed/transformer.py` | Явная передача `entity-type="publication"` |

### Результирующие entity-type

| Трансформер | entity-class | entity-type |
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

### 1. Explicit entity-type in each transformer

```python
class ActivityTransformer(BaseChemblTransformer):
    entity-class = Bioactivity
    entity-type = "activity"  # Explicit
```

**Rejected** because:
- Requires changes to all 12 ChEMBL transformers
- Duplicates information (entity-class already provides this)
- Prone to inconsistencies (typos, naming variations)

### 2. Mapping dictionary

```python
-ENTITY-TYPE-MAP = {
    "Bioactivity": "activity",
    "ProteinClassification": "protein-class",
    ...
}
```

**Rejected** because:
- Additional maintenance burden
- Must be updated when new entities added
- Simple `.lower()` is sufficient for now

### 3. entity-type parameter with default

```python
class BaseChemblTransformer(BaseTransformer):
    def __init__(self, entity-type: str | None = None, ...):
        derived = entity-type or self.entity-class.--name--.lower()
        super().__init__(entity-type=derived, ...)
```

**Rejected** because:
- Over-engineering for no clear benefit
- Nobody needs to override entity-type for ChEMBL transformers

## Consequences

### Positive

- **(+) Meaningful metrics labels**: All transformers now have informative `entity-type`
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

- **Audit Report**: `docs/audits/entity-type-audit.md` — detailed analysis of all 19 transformers
