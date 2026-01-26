# ADR-024: Entity Naming Unification

**Status:** Accepted
**Date:** 2026-01-06
**Decision makers:** @BioETL-Team
**Relates to:** glossary.md (Ubiquitous Language), RULES.md §8.2 (Domain Layer)

## Context

При работе с доменными сущностями из разных провайдеров выявлено несоответствие между терминологией провайдеров (API-специфичные имена) и каноническими терминами Ubiquitous Language.

### Исходная Проблема

| Provider | API-имя | Доменное значение |
|----------|---------|-------------------|
| ChEMBL | `Document` | Научная публикация (статья, патент) |
| PubChem | `Compound` | Химическая молекула |
| UniProt | `Protein` | Биологическая мишень |

Проблемы:
1. **Семантическая путаница**: `Document` в ChEMBL — это публикация, а не документ общего назначения
2. **Несогласованность**: PubMed использует `Publication`, а ChEMBL — `Document` для того же концепта
3. **Domain ambiguity**: UniProt `Protein` — это target для bioactivity, а не просто белок

### Принципы Ubiquitous Language

Согласно glossary.md, канонические термины:
- **Publication** — научный документ (статья, патент и т.д.)
- **Molecule** — химическое соединение с определённой структурой
- **Target** — биологическая мишень для измерения активности

## Decision

Переименовать доменные сущности согласно каноническим терминам Ubiquitous Language:

| Старое имя | Новое (каноническое) | Обоснование |
|------------|---------------------|-------------|
| `Document` | `ChemblPublication` | Префикс провайдера + канонический термин |
| `Compound` | `PubchemMolecule` | Префикс провайдера + канонический термин |
| `Protein` | `UniprotTarget` | Префикс провайдера + канонический термин |

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
2. No external API stability requirements
3. Cleaner codebase without deprecated symbols

### Pandera Schemas

Аналогичное переименование для схем валидации:

| Старое имя | Новое (каноническое) |
|------------|---------------------|
| `DocumentSchema` | `ChemblPublicationSchema` |
| `CompoundSchema` | `PubchemMoleculeSchema` |
| `ProteinSchema` | `UniprotTargetSchema` |
| `ArticleSchema` | `PubMedPublicationSchema` |

**Note:** PubMed's `ArticleSchema` was renamed to `PubMedPublicationSchema` (2026-01-25)
to align with `entity_type: publication` in pipeline config and maintain consistency
with other publication schemas (`ChemblPublicationSchema`, `OpenAlexPublicationSchema`,
`SemanticScholarPublicationSchema`). A backward-compatibility alias `ArticleSchema`
is provided but deprecated.

## Consequences

### Positive

1. **Ubiquitous Language alignment**: Код соответствует глоссарию терминов
2. **Self-documenting**: `ChemblPublication` явно указывает на источник и семантику
3. **Disambiguation**: Устранена путаница между `Document` (ChEMBL) и документами общего назначения
4. **Consistency**: Все провайдерские сущности следуют паттерну `{Provider}{CanonicalTerm}`

### Negative

1. **Migration overhead**: Существующий код использовал старые имена (все обновлено атомарно в одном коммите, aliases не потребовались)
2. **Documentation updates**: Необходимо обновить документацию (выполнено)

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
- `configs/pipelines/chembl/document.yaml` → `publication.yaml`
- `configs/pipelines/chembl/document_similarity.yaml` → `publication_similarity.yaml`
- `configs/pipelines/chembl/document_term.yaml` → `publication_term.yaml`
- Pipeline names changed: `chembl_document` → `chembl_publication`, etc.

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
- `pipeline_factories.py` — imports, configs, and exports updated
- `registration.py` — import updated

**Test Files (renamed):**
- `test_document_term_data_source.py` → `test_publication_term_data_source.py`
- `test_document_similarity_transformer.py` → `test_publication_similarity_transformer.py`
- `test_chembl_document_e2e.py` → `test_chembl_publication_e2e.py`
- `test_chembl_document_term_e2e.py` → `test_chembl_publication_term_e2e.py`

**Documentation:**
- `docs/glossary.md` — Migration notes добавлены
- `configs/naming_exceptions.yaml` — Canonical + deprecated names

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
# from bioetl.application.pipelines.chembl.document_transformer import DocumentTransformer  # ERROR!

# Canonical names (ONLY option)
from bioetl.application.pipelines.chembl.publication_transformer import PublicationTransformer
from bioetl.application.pipelines.chembl.publication import ChEMBLPublicationPipeline
```

**Pipeline Names (CLI):**
```bash
# Old names no longer work
# bioetl run chembl_document  # ERROR: Unknown pipeline

# Canonical names (ONLY option)
bioetl run chembl_publication
```

### Deprecation Timeline

- **v2.0**: Canonical names introduced with direct migration (no aliases needed)
- ~~**v3.0 (planned)**: Deprecated aliases may be removed~~ — Not applicable, aliases were never added

## Phase 3: Centralized Publication Mapping Registry (v2.1)

**Date:** 2026-01-26

### Problem

Publication entity mappings (`publication*` → `document*` for ChEMBL API) were scattered across:
1. YAML pipeline configs (`entity_type: publication`)
2. `ChemblEntityMapper` hardcoded dictionaries
3. Implicit comments and ADR documentation

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
    canonical_name: str      # Domain entity type (publication*)
    api_resource: str        # ChEMBL API resource (document*)
    plural_key: str          # Response array key (documents)
    primary_key_field: str   # PK for deduplication
    is_legacy_alias: bool    # True for backward-compat aliases
```

**Key Functions:**
- `get_publication_mapping(entity_type)` — Get mapping for entity type
- `is_publication_entity(entity_type)` — Check if publication-related
- `is_legacy_publication_alias(entity_type)` — Check if legacy alias
- `validate_publication_entity_type(entity_type, provider)` — Config validation

### Updated Components

**`ChemblEntityMapper`** now imports from registry:
```python
from bioetl.domain.registry.publication import (
    get_publication_mapping,
    is_publication_entity,
)

class ChemblEntityMapper:
    @staticmethod
    def get_resource_url(entity_type: str) -> str:
        # Check publication registry first (ADR-024)
        pub_mapping = get_publication_mapping(entity_type)
        if pub_mapping is not None:
            return f"{CHEMBL_API_BASE}/{pub_mapping.api_resource}"
        # ... non-publication entities
```

**`PipelineYamlConfig`** now validates entity_type:
- Raises `ValueError` if `document*` used in ChEMBL YAML configs
- Enforces canonical names (`publication*`) at config load time

### Benefits

1. **Single source of truth** — All publication mappings in one place
2. **Explicit validation** — Config loading fails fast on legacy names
3. **Type safety** — `PublicationMapping` dataclass is immutable and typed
4. **Extensibility** — Add new publication variants in registry, not scattered across codebase

## References

- [glossary.md](../../glossary.md) — Ubiquitous Language definitions
- [RULES.md §8.2](../../RULES.md) — Domain Layer guidelines
- [ADR-021](ADR-021-ddd-aggregates-adoption.md) — DDD Aggregates
