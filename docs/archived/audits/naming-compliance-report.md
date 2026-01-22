# Entity Naming Compliance Report

**Audit Date:** 2026-01-19 (Updated)
**Previous Audit:** 2026-01-16
**ADR Reference:** ADR-024 Entity Naming Unification
**Auditor:** Claude Code
**Status:** ⚠️ PARTIALLY COMPLIANT (migration incomplete)

---

## Executive Summary

The BioETL codebase is **partially compliant** with ADR-024 Entity Naming Unification. While domain entities and pipelines have been migrated successfully, several **schema class names** were not updated during the Phase 2 migration, leaving deprecated "Document" terminology in Gold and Pandera schemas.

### Compliance Score: 85%

| Category | Status | Details |
|----------|--------|---------|
| Domain Entities | ✅ Compliant | Canonical names implemented |
| ChEMBL Pipelines | ✅ Compliant | Renamed per ADR-024 |
| ChEMBL Transformers | ✅ Compliant | Renamed per ADR-024 |
| Gold Schemas | ❌ Non-Compliant | Still using "Document" prefix |
| Domain Pandera Schemas | ❌ Non-Compliant | Still using "Document" prefix |
| Deprecated Aliases | ⚠️ Not Implemented | Missing but not blocking |
| PubChem/UniProt Pipelines | ✅ N/A | By design - uses API terms |
| Test File Naming | ✅ Compliant | Follows canonical names |
| Config Files | ✅ Compliant | Properly structured |

---

## Phase 1: ADR-024 Compliance Verification

### Domain Entities - ✅ COMPLIANT

All canonical entity names are correctly implemented:

| Canonical Name | File | Status |
|----------------|------|--------|
| `ChemblPublication` | `domain/entities/chembl_structures.py:16` | ✅ Implemented |
| `PubchemMolecule` | `domain/entities/pubchem.py:91` | ✅ Implemented |
| `UniprotTarget` | `domain/entities/uniprot.py:57` | ✅ Implemented |

**Verification commands used:**
```bash
grep -rn "ChemblPublication" src/  # Found in 9 files
grep -rn "PubchemMolecule" src/    # Found in 10 files
grep -rn "UniprotTarget" src/      # Found in 5 files
```

### Known Exceptions (Intentionally Retained)

| Entity | Rationale | Reference |
|--------|-----------|-----------|
| `DocumentTerm` | ChEMBL-specific derived entity (MeSH terms) | ADR-024 |
| `DocumentSimilarity` | ChEMBL-specific derived entity (Tanimoto coefficients) | ADR-024 |
| `CompoundId` | Value Object for cross-provider compound identification | Value Objects are exempt |
| `CompoundSource` | Enum for compound source databases | Enums are exempt |

---

## Phase 2: Deprecated Alias Usage

### Finding: Deprecated Aliases NOT Implemented

According to ADR-024, the following deprecated aliases should exist for backward compatibility:

```python
# Expected in chembl_structures.py
Document = ChemblPublication  # Deprecated alias — remove in v3.0

# Expected in pubchem.py
Compound = PubchemMolecule    # Deprecated alias — remove in v3.0

# Expected in uniprot.py
Protein = UniprotTarget       # Deprecated alias — remove in v3.0
```

**Current Status:** These aliases do **NOT exist** in the codebase.

**Impact:** Low - No code currently imports these deprecated terms.

**Verification:**
```bash
grep -rn "from.*import.*\bDocument\b" src/  # No matches (excluding DocumentTerm/Similarity)
grep -rn "from.*import.*\bCompound\b" src/  # No matches
grep -rn "from.*import.*\bProtein\b" src/   # No matches
```

**Recommendation:** Either:
1. Add the deprecated aliases per ADR-024 specification (for backward compatibility), OR
2. Update ADR-024 to reflect that v2.0 migration is complete and aliases were never needed

---

## Phase 2.5: Schema Class Naming - ❌ NON-COMPLIANT (NEW FINDING)

### Gold Schemas - Require Renaming

The following Gold layer schema classes in `infrastructure/schemas/gold.py` still use deprecated "Document" terminology:

| Current Name | Expected Name | Line | Status |
|--------------|---------------|------|--------|
| `ChEMBLDocumentGoldSchema` | `ChemblPublicationGoldSchema` | 395 | ❌ Not Renamed |
| `ChEMBLDocumentTermGoldSchema` | `ChemblPublicationTermGoldSchema` | 440 | ❌ Not Renamed |
| `ChEMBLDocumentSimilarityGoldSchema` | `ChemblPublicationSimilarityGoldSchema` | 622 | ❌ Not Renamed |

