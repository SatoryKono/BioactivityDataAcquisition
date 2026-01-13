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

Deprecated aliases сохранены для обратной совместимости:

```python
# chembl_structures.py
Document = ChemblPublication  # Deprecated alias

# pubchem.py
Compound = PubchemMolecule  # Deprecated alias

# uniprot.py
Protein = UniprotTarget  # Deprecated alias
```

Aliases работают идентично оригинальным классам (type aliases).

### Pandera Schemas

Аналогичное переименование для схем валидации:

| Старое имя | Новое (каноническое) |
|------------|---------------------|
| `DocumentSchema` | `ChemblPublicationSchema` |
| `CompoundSchema` | `PubchemMoleculeSchema` |
| `ProteinSchema` | `UniprotTargetSchema` |

## Consequences

### Positive

1. **Ubiquitous Language alignment**: Код соответствует глоссарию терминов
2. **Self-documenting**: `ChemblPublication` явно указывает на источник и семантику
3. **Disambiguation**: Устранена путаница между `Document` (ChEMBL) и документами общего назначения
4. **Consistency**: Все провайдерские сущности следуют паттерну `{Provider}{CanonicalTerm}`

### Negative

1. **Migration overhead**: Существующий код использует старые имена (митигируется aliases)
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

**Domain Entities:**
```python
# Before (deprecated)
from bioetl.domain.entities import Document, Compound, Protein

# After (canonical)
from bioetl.domain.entities import ChemblPublication, PubchemMolecule, UniprotTarget
```

**Pipelines and Transformers:**
```python
# Before (deprecated)
from bioetl.application.pipelines.chembl.document_transformer import DocumentTransformer
from bioetl.application.pipelines.chembl.document import ChEMBLDocumentPipeline

# After (canonical)
from bioetl.application.pipelines.chembl.publication_transformer import PublicationTransformer
from bioetl.application.pipelines.chembl.publication import ChEMBLPublicationPipeline

# Via package __init__.py (both work, new names preferred)
from bioetl.application.pipelines.chembl import (
    PublicationTransformer,    # Canonical
    DocumentTransformer,       # Deprecated alias
)
```

**Pipeline Names (CLI):**
```bash
# Before (deprecated)
bioetl run chembl_document

# After (canonical)
bioetl run chembl_publication
```

### Deprecation Timeline

- **v2.0**: Canonical names introduced, deprecated aliases available
- **v3.0 (planned)**: Deprecated aliases may be removed with deprecation warnings

## References

- [glossary.md](../../../glossary.md) — Ubiquitous Language definitions
- [RULES.md §8.2](../../../RULES.md) — Domain Layer guidelines
- [ADR-021](ADR-021-ddd-aggregates-adoption.md) — DDD Aggregates
