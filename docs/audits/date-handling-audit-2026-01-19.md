# Audit Report: Date Handling

**Date**: 2026-01-19
**Auditor**: Claude
**Scope**: All publication transformers (7 pipelines)
**Requirement**: YYYY-MM-DD format, partial date strategy: end of period (YYYY-MM → -30, YYYY → -12-31)

---

## Executive Summary

The audit identified **critical inconsistencies** in date handling across publication pipelines:

1. **Current implementation uses "start of period"** (YYYY-01-01, YYYY-MM-01) instead of required "end of period"
2. **OpenAlex and SemanticScholar have NO date normalization** - raw API data passed through
3. **No schema-level regex validation** for date format enforcement

---

## Current State

| Pipeline | Date Field | Current Output Format | Partial Date Handling | Has Regex Validation |
|----------|------------|----------------------|----------------------|---------------------|
| **pubmed** | publication_date | YYYY-MM-DD | Priority: epub→pub_date→year. Year-only: `YYYY-01-01` (start) | No |
| pubmed | epub_date | YYYY-MM-DD, YYYY-MM, YYYY | No normalization - partial dates pass through | No |
| pubmed | pub_date | YYYY-MM-DD, YYYY-MM, YYYY | No normalization - partial dates pass through | No |
| pubmed | accepted_date | YYYY-MM-DD, YYYY-MM, YYYY | No normalization | No |
| pubmed | received_date | YYYY-MM-DD, YYYY-MM, YYYY | No normalization | No |
| pubmed | revised_date | YYYY-MM-DD, YYYY-MM, YYYY | No normalization | No |
| **crossref** | publication_date | YYYY-MM-DD | `YYYY-MM→-01`, `YYYY→-01-01` (start of period) | No |
| crossref | published_print | YYYY-MM-DD, YYYY-MM, YYYY | No normalization - partial dates in output | No |
| crossref | published_online | YYYY-MM-DD, YYYY-MM, YYYY | No normalization - partial dates in output | No |
| **openalex** | publication_date | Pass-through from API | **NO normalization** | No |
| **semanticscholar** | publication_date | Pass-through from API | **NO normalization** | No |
| **chembl** | publication_date | YYYY-01-01 | Year-only: `YYYY-01-01` (start of period) | No |

---

## Normalization Infrastructure

### Existing Functions

| Function | Location | Purpose |
|----------|----------|---------|
| `format_date_parts()` | `domain/normalization.py:41-47` | CrossRef date-parts to ISO string (preserves partial) |
| `parse_date_field()` | `domain/normalization.py:50-59` | Parse date string to date object |
| `DateExtractor` | `pubmed/extractors/date.py` | PubMed XML date parsing (returns partial dates) |

### Existing Tests

| Test File | Coverage |
|-----------|----------|
| `tests/unit/application/pipelines/test_date_parsing.py` | Tests `_compute_publication_date` for PubMed & CrossRef |
| `tests/unit/pipelines/pubmed/extractors/test_date_extractor.py` | Tests DateExtractor methods |

---

## Gaps Identified

### 1. Inconsistent Partial Date Strategy (CRITICAL)

**Requirement**: "end of period" (`YYYY-MM → last day of month`, `YYYY → -12-31`)
**Current**: "start of period" (`YYYY-MM → -01`, `YYYY → -01-01`)

**Files affected**:
- `crossref/transformer.py:230-241` (`_compute_publication_date`)
- `pubmed/transformer.py:283-295` (`_compute_publication_date`)
- `chembl/publication_transformer.py:171` (inline date computation)

**Code example (CrossRef - current behavior)**:
```python
# crossref/transformer.py:234-241
# Partial date: YYYY-MM -> YYYY-MM-01  <-- Should be last day of month
if len(date_str) == 7 and date_str[4] == "-":
    return f"{date_str}-01"

# Partial date: YYYY -> YYYY-01-01  <-- Should be YYYY-12-31
if len(date_str) == 4 and date_str.isdigit():
    return f"{date_str}-01-01"
```

### 2. OpenAlex: No Date Normalization (HIGH)

- `openalex/transformer.py:187` passes `publication_date` directly from API
- No `_compute_publication_date` method
- OpenAlex API may return partial dates (YYYY, YYYY-MM)

### 3. SemanticScholar: No Date Normalization (HIGH)

- `semanticscholar/transformer.py:188` passes `publicationDate` directly from API
- No `_compute_publication_date` method
- S2 API may return partial dates

