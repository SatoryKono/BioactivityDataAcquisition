# Publication Pipeline Field Mapping Verification Report

> **Status:** Historical verification artifact (non-normative).
> Use this report as dated evidence only; current policy source of truth is `docs/00-project/RULES.md` and active ADRs.

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
| 2 | `chembl_publication_similarity` | ChEMBL | publication-similarity | ✅ Correct |
| 3 | `chembl_publication_term` | ChEMBL | publication-term | ✅ Correct |
| 4 | `pubmed_publication` | PubMed | publication | ⚠️ Missing Gold fields (Type mismatch ✅ FIXED) |
| 5 | `crossref_publication` | CrossRef | work | ⚠️ Missing Gold fields (Type mismatch ✅ FIXED) |
| 6 | `openalex_publication` | OpenAlex | publication | ✅ Correct (Type mismatch ✅ FIXED) |
| 7 | `semanticscholar_publication` | SemanticScholar | publication | ✅ Correct |

Примечание: API-ресурсы остаются `document*`, но canonical `entity-type` — `publication*` (см. ADR-024).

---

## Finding 1: TYPE-MISMATCH - `authors` Field Type Inconsistency

**Severity**: HIGH → ✅ **RESOLVED** (2026-01-26)
**Affected Pipelines**: `pubmed_publication`, `crossref_publication`, `openalex_publication`

### Issue

~~The `authors` field has inconsistent types between Silver (JSON string) and Gold (Python list) schemas for 3 providers, while 2 providers are correctly aligned.~~

**Resolution**: All Gold schemas now use `Series[str]` for the `authors` field, matching the Silver layer where transformers serialize authors to JSON strings via `serialize-json-list()`.

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

**Silver Schema (`src/bioetl/domain/schemas/common/publication-base.py`)**:
- Line 64-67: `authors: Series[str] = pa.Field(nullable=True, description="JSON array of author names")` ✅

**Transformer Evidence (all serialize to JSON string)**:
- `pubmed/transformer.py`: `"authors": self.serialize-json-list(hashed-authors)`
- `crossref/transformer.py`: `"authors": self.serialize-json-list(hashed-authors)`
- `openalex/transformer.py`: `"authors": self.serialize-json-list(hashed-authors)`

---

## Finding 2: MISSING-FIELD - CrossRef Gold Schema

**Severity**: MEDIUM
**Pipeline**: `crossref_publication`
**Location**: `gold.py:748-810`

### Missing Fields

| Field | Silver Schema Line | Purpose |
|-------|-------------------|---------|
| `pmid` | 669 | Cross-provider linking |
| `pmc-id` | 667 | Cross-provider linking |
| `-lookup-method` | 648 | Resolution tracking |
| `-original-id` | 649 | Resolution tracking |

### Context

The transformer explicitly sets `pmid: None, pmc-id: None` (`transformer.py:157-158`) to prepare for future cross-enrichment. These fields exist in Silver but are absent from Gold.

### Recommended Fix

Add fields to `CrossRefPublicationGoldSchema`:

```python
# After doi field (line 761)
pmid: Series[str] = pa.Field(nullable=True)
pmc-id: Series[str] = pa.Field(nullable=True)

# After source field (line 794)
lookup-method: Series[str] = pa.Field(nullable=True, alias="-lookup-method")
original-id: Series[str] = pa.Field(nullable=True, alias="-original-id")
```

---

## Finding 3: MISSING-FIELD - PubMed Gold Schema

**Severity**: MEDIUM
**Pipeline**: `pubmed_publication`
**Location**: `gold.py:211-262`

### Missing Fields

| Field | Silver Schema Line | Purpose |
|-------|-------------------|---------|
| `-lookup-method` | 173 | Resolution tracking |
| `-original-id` | 174 | Resolution tracking |
| `source` | 207 | Provider identification |

### Recommended Fix

Add fields to `PubMedPublicationGoldSchema`:

```python
# After country field (line 246)
source: Series[str] = pa.Field(nullable=True)

# Before DQ fields (line 248)
lookup-method: Series[str] = pa.Field(nullable=True, alias="-lookup-method")
original-id: Series[str] = pa.Field(nullable=True, alias="-original-id")
```

---

## Finding 4: MISSING-FIELD - ChEMBL Document Gold Schema

**Severity**: MEDIUM
**Pipeline**: `chembl_publication`
**Location**: `gold.py:400-444`

### Missing Fields

| Field | Silver Schema Line | Purpose |
|-------|-------------------|---------|
| `-lookup-method` | 390 | Resolution tracking |
| `-original-id` | 391 | Resolution tracking |

### Recommended Fix

