______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-024: Entity Naming Unification

**Date:** 2026-01-06
**Status:** Accepted
**Decision makers:** @BioETL-Team

## Context

При работе с доменными сущностями из разных провайдеров выявлено несоответствие между терминологией провайдеров (API-специфичные имена) и каноническими терминами Ubiquitous Language.

### Исходная Проблема

| Provider | API-имя    | Доменное значение                   |
| -------- | ---------- | ----------------------------------- |
| ChEMBL   | `Document` | Научная публикация (статья, патент) |
| PubChem  | `Compound` | Химическая молекула                 |
| UniProt  | `Protein`  | Биологическая мишень                |

Проблемы:

1. **Семантическая путаница**: `Document` в ChEMBL — это публикация, а не документ общего назначения
1. **Несогласованность**: PubMed использует `Publication`, а ChEMBL — `Document` для того же концепта
1. **Domain ambiguity**: UniProt `Protein` — это target для bioactivity, а не просто белок

### Принципы Ubiquitous Language

Согласно glossary.md, канонические термины:

- **Publication** — научный документ (статья, патент и т.д.)
- **Molecule** — химическое соединение с определённой структурой
- **Target** — биологическая мишень для измерения активности

## Decision

Переименовать доменные сущности согласно каноническим терминам Ubiquitous Language:

| Старое имя | Новое (каноническое) | Обоснование                              |
| ---------- | -------------------- | ---------------------------------------- |
| `Document` | `ChemblPublication`  | Префикс провайдера + канонический термин |
| `Compound` | `PubchemMolecule`    | Префикс провайдера + канонический термин |
| `Protein`  | `UniprotTarget`      | Префикс провайдера + канонический термин |

### Backward Compatibility

**Update (2026-01-21):** Deprecated aliases were **planned but never implemented**.
Code analysis confirmed that the codebase was migrated directly to canonical names
without requiring backward compatibility shims. All consumers were updated atomically.

Original plan (not implemented):

```python
# These aliases were NEVER added - direct migration was cleaner
# Document = ChemblPublication  # NOT IMPLEMENTED
# Compound = PubchemMolecule    # NOT IMPLEMENTED
# Protein = UniprotTarget       # NOT IMPLEMENTED
```

**Rationale for skipping aliases:**

1. All internal consumers were updated in the same migration
1. No external API stability requirements
1. Cleaner codebase without deprecated symbols

### Pandera Schemas

Аналогичное переименование для схем валидации:

| Старое имя       | Новое (каноническое)      |
| ---------------- | ------------------------- |
| `DocumentSchema` | `ChemblPublicationSchema` |
| `CompoundSchema` | `PubchemMoleculeSchema`   |
| `ProteinSchema`  | `UniprotTargetSchema`     |
| `ArticleSchema`  | `PubMedPublicationSchema` |

**Note:** PubMed's `ArticleSchema` was renamed to `PubMedPublicationSchema` (2026-01-25)
to align with `entity_type: publication` in pipeline config and maintain consistency
with other publication schemas (`ChemblPublicationSchema`, `OpenAlexPublicationSchema`,
`SemanticScholarPublicationSchema`). A backward-compatibility alias `ArticleSchema`
is provided but deprecated.

## Consequences

### Positive

1. **Ubiquitous Language alignment**: Код соответствует глоссарию терминов
1. **Self-documenting**: `ChemblPublication` явно указывает на источник и семантику
1. **Disambiguation**: Устранена путаница между `Document` (ChEMBL) и документами общего назначения
1. **Consistency**: Все провайдерские сущности следуют паттерну `{Provider}{CanonicalTerm}`

### Negative

1. **Migration overhead**: Существующий код использовал старые имена (все обновлено атомарно в одном коммите, aliases не потребовались)
1. **Documentation updates**: Необходимо обновить документацию (выполнено)

### Neutral

- Error messages используют канонические имена (`PubchemMolecule cid is required`)
- Тесты обновлены для новых error messages

## Implementation

### Phase 1: Domain Entities (v2.0)

**Domain Entities:**

- `src/bioetl/domain/entities/chembl_structures.py` — `Document` → `ChemblPublication`
- `src/bioetl/domain/entities/pubchem.py` — `Compound` → `PubchemMolecule`
- `src/bioetl/domain/entities/uniprot.py` — `Protein` → `UniprotTarget`
- `src/bioetl/domain/entities/__init__.py` — exports обновлены

**Pandera Schemas:**