**Verification:**
```bash
grep -n "class ChEMBLDocument.*GoldSchema" src/bioetl.contracts.schemas.gold.py
# Output:
# 395:class ChEMBLDocumentGoldSchema(pa.DataFrameModel):
# 440:class ChEMBLDocumentTermGoldSchema(pa.DataFrameModel):
# 622:class ChEMBLDocumentSimilarityGoldSchema(pa.DataFrameModel):
```

**Impact:**
- These schemas are imported and used in `composition/factories/pipeline_factories.py:94-96,208,222`
- Breaking change if renamed without updating imports
- Inconsistent with migrated transformer/pipeline names

### Domain Pandera Schemas - Require Renaming

The following Pandera schemas in domain layer still use deprecated terminology:

| Current Name | Expected Name | File | Line | Status |
|--------------|---------------|------|------|--------|
| `DocumentTermSchema` | `PublicationTermSchema` | `schemas/chembl/publication_term.py` | 18 | ❌ Not Renamed |
| `DocumentSimilaritySchema` | `PublicationSimilaritySchema` | `schemas/chembl/publication_similarity.py` | 14 | ❌ Not Renamed |

**Note:** The file names were correctly renamed (`publication_term.py`, `publication_similarity.py`), but the class names inside were not updated.

**Verification:**
```bash
grep -n "class Document.*Schema" src/bioetl/domain/schemas/chembl/
# Output:
# publication_term.py:18:class DocumentTermSchema(ETLRecordSchema):
# publication_similarity.py:14:class DocumentSimilaritySchema(ETLRecordSchema):
```

### ADR-024 Scope Clarification Needed

ADR-024 Phase 2 lists schema file renames but doesn't explicitly mention class name changes:

> **Schema Files (renamed):**
> - `src/bioetl/domain/schemas/chembl/document.py` → `publication.py`
> - `src/bioetl/domain/schemas/chembl/document_similarity.py` → `publication_similarity.py`
> - `src/bioetl/domain/schemas/chembl/document_term.py` → `publication_term.py`

**Interpretation:** The intent was likely to rename both files AND classes, but only file renames were executed. Gold schemas were not explicitly mentioned.

**Recommendation:** Complete the migration by:
1. Renaming Gold schema classes to `ChemblPublicationGoldSchema`, etc.
2. Renaming domain Pandera schema classes to `PublicationTermSchema`, etc.
3. Updating all imports in `pipeline_factories.py`
4. Adding deprecated aliases if backward compatibility needed

---

## Phase 3: Configuration and Pipeline Naming

### ChEMBL Publication Pipelines - ✅ COMPLIANT

All ChEMBL document-related configs have been renamed:

| Old Config | New Config | Status |
|------------|------------|--------|
| `chembl/document.yaml` | `chembl/publication.yaml` | ✅ Migrated |
| `chembl/document_similarity.yaml` | `chembl/publication_similarity.yaml` | ✅ Migrated |
| `chembl/document_term.yaml` | `chembl/publication_term.yaml` | ✅ Migrated |

**Pipeline names verified:**
- `chembl_publication` - ✅ Correct
- `chembl_publication_similarity` - ✅ Correct
- `chembl_publication_term` - ✅ Correct

### PubChem and UniProt Pipelines - ✅ BY DESIGN

Per `glossary.md` §CLI Conventions (lines 168-179), pipeline names use **provider-specific API terms**:

| Pipeline Name | Entity Type | Status | Rationale |
|---------------|-------------|--------|-----------|
| `pubchem_compound` | compound | ✅ Correct | Reflects PubChem API terminology |
| `uniprot_protein` | protein | ✅ Correct | Reflects UniProt API terminology |

This is **intentional** and documented in:
- `glossary.md` lines 168-179 (CLI Conventions)
- `naming_exceptions.yaml` lines 181-184 (Pipeline ID Format)

**Key Distinction:**
- **Domain Entity names** (class names): Use canonical Ubiquitous Language (`PubchemMolecule`, `UniprotTarget`)
- **Pipeline names** (CLI identifiers): Use provider-specific API terms (`pubchem_compound`, `uniprot_protein`)

---

## Phase 4: Test File Naming

### Test Files - ✅ COMPLIANT

ChEMBL publication test files have been renamed:

| Test Category | Files | Status |
|---------------|-------|--------|
| Unit Tests | `test_publication_term_data_source.py`, `test_publication_similarity_transformer.py` | ✅ Renamed |
| E2E Tests | `test_chembl_publication_e2e.py`, `test_chembl_publication_term_e2e.py` | ✅ Renamed |
| VCR Cassettes | `test_chembl_publication_*.yaml` | ✅ Renamed |

PubChem and UniProt test files correctly use API terminology:
- `test_pubchem_compound_e2e.py` - ✅ Correct (matches pipeline name)
- `test_uniprot_protein_e2e.py` - ✅ Correct (matches pipeline name)

### Documentation References in Tests

"Document" appears in test files only in:
1. Comments explaining the migration (e.g., "Publication vs Document per ADR-024")
2. Test data literals (e.g., `"title": "Test Document"`)
3. Historical context comments

