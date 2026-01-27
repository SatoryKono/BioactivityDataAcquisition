# Publication Pipeline Field Mapping Verification Report

**Date**: 2026-01-19
**Updated**: 2026-01-26 (Finding 1 resolved)
**Scope**: All 7 Publication Pipelines
**Status**: Completed

---

## Executive Summary

Systematic verification of field mapping across all publication pipeline layers (API → Transformer → Entity → Silver → Gold) identified **8 schema inconsistencies**. Cross-provider field normalization for DOI, PMID, and PMC ID is **correctly implemented**.

**Update (2026-01-26)**: Finding 1 (`authors` field type mismatch) has been resolved. All Gold schemas now correctly use `Series[str]` for the `authors` field.

---

## Target Pipelines Verified

| # | Pipeline | Provider | Entity | Status |
|---|----------|----------|--------|--------|
| 1 | `chembl_publication` | ChEMBL | publication | ⚠️ Missing Gold fields |
| 2 | `chembl_publication_similarity` | ChEMBL | publication_similarity | ✅ Correct |
| 3 | `chembl_publication_term` | ChEMBL | publication_term | ✅ Correct |
| 4 | `pubmed_publication` | PubMed | publication | ⚠️ Missing Gold fields (Type mismatch ✅ FIXED) |
| 5 | `crossref_publication` | CrossRef | work | ⚠️ Missing Gold fields (Type mismatch ✅ FIXED) |
| 6 | `openalex_publication` | OpenAlex | publication | ✅ Correct (Type mismatch ✅ FIXED) |
| 7 | `semanticscholar_publication` | SemanticScholar | publication | ✅ Correct |

Примечание: API-ресурсы остаются `document*`, но canonical `entity_type` — `publication*` (см. ADR-024).

---

## Finding 1: TYPE_MISMATCH - `authors` Field Type Inconsistency

**Severity**: HIGH → ✅ **RESOLVED** (2026-01-26)
**Affected Pipelines**: `pubmed_publication`, `crossref_publication`, `openalex_publication`

### Issue

~~The `authors` field has inconsistent types between Silver (JSON string) and Gold (Python list) schemas for 3 providers, while 2 providers are correctly aligned.~~

**Resolution**: All Gold schemas now use `Series[str]` for the `authors` field, matching the Silver layer where transformers serialize authors to JSON strings via `serialize_json_list()`.

### Current State (Verified 2026-01-26)

| Provider | Transformer Output | Silver Schema | Gold Schema | Status |
|----------|-------------------|---------------|-------------|--------|
| PubMed | JSON string | `pa.string()` | `Series[str]` | ✅ Correct |
| CrossRef | JSON string | `pa.string()` | `Series[str]` | ✅ Correct |
| OpenAlex | JSON string | `pa.string()` | `Series[str]` | ✅ Correct |
| ChEMBL | JSON string | `pa.string()` | `Series[str]` | ✅ Correct |
| SemanticScholar | JSON string | `pa.string()` | `Series[str]` | ✅ Correct |

### File Locations (Current)

**Gold Schema (`src/bioetl/domain/contracts/gold/publications.py`)**:
- Line 64: PubMed `authors: Series[str] = pa.Field(nullable=True)  # JSON-serialized list` ✅
- Line 162: CrossRef `authors: Series[str] = pa.Field(nullable=True)  # JSON-serialized list` ✅
- Line 252: OpenAlex `authors: Series[str] = pa.Field(nullable=True)  # JSON-serialized list` ✅
- Line 353: SemanticScholar `authors: Series[str] = pa.Field(nullable=True)` ✅

**Silver Schema (`src/bioetl/domain/schemas/common/publication_base.py`)**:
- Line 64-67: `authors: Series[str] = pa.Field(nullable=True, description="JSON array of author names")` ✅

**Transformer Evidence (all serialize to JSON string)**:
- `pubmed/transformer.py`: `"authors": self.serialize_json_list(hashed_authors)`
- `crossref/transformer.py`: `"authors": self.serialize_json_list(hashed_authors)`
- `openalex/transformer.py`: `"authors": self.serialize_json_list(hashed_authors)`

---

## Finding 2: MISSING_FIELD - CrossRef Gold Schema

**Severity**: MEDIUM
**Pipeline**: `crossref_publication`
**Location**: `gold.py:748-810`

### Missing Fields

| Field | Silver Schema Line | Purpose |
|-------|-------------------|---------|
| `pmid` | 669 | Cross-provider linking |
| `pmc_id` | 667 | Cross-provider linking |
| `_lookup_method` | 648 | Resolution tracking |
| `_original_id` | 649 | Resolution tracking |

### Context

The transformer explicitly sets `pmid: None, pmc_id: None` (`transformer.py:157-158`) to prepare for future cross-enrichment. These fields exist in Silver but are absent from Gold.

### Recommended Fix

Add fields to `CrossRefPublicationGoldSchema`:

```python
# After doi field (line 761)
pmid: Series[str] = pa.Field(nullable=True)
pmc_id: Series[str] = pa.Field(nullable=True)

# After source field (line 794)
lookup_method: Series[str] = pa.Field(nullable=True, alias="_lookup_method")
original_id: Series[str] = pa.Field(nullable=True, alias="_original_id")
```

---

## Finding 3: MISSING_FIELD - PubMed Gold Schema

**Severity**: MEDIUM
**Pipeline**: `pubmed_publication`
**Location**: `gold.py:211-262`

### Missing Fields