- `src/bioetl/domain/schemas/chembl/document.py` — `DocumentSchema` → `ChemblPublicationSchema`
- `src/bioetl/domain/schemas/pubchem/compound.py` — `CompoundSchema` → `PubchemMoleculeSchema`
- `src/bioetl/domain/schemas/uniprot/protein.py` — `ProteinSchema` → `UniprotTargetSchema`

### Phase 2: Pipeline and Transformer Renames (v2.0)

**Pipeline Configs (renamed files):**

- `configs/entities/chembl/document.yaml` → `publication.yaml`
- `configs/entities/chembl/document-similarity.yaml` → `publication_similarity.yaml`
- `configs/entities/chembl/document-term.yaml` → `publication_term.yaml`
- Pipeline names changed: `chembl-document` → `chembl_publication`, etc.

**Pipeline Classes (renamed files):**

- `document.py` → `publication.py` — `ChEMBLDocumentPipeline` → `ChEMBLPublicationPipeline`
- `document_similarity.py` → `publication_similarity.py` — `ChEMBLDocumentSimilarityPipeline` → `ChEMBLPublicationSimilarityPipeline`
- `document_term.py` → `publication_term.py` — `ChEMBLDocumentTermPipeline` → `ChEMBLPublicationTermPipeline`

**Transformer Classes (renamed files):**

- `document_transformer.py` → `publication_transformer.py` — `DocumentTransformer` → `PublicationTransformer`
- `document_similarity_transformer.py` → `publication_similarity_transformer.py` — `DocumentSimilarityTransformer` → `PublicationSimilarityTransformer`
- `document_term_transformer.py` → `publication_term_transformer.py` — `DocumentTermTransformer` → `PublicationTermTransformer`

**Data Source (renamed file):**

- `document_term_data_source.py` → `publication_term_data_source.py` — `DocumentTermDataSource` → `PublicationTermDataSource`

**Schema Files (renamed):**

- `src/bioetl/domain/schemas/chembl/document.py` → `publication.py`
- `src/bioetl/domain/schemas/chembl/document_similarity.py` → `publication_similarity.py`
- `src/bioetl/domain/schemas/chembl/document_term.py` → `publication_term.py`
- `src/bioetl/domain/schemas/pubmed/article.py` → `publication.py` — `ArticleSchema` → `PubMedPublicationSchema` (2026-01-25)

**Factory Updates:**

- `transformer_factory.py` — imports and registrations updated
- `pipeline/registry.py` — imports, configs, and exports updated
- `registration.py` — import updated

**Test Files (renamed):**

- `test_document_term_data_source.py` → `test_publication_term_data_source.py`
- `test_document_similarity_transformer.py` → `test_publication_similarity_transformer.py`
- `test_chembl_document_e2e.py` → `test_chembl_publication_e2e.py`
- `test_chembl_document_term_e2e.py` → `test_chembl_publication_term_e2e.py`

**Documentation:**

- `docs/glossary.md` — Migration notes добавлены
- `configs/naming-exceptions.yaml` — Canonical + deprecated names

**Tests:**

- `tests/unit/domain/test_entities.py` — Error messages обновлены
- All test files updated to use new class names

### Migration Guide

**Note:** Since aliases were never implemented for domain entities, old imports will raise `ImportError`.
All code must use canonical names directly.

**Exception:** `ArticleSchema` is provided as a deprecated alias for `PubMedPublicationSchema`
for backward compatibility. Prefer `PubMedPublicationSchema` in new code.

**Domain Entities:**

```python
# Old names (NOT available - will raise ImportError)
# from bioetl.domain.entities import Document, Compound, Protein  # ERROR!

# Canonical names (ONLY option)
from bioetl.domain.entities import ChemblPublication, PubchemMolecule, UniprotTarget
```

**Pipelines and Transformers:**

```python
# Old files/classes no longer exist
# from bioetl.application.pipelines.chembl.document-transformer import DocumentTransformer  # ERROR!

# Canonical names (ONLY option)
from bioetl.application.pipelines.chembl.publication-transformer import (
    PublicationTransformer,
)
from bioetl.application.pipelines.chembl.publication import ChEMBLPublicationPipeline
```

**Pipeline Names (CLI):**

```bash
# Old names no longer work
# bioetl run --pipeline chembl-document  # ERROR: Unknown pipeline

# Canonical names (ONLY option)
bioetl run --pipeline chembl_publication
```

### Publication field alias compatibility window (update: 2026-02-18)