### 4. No Schema Regex Validation (MEDIUM)

- All date fields use `pa.Field(nullable=True)` without `str_matches` pattern
- No enforcement of YYYY-MM-DD format at schema level
- Files: `infrastructure/schemas/silver.py`, `infrastructure/schemas/gold.py`

### 5. PubMed Legacy Date Fields Not Normalized (LOW)

- `epub_date`, `pub_date`, `accepted_date`, `received_date`, `revised_date` can contain partial dates
- Only `publication_date` is normalized

### 6. Missing Tests for End-of-Period Strategy

- Current tests verify start-of-period behavior
- Need tests that verify correct end-of-period transformation

---

## Priority Order

| Priority | Task | Files | Est. Lines |
|----------|------|-------|------------|
| **P1** | Create centralized date normalization utility | `domain/normalization.py` | +30 |
| **P2** | Fix CrossRef `_compute_publication_date` | `crossref/transformer.py` | ~10 |
| **P3** | Fix PubMed `_compute_publication_date` | `pubmed/transformer.py` | ~5 |
| **P4** | Add date normalization to OpenAlex | `openalex/transformer.py` | +25 |
| **P5** | Add date normalization to SemanticScholar | `semanticscholar/transformer.py` | +25 |
| **P6** | Fix ChEMBL publication_date | `chembl/publication_transformer.py` | ~2 |
| **P7** | Add schema regex validation (optional) | `schemas/silver.py`, `schemas/gold.py` | ~20 |
| **P8** | Update tests for end-of-period | `test_date_parsing.py` | +50 |

---

## Proposed Solution

### New Centralized Function

```python
# domain/normalization.py
import calendar

def normalize_partial_date(date_str: str | None) -> str | None:
    """Normalize partial date to YYYY-MM-DD using end-of-period strategy.

    Args:
        date_str: Date string (YYYY-MM-DD, YYYY-MM, or YYYY).

    Returns:
        Full ISO date (YYYY-MM-DD) or None.

    Examples:
        >>> normalize_partial_date("2024-03-15")
        '2024-03-15'
        >>> normalize_partial_date("2024-03")
        '2024-03-31'
        >>> normalize_partial_date("2024")
        '2024-12-31'
    """
    if not date_str:
        return None

    # Already full ISO format
    if len(date_str) == 10 and date_str[4] == "-" and date_str[7] == "-":
        return date_str

    # YYYY-MM -> YYYY-MM-{last_day}
    if len(date_str) == 7 and date_str[4] == "-":
        year, month = int(date_str[:4]), int(date_str[5:7])
        _, last_day = calendar.monthrange(year, month)
        return f"{date_str}-{last_day:02d}"

    # YYYY -> YYYY-12-31
    if len(date_str) == 4 and date_str.isdigit():
        return f"{date_str}-12-31"

    return date_str
```

---

## Verification Commands

```bash
# Find all date handling in transformers
grep -rn "publication_date\|_compute_publication_date" \
    src/bioetl/application/pipelines/*/transformer.py

# Check normalization functions
grep -rn "def.*date" src/bioetl/domain/normalization.py

# Run existing date tests
pytest tests/unit/application/pipelines/test_date_parsing.py -v
pytest tests/unit/pipelines/pubmed/extractors/test_date_extractor.py -v
```

---

## Appendix: File Locations

| Component | Path |
|-----------|------|
| PubMed Transformer | `src/bioetl/application/pipelines/pubmed/transformer.py` |
| CrossRef Transformer | `src/bioetl/application/pipelines/crossref/transformer.py` |
| OpenAlex Transformer | `src/bioetl/application/pipelines/openalex/transformer.py` |
| SemanticScholar Transformer | `src/bioetl/application/pipelines/semanticscholar/transformer.py` |
| ChEMBL Publication Transformer | `src/bioetl/application/pipelines/chembl/publication_transformer.py` |
| Domain Normalization | `src/bioetl/domain/normalization.py` |
| PubMed DateExtractor | `src/bioetl/application/pipelines/pubmed/extractors/date.py` |
| CrossRef Extractors | `src/bioetl/application/pipelines/crossref/extractors.py` |
| Silver Schemas | `src/bioetl/infrastructure/schemas/silver.py` |
| Gold Schemas | `src/bioetl/infrastructure/schemas/gold.py` |
| Date Parsing Tests | `tests/unit/application/pipelines/test_date_parsing.py` |