| Field | Silver Schema Line | Purpose |
|-------|-------------------|---------|
| `_lookup_method` | 173 | Resolution tracking |
| `_original_id` | 174 | Resolution tracking |
| `source` | 207 | Provider identification |

### Recommended Fix

Add fields to `PubMedPublicationGoldSchema`:

```python
# After country field (line 246)
source: Series[str] = pa.Field(nullable=True)

# Before DQ fields (line 248)
lookup_method: Series[str] = pa.Field(nullable=True, alias="_lookup_method")
original_id: Series[str] = pa.Field(nullable=True, alias="_original_id")
```

---

## Finding 4: MISSING_FIELD - ChEMBL Document Gold Schema

**Severity**: MEDIUM
**Pipeline**: `chembl_publication`
**Location**: `gold.py:400-444`

### Missing Fields

| Field | Silver Schema Line | Purpose |
|-------|-------------------|---------|
| `_lookup_method` | 390 | Resolution tracking |
| `_original_id` | 391 | Resolution tracking |

### Recommended Fix

Add fields to `ChEMBLDocumentGoldSchema`:

```python
# After src_id field (line 428)
lookup_method: Series[str] = pa.Field(nullable=True, alias="_lookup_method")
original_id: Series[str] = pa.Field(nullable=True, alias="_original_id")
```

---

## Cross-Provider Field Mapping Verification

### DOI Normalization ✅

All providers use `DOI.from_raw()` value object for consistent normalization:

| Provider | Location | Method |
|----------|----------|--------|
| ChEMBL | `publication_transformer.py:162-163` | `DOI.from_raw(data.get("doi"))` |
| PubMed | `transformer.py:168-170` | `DOI.from_raw(raw_doi)` |
| CrossRef | `transformer.py:115-116` | `DOI.from_raw(rec.get("DOI"))` |
| OpenAlex | `transformer.py:130-131` | `DOI.from_raw(rec.get("doi"))` |
| SemanticScholar | `transformer.py:127-128` | `DOI.from_raw(raw_doi)` |

### PMID Normalization ✅

All providers use `PubMedId.from_raw()` or `normalize_pmid()`:

| Provider | Location | Method |
|----------|----------|--------|
| ChEMBL | `publication_transformer.py:48` | `PMID` converter (via `normalize_pmid`) |
| PubMed | `transformer.py:149-150` | `PubMedId.from_raw(raw_pmid)` |
| OpenAlex | `extractors.py` | Via `extract_external_ids` |
| SemanticScholar | `transformer.py:131-133` | `PubMedId.from_raw(raw_pmid)` |
| CrossRef | N/A | Does not provide PMID |

### PMC ID Normalization ✅

All providers use `normalize_pmc_id()`:

| Provider | Location | Method |
|----------|----------|--------|
| ChEMBL | `publication_transformer.py:189` | Set to `None` (API doesn't provide) |
| PubMed | `transformer.py:196` | `normalize_pmc_id(IdentifierExtractor.extract_pmc_id(root))` |
| OpenAlex | `transformer.py:178` | Via `extract_external_ids` |
| SemanticScholar | `transformer.py:172-174` | `normalize_pmc_id(external_ids.get("pmcid"))` |
| CrossRef | N/A | Does not provide PMC ID |

---

## Pipelines Verified as Correct

### 1. chembl_publication_similarity ✅

- **Transformer**: `publication_similarity_transformer.py`
- **Entity**: `DocumentSimilarity`
- **Silver**: `CHEMBL_DOCUMENT_SIMILARITY_SCHEMA`
- **Gold**: `ChEMBLDocumentSimilarityGoldSchema`
- **Status**: All fields correctly mapped, types consistent

### 2. chembl_publication_term ✅

- **Transformer**: `publication_term_transformer.py`
- **Entity**: `DocumentTerm`
- **Silver**: `CHEMBL_DOCUMENT_TERM_SCHEMA`
- **Gold**: `ChEMBLDocumentTermGoldSchema`
- **Status**: All fields correctly mapped, types consistent

### 3. semanticscholar_publication ✅

- **Transformer**: `semanticscholar/transformer.py`
- **Entity**: `SemanticScholarPublicationEntity`
- **Silver**: `SEMANTICSCHOLAR_PUBLICATION_SCHEMA`
- **Gold**: `SemanticScholarPublicationGoldSchema`
- **Status**: All fields correctly mapped, includes `_lookup_method` and `_original_id`

---

## Summary Table

| Finding | Category | Severity | Pipelines Affected | Status |
|---------|----------|----------|-------------------|--------|
| 1 | TYPE_MISMATCH | HIGH | pubmed, crossref, openalex | ✅ RESOLVED |
| 2 | MISSING_FIELD | MEDIUM | crossref | Open |
| 3 | MISSING_FIELD | MEDIUM | pubmed | Open |
| 4 | MISSING_FIELD | MEDIUM | chembl_publication | Open |

---

## Acceptance Criteria Status

| Criteria | Status |
|----------|--------|
| Mapping Matrix Complete | ✅ Verified for all 7 pipelines |
| No TYPE_MISMATCH | ✅ All type mismatches resolved (authors field fixed 2026-01-26) |
| No NULLABLE_MISMATCH | ✅ No nullable mismatches found |
| Cross-Provider Linking | ✅ DOI/PMID/PMC ID mapping verified |
| Documentation Updated | ✅ This report |

---

## References

- **RULES.md §2.4**: Content Hash и Entity ID
- **RULES.md §3.2**: Silver Layer Requirements
- **RULES.md §3.3**: Gold Layer Requirements
- **ADR-024**: Document → Publication Renaming
