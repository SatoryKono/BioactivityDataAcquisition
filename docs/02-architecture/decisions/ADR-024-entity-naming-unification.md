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

### Files Modified

**Domain Entities:**
- `src/bioetl/domain/entities/chembl_structures.py` — `Document` → `ChemblPublication`
- `src/bioetl/domain/entities/pubchem.py` — `Compound` → `PubchemMolecule`
- `src/bioetl/domain/entities/uniprot.py` — `Protein` → `UniprotTarget`
- `src/bioetl/domain/entities/__init__.py` — exports обновлены

**Pandera Schemas:**
- `src/bioetl/domain/schemas/chembl/document.py` — `DocumentSchema` → `ChemblPublicationSchema`
- `src/bioetl/domain/schemas/pubchem/compound.py` — `CompoundSchema` → `PubchemMoleculeSchema`
- `src/bioetl/domain/schemas/uniprot/protein.py` — `ProteinSchema` → `UniprotTargetSchema`

**Transformers:**
- `src/bioetl/application/pipelines/chembl/document_transformer.py` — uses `ChemblPublication`
- `src/bioetl/application/pipelines/pubchem/transformer.py` — uses `PubchemMolecule`
- `src/bioetl/application/pipelines/uniprot/transformer.py` — uses `UniprotTarget`

**Documentation:**
- `docs/glossary.md` — Migration notes добавлены
- `configs/naming_exceptions.yaml` — Canonical + deprecated names

**Tests:**
- `tests/unit/domain/test_entities.py` — Error messages обновлены

### Migration Guide

```python
# Before (deprecated)
from bioetl.domain.entities import Document, Compound, Protein

# After (canonical)
from bioetl.domain.entities import ChemblPublication, PubchemMolecule, UniprotTarget
```

### Deprecation Timeline

- **v2.0**: Canonical names introduced, deprecated aliases available
- **v3.0 (planned)**: Deprecated aliases may be removed with deprecation warnings

## References

- [glossary.md](../../../glossary.md) — Ubiquitous Language definitions
- [RULES.md §8.2](../../../RULES.md) — Domain Layer guidelines
- [ADR-021](ADR-021-ddd-aggregates-adoption.md) — DDD Aggregates