Add fields to `ChEMBLPublicationGoldSchema`:

```python
# After src-id field (line 428)
lookup-method: Series[str] = pa.Field(nullable=True, alias="-lookup-method")
original-id: Series[str] = pa.Field(nullable=True, alias="-original-id")
```

---

## Cross-Provider Field Mapping Verification

### DOI Normalization ✅

All providers use `DOI.from-raw()` value object for consistent normalization:

| Provider | Location | Method |
|----------|----------|--------|
| ChEMBL | `publication-transformer.py:162-163` | `DOI.from-raw(data.get("doi"))` |
| PubMed | `transformer.py:168-170` | `DOI.from-raw(raw-doi)` |
| CrossRef | `transformer.py:115-116` | `DOI.from-raw(rec.get("DOI"))` |
| OpenAlex | `transformer.py:130-131` | `DOI.from-raw(rec.get("doi"))` |
| SemanticScholar | `transformer.py:127-128` | `DOI.from-raw(raw-doi)` |

### PMID Normalization ✅

All providers use `PubMedId.from-raw()` or `normalize-pmid()`:

| Provider | Location | Method |
|----------|----------|--------|
| ChEMBL | `publication-transformer.py:48` | `PMID` converter (via `normalize-pmid`) |
| PubMed | `transformer.py:149-150` | `PubMedId.from-raw(raw-pmid)` |
| OpenAlex | `extractors.py` | Via `extract-external-ids` |
| SemanticScholar | `transformer.py:131-133` | `PubMedId.from-raw(raw-pmid)` |
| CrossRef | N/A | Does not provide PMID |

### PMC ID Normalization ✅

All providers use `normalize-pmc-id()`:

| Provider | Location | Method |
|----------|----------|--------|
| ChEMBL | `publication-transformer.py:189` | Set to `None` (API doesn't provide) |
| PubMed | `transformer.py:196` | `normalize-pmc-id(IdentifierExtractor.extract-pmc-id(root))` |
| OpenAlex | `transformer.py:178` | Via `extract-external-ids` |
| SemanticScholar | `transformer.py:172-174` | `normalize-pmc-id(external-ids.get("pmcid"))` |
| CrossRef | N/A | Does not provide PMC ID |

---

## Pipelines Verified as Correct

### 1. chembl_publication_similarity ✅

- **Transformer**: `publication-similarity-transformer.py`
- **Entity**: `ChemblPublicationSimilarity`
- **Silver**: `CHEMBL-DOCUMENT-SIMILARITY-SCHEMA`
- **Gold**: `ChEMBLPublicationSimilarityGoldSchema`
- **Status**: All fields correctly mapped, types consistent

### 2. chembl_publication_term ✅

- **Transformer**: `publication-term-transformer.py`
- **Entity**: `ChemblPublicationTerm`
- **Silver**: `CHEMBL-DOCUMENT-TERM-SCHEMA`
- **Gold**: `ChEMBLPublicationTermGoldSchema`
- **Status**: All fields correctly mapped, types consistent

### 3. semanticscholar_publication ✅

- **Transformer**: `semanticscholar/transformer.py`
- **Entity**: `SemanticScholarPublicationEntity`
- **Silver**: `SEMANTICSCHOLAR-PUBLICATION-SCHEMA`
- **Gold**: `SemanticScholarPublicationGoldSchema`
- **Status**: All fields correctly mapped, includes `-lookup-method` and `-original-id`

---

## Summary Table

| Finding | Category | Severity | Pipelines Affected | Status |
|---------|----------|----------|-------------------|--------|
| 1 | TYPE-MISMATCH | HIGH | pubmed, crossref, openalex | ✅ RESOLVED |
| 2 | MISSING-FIELD | MEDIUM | crossref | Open |
| 3 | MISSING-FIELD | MEDIUM | pubmed | Open |
| 4 | MISSING-FIELD | MEDIUM | chembl_publication | Open |

---

## Acceptance Criteria Status

| Criteria | Status |
|----------|--------|
| Mapping Matrix Complete | ✅ Verified for all 7 pipelines |
| No TYPE-MISMATCH | ✅ All type mismatches resolved (authors field fixed 2026-01-26) |
| No NULLABLE-MISMATCH | ✅ No nullable mismatches found |
| Cross-Provider Linking | ✅ DOI/PMID/PMC ID mapping verified |
| Documentation Updated | ✅ This report |

---

## References

- **RULES.md §2.4**: Content Hash и Entity ID
- **RULES.md §3.2**: Silver Layer Requirements
- **RULES.md §3.3**: Gold Layer Requirements
- **ADR-024**: Document → Publication Renaming
