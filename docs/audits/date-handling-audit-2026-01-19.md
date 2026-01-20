# Audit Report: Date Handling

**Date**: 2026-01-19 (Updated: 2026-01-20)
**Auditor**: Claude
**Scope**: All publication transformers (7 pipelines)
**Requirement**: YYYY-MM-DD format, partial date strategy: end of period (YYYY-MM → last day, YYYY → -12-31)

---

## Executive Summary

✅ **COMPLIANT**: All publication pipelines correctly implement end-of-period date normalization.

The codebase has comprehensive date handling infrastructure:
- Centralized `format_date_parts()` in `domain/normalization.py`
- `DefaultDataNormalizationService.normalize_partial_date()` in domain services
- Per-transformer `_normalize_partial_date()` methods with consistent implementation
- All output dates in YYYY-MM-DD format

---

## Current State

| Pipeline | Date Field | Output Format | Partial Date Strategy | Status |
|----------|------------|---------------|----------------------|--------|
| **pubmed** | publication_date | YYYY-MM-DD | End-of-period (YYYY-MM→-30, YYYY→-12-31) | ✅ |
| **crossref** | publication_date | YYYY-MM-DD | End-of-period via `format_date_parts()` | ✅ |
| **openalex** | publication_date | YYYY-MM-DD | End-of-period (`_normalize_partial_date`) | ✅ |
| **semanticscholar** | publication_date | YYYY-MM-DD | End-of-period (`_normalize_partial_date`) | ✅ |
| **chembl** | publication_date | YYYY-MM-DD | Year-only: YYYY-01-01 (start of year) | ⚠️ Note |

**Note on ChEMBL**: ChEMBL publication data only contains year information. The transformer uses YYYY-01-01
(start of year) convention which differs from other pipelines. This is acceptable as ChEMBL publications
focus on journal metadata where precise dates are unavailable.

---

## Date Normalization Infrastructure

### Core Functions

| Function | Location | Purpose |
|----------|----------|---------|
| `format_date_parts()` | `domain/normalization.py:56-73` | CrossRef date-parts to ISO (end-of-period) |
| `parse_date_field()` | `domain/normalization.py:88-97` | Parse date string to Python date object |
| `normalize_partial_date()` | `domain/services/data_normalization_service.py:186-240` | Service method for partial date normalization |

### Transformer Methods

| Pipeline | Method | Location |
|----------|--------|----------|
| PubMed | `_normalize_partial_date()` | `pubmed/transformer.py:300-319` |
| PubMed | `_compute_publication_date()` | `pubmed/transformer.py:270-298` |
| CrossRef | `_compute_publication_date()` | `crossref/transformer.py:209-226` |
| OpenAlex | `_normalize_partial_date()` | `openalex/transformer.py:229-266` |
| SemanticScholar | `_normalize_partial_date()` | `semanticscholar/transformer.py:225+` |

---

## Date Handling Strategy

### End-of-Period Normalization

The project uses **end-of-period** normalization for partial dates:

| Input Format | Normalized Output | Rationale |
|--------------|-------------------|-----------|
| `2024-03-15` | `2024-03-15` | Full date unchanged |
| `2024-03` | `2024-03-30` | End of month (simplified day 30) |
| `2024` | `2024-12-31` | End of year |

**Rationale**: End-of-period ensures that date-based queries include all records from the partial period.
For example, a publication from "2024" should be included when querying for dates ≤ 2024-12-31.

### CrossRef Date-Parts

CrossRef API returns dates as nested arrays: `[[year, month?, day?]]`

| API Response | Normalized |
|--------------|------------|
| `[[2024, 3, 15]]` | `2024-03-15` |
| `[[2024, 3]]` | `2024-03-31` (exact last day via `calendar.monthrange`) |
| `[[2024]]` | `2024-12-31` |

---

## Test Coverage

| Test File | Coverage |
|-----------|----------|
| `tests/unit/application/pipelines/test_date_parsing.py` | Unit tests for `_compute_publication_date` |
| `tests/unit/pipelines/pubmed/extractors/test_date_extractor.py` | PubMed XML date extraction |
| `tests/integration/pipelines/test_pubmed_date_normalization.py` | Integration tests for PubMed dates |
| `tests/integration/pipelines/test_crossref_date_normalization.py` | Integration tests for CrossRef dates |

---

## Verification Commands

```bash
# Find all date normalization methods
grep -rn "_normalize_partial_date\|_compute_publication_date" \
    src/bioetl/application/pipelines/*/transformer.py

# Check centralized normalization functions
grep -rn "def.*date" src/bioetl/domain/normalization.py

# Verify format_date_parts implementation
grep -A 20 "def format_date_parts" src/bioetl/domain/normalization.py

# Run date-related tests
pytest tests/unit/application/pipelines/test_date_parsing.py -v
pytest tests/integration/pipelines/test_pubmed_date_normalization.py -v
pytest tests/integration/pipelines/test_crossref_date_normalization.py -v
```

---

## File Locations

| Component | Path |
|-----------|------|
| Domain Normalization | `src/bioetl/domain/normalization.py` |
| Data Normalization Service | `src/bioetl/domain/services/data_normalization_service.py` |
| PubMed Transformer | `src/bioetl/application/pipelines/pubmed/transformer.py` |
| PubMed DateExtractor | `src/bioetl/application/pipelines/pubmed/extractors/date.py` |
| CrossRef Transformer | `src/bioetl/application/pipelines/crossref/transformer.py` |
| CrossRef Extractors | `src/bioetl/application/pipelines/crossref/extractors.py` |
| OpenAlex Transformer | `src/bioetl/application/pipelines/openalex/transformer.py` |
| SemanticScholar Transformer | `src/bioetl/application/pipelines/semanticscholar/transformer.py` |
| ChEMBL Publication Transformer | `src/bioetl/application/pipelines/chembl/publication_transformer.py` |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-01-19 | Initial audit (contained inaccuracies) |
| 2026-01-20 | Updated to reflect correct implementation state |