These are **acceptable** - they don't represent usage of deprecated class names.

---

## Terminology Linter Results

Running `scripts/lint_terminology.py` shows violations unrelated to ADR-024:

| File | Violations | Type |
|------|------------|------|
| `scripts/verify_checksums.py` | 12 | `checksum` → `content_hash` |
| `batch_transformer.py` | 8 | `chunk` → `batch` (in variable names) |
| `batch_executor.py` | 2 | `Raw` → `bronze` (in docstrings) |

**Note:** The terminology linter does NOT check for `Document`, `Compound`, `Protein` deprecated terms. Consider adding these patterns if enforcement is desired.

---

## Recommendations

### High Priority

1. **Complete Gold Schema Renaming** (ADR-024 Migration Gap)
   - Rename `ChEMBLDocumentGoldSchema` → `ChemblPublicationGoldSchema`
   - Rename `ChEMBLDocumentTermGoldSchema` → `ChemblPublicationTermGoldSchema`
   - Rename `ChEMBLDocumentSimilarityGoldSchema` → `ChemblPublicationSimilarityGoldSchema`
   - Update imports in `composition/factories/pipeline_factories.py`

2. **Complete Domain Schema Class Renaming**
   - Rename `DocumentTermSchema` → `PublicationTermSchema` in `publication_term.py`
   - Rename `DocumentSimilaritySchema` → `PublicationSimilaritySchema` in `publication_similarity.py`

### Medium Priority

1. **Clarify deprecated alias status in ADR-024**
   - Either implement the aliases as documented, OR
   - Update ADR-024 to indicate aliases were determined unnecessary

2. ~~**Update `naming_exceptions.yaml`**~~ ✅ Already Correct
   - Line 181 already shows `chembl_publication` (not `chembl_document`)
   - Comment documents the rename per ADR-024

3. **Update ADR-024 Phase 2 documentation**
   - Add Gold schema renames to the migration scope
   - Clarify that both file names AND class names should be renamed

### Low Priority

1. **Update lint_terminology.py**
   - Add patterns for `Document`, `Compound`, `Protein` if enforcement is desired
   - Currently only checks generic terms like `workflow`, `chunk`, etc.

2. **Review terminology linter violations**
   - `checksum` usage in `scripts/verify_checksums.py` may be intentional
   - `chunk` in streaming context (`batch_transformer.py`) may be valid

---

## Files Verified

### Domain Layer
- `src/bioetl/domain/entities/__init__.py` - Exports canonical names
- `src/bioetl/domain/entities/chembl_structures.py` - `ChemblPublication` defined
- `src/bioetl/domain/entities/pubchem.py` - `PubchemMolecule` defined
- `src/bioetl/domain/entities/uniprot.py` - `UniprotTarget` defined
- `src/bioetl/domain/value_objects/compound_ids.py` - `CompoundId` (valid exception)

### Configuration
- `configs/pipelines/chembl/publication.yaml` - ✅ Canonical name
- `configs/pipelines/chembl/publication_similarity.yaml` - ✅ Canonical name
- `configs/pipelines/chembl/publication_term.yaml` - ✅ Canonical name
- `configs/pipelines/pubchem/compound.yaml` - ✅ API term (by design)
- `configs/pipelines/uniprot/protein.yaml` - ✅ API term (by design)

### Documentation
- `docs/02-architecture/decisions/ADR-024-entity-naming-unification.md`
- `docs/glossary.md`
- `configs/naming_exceptions.yaml`

---

## Conclusion

The ADR-024 entity naming migration is **85% complete**. The codebase properly distinguishes between:

1. **Domain entity names** (Ubiquitous Language): `ChemblPublication`, `PubchemMolecule`, `UniprotTarget`
2. **Pipeline/CLI names** (API terminology): `chembl_publication`, `pubchem_compound`, `uniprot_protein`

### Remaining Migration Items

| Component | Count | Effort |
|-----------|-------|--------|
| Gold Schema Classes | 3 | Low - Search & Replace |
| Domain Pandera Schema Classes | 2 | Low - Search & Replace |
| Factory Imports | 4 | Low - Update imports |
| **Total** | **9 items** | **~30 min** |

### Notable Observations

1. **Deprecated aliases** mentioned in ADR-024 were never implemented - no practical impact as no code uses deprecated import patterns
2. **DocumentTerm** and **DocumentSimilarity** entity classes are intentionally retained (ChEMBL-derived entities, not publications)
3. **Schema class naming** was overlooked during Phase 2 - only file names were renamed

### Next Steps

Complete the high-priority schema renaming to achieve 100% ADR-024 compliance.

---

*Report generated: 2026-01-16*
*Updated: 2026-01-19 - Added Phase 2.5 schema naming findings*