For publication pipeline read-path compatibility, legacy field names are still
accepted via explicit alias mapping, but canonical names are the public Gold/API
contract.

Legacy aliases accepted until **2026-06-30**:

| Legacy field         | Canonical field      | Source                                    |
| -------------------- | -------------------- | ----------------------------------------- |
| `pubmed-id`          | `publication-pmid`   | `FieldSpec(target=...)`                   |
| `doi`                | `publication-doi`    | `FieldSpec(target=...)` + `field-aliases` |
| `doc-type`           | `publication-type`   | `FieldSpec(target=...)` + `field-aliases` |
| `first-page`         | `page-first`         | `FieldSpec(target=...)` + `field-aliases` |
| `last-page`          | `page-last`          | `FieldSpec(target=...)` + `field-aliases` |
| `year`               | `publication-year`   | `FieldSpec(target=...)` + `field-aliases` |
| `document-chembl-id` | `publication-id`     | `field-aliases`                           |
| `pmid`               | `publication-pmid`   | `field-aliases`                           |
| `pmc-id`             | `publication-pmc-id` | `field-aliases`                           |

After 2026-06-30, legacy aliases must be removed from read-path shims and
consumers should use canonical fields only.

### Deprecation Timeline

- **v2.0**: Canonical names introduced with direct migration (no aliases needed)
- **2026-02-18**: Read-path compatibility shim added for publication field aliases
- **2026-06-30**: Cutoff date for publication legacy alias removal
- ~~**v3.0 (planned)**: Deprecated aliases may be removed~~ — superseded by dated cutoff above

## Phase 3: Centralized Publication Mapping Registry (v2.1)

**Date:** 2026-01-26

### Problem

Publication entity mappings (`publication*` → `document*` for ChEMBL API) were scattered across:

1. YAML pipeline configs (`entity_type: publication`)
1. `ChemblEntityMapper` hardcoded dictionaries
1. Implicit comments and ADR documentation

This distributed knowledge created risk of desynchronization when adding new publication variants.

### Solution

Introduced a centralized **Publication Mapping Registry** in domain layer:

**New Files:**

- `src/bioetl/domain/registry/__init__.py` — Registry exports
- `src/bioetl/domain/registry/publication.py` — Single source of truth for publication mappings

**Registry Structure:**

```python
@dataclass(frozen=True, slots=True)
class PublicationMapping:
    canonical-name: str  # Domain entity type (publication*)
    api-resource: str  # ChEMBL API resource (document*)
    plural-key: str  # Response array key (documents)
    primary-key-field: str  # PK for deduplication
    is-legacy-alias: bool  # True for backward-compat aliases
```

**Key Functions:**

- `get-publication-mapping(entity_type)` — Get mapping for entity type
- `is-publication-entity(entity_type)` — Check if publication-related
- `is-legacy-publication-alias(entity_type)` — Check if legacy alias
- `validate-publication-entity_type(entity_type, provider)` — Config validation

### Updated Components

**`ChemblEntityMapper`** now imports from registry:

```python
from bioetl.domain.registry.publication import (
    get-publication-mapping,
    is-publication-entity,
)

class ChemblEntityMapper:
    @staticmethod
    def get-resource-url(entity_type: str) -> str:
        # Check publication registry first (ADR-024)
        pub-mapping = get-publication-mapping(entity_type)
        if pub-mapping is not None:
            return f"{CHEMBL-API-BASE}/{pub-mapping.api-resource}"
        # ... non-publication entities
```

**`PipelineYamlConfig`** now validates entity_type:

- Raises `ValueError` if `document*` used in ChEMBL YAML configs
- Enforces canonical names (`publication*`) at config load time

### Benefits

1. **Single source of truth** — All publication mappings in one place
1. **Explicit validation** — Config loading fails fast on legacy names
1. **Type safety** — `PublicationMapping` dataclass is immutable and typed
1. **Extensibility** — Add new publication variants in registry, not scattered across codebase

## References

- [glossary.md](../../00-project/glossary.md) — Ubiquitous Language definitions
- [RULES.md §8.2](../../00-project/RULES.md) — Domain Layer guidelines
- [ADR-021](ADR-021-ddd-aggregates-adoption.md) — DDD Aggregates

## Compliance

| Control      | Requirement                                                                | Status | Evidence                               |
| ------------ | -------------------------------------------------------------------------- | ------ | -------------------------------------- |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-024-entity-naming-unification.md` |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted`                             |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                       |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria`   |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                           |

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
