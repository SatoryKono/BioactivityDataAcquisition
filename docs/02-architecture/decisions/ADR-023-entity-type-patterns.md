______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-023: Паттерны передачи entity_type в трансформерах

**Date:** 2026-01-06
**Status:** Accepted
**Decision makers:** @BioETL-Team

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

- **Metrics labels**: `transform-duration-seconds{entity_type="..."}`, `transform-errors-total{entity_type="..."}`
- **Tracing attributes**: `bioetl.entity_type` в span
- **Entity ID generation**: `compute-entity-id()` формирует `{provider}:{entity_type}:{source-id}`

### Выявленные Паттерны

| Паттерн | Описание                                                       | Количество | Итоговый entity_type |
| ------- | -------------------------------------------------------------- | ---------- | -------------------- |
| **A**   | ChEMBL через `BaseChemblTransformer` (не передаёт entity_type) | 12         | `"unknown"`          |
| **B**   | Явная передача entity_type в `super().__init__()`              | 6          | Корректный           |
| **C**   | Нет entity_type, нет entity_class (PubMed)                     | 1          | `"unknown"`          |

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

## Decision

### 1. Auto-derive entity_type в BaseChemblTransformer

`BaseChemblTransformer` автоматически выводит `entity_type` из `entity_class.--name--.lower()`:

```python
class BaseChemblTransformer(BaseTransformer):
    entity_class: ClassVar[type[BaseEntity]]

    def __init__(self, provider: str = "chembl", ...):
        # Auto-derive entity_type from entity_class ClassVar
        entity_type = self.entity_class.--name--.lower()

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
transform-duration-seconds{provider="chembl", entity_type="unknown"}

# После: гранулярные метрики
transform-duration-seconds{provider="chembl", entity_type="bioactivity"}
transform-duration-seconds{provider="chembl", entity_type="assay"}
transform-duration-seconds{provider="chembl", entity_type="molecule"}
```

### 4. Tracing Attributes

Span атрибуты становятся информативными:

```json
{
  "name": "transform-record",
  "attributes": {
    "bioetl.provider": "chembl",
    "bioetl.entity_type": "bioactivity"  // ← Вместо "unknown"
  }
}
```

## Implementation

### Изменённые Файлы

| Файл                                                      | Изменение                                   |
| --------------------------------------------------------- | ------------------------------------------- |
| `application/pipelines/chembl/base_chembl_transformer.py` | Auto-derive `entity_type` из `entity_class` |
| `application/pipelines/pubmed/transformer.py`             | Явная передача `entity_type="publication"`  |

### Результирующие entity_type

| Трансформер                      | entity_class                | entity_type                     |
| -------------------------------- | --------------------------- | ------------------------------- |
| ActivityTransformer              | Bioactivity                 | `"bioactivity"`                 |
| AssayTransformer                 | Assay                       | `"assay"`                       |
| MoleculeTransformer              | Molecule                    | `"molecule"`                    |
| TargetTransformer                | Target                      | `"target"`                      |
| PublicationTransformer           | ChemblPublication           | `"chemblpublication"`           |
| TargetComponentTransformer       | TargetComponent             | `"targetcomponent"`             |
| CellLineTransformer              | CellLine                    | `"cellline"`                    |
| CompoundRecordTransformer        | CompoundRecord              | `"compoundrecord"`              |
| ProteinClassTransformer          | ProteinClassification       | `"proteinclassification"`       |
| AssayParametersTransformer       | AssayParameters             | `"assayparameters"`             |
| PublicationSimilarityTransformer | ChemblPublicationSimilarity | `"chemblpublicationsimilarity"` |
| PublicationTermTransformer       | ChemblPublicationTerm       | `"chemblpublicationterm"`       |
| PubMedPublicationTransformer     | —                           | `"publication"`                 |

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

### 3. entity_type parameter with default

```python
class BaseChemblTransformer(BaseTransformer):
    def __init__(self, entity_type: str | None = None, ...):
        derived = entity_type or self.entity_class.--name--.lower()
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

## References

- **ADR-006**: Logger and Metrics Ports — defines MetricsPort used for observability
- **ADR-017**: Observability Architecture — establishes O1 requirements for tracing and metrics
- **ADR-020**: BasePipeline Decomposition — related transformer architecture decisions
- **ADR-022**: NoOp Tracing — TracingPort and span attributes mentioned here

## References

- **Audit Report**: `docs/audits/entity_type-audit.md` — detailed analysis of all 19 transformers

## Compliance

| Control      | Requirement                                                                | Status | Evidence                             |
| ------------ | -------------------------------------------------------------------------- | ------ | ------------------------------------ |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-023-entity-type-patterns.md`    |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted`                           |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                     |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria` |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                         |

## Rollout

- Rollout steps MUST be sequenced before broad adoption.
- Documentation, configuration, and test surfaces SHOULD be updated in the same change set when the decision is implemented.
- Breaking or migration-sensitive adoption SHOULD include an explicit transition window.

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
