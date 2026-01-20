# Date Handling Guide

This guide documents how dates are processed, normalized, and validated across BioETL pipelines.

---

## Overview

BioETL normalizes all publication dates to **ISO 8601 format (YYYY-MM-DD)** for consistency across
providers. Partial dates (year-only or year-month) are normalized using the **end-of-period** strategy.

---

## End-of-Period Normalization Strategy

When a date has incomplete precision (e.g., only year or year-month), BioETL normalizes to the
**end of the period**:

| Input | Output | Rationale |
|-------|--------|-----------|
| `2024-03-15` | `2024-03-15` | Full date, unchanged |
| `2024-03` | `2024-03-30` | End of month (day 30 for simplicity) |
| `2024` | `2024-12-31` | End of year |

**Why end-of-period?**

End-of-period normalization ensures that:
1. Date range queries include all records from partial periods
2. Publications from "2024" appear in queries for "dates ≤ 2024-12-31"
3. Sorting by date places partial dates at the end of their period

---

## Core Functions

### `format_date_parts()` (CrossRef)

Location: `src/bioetl/domain/normalization.py:56-73`

Converts CrossRef API date-parts format to ISO string:

```python
from bioetl.domain.normalization import format_date_parts

# Full date
format_date_parts([[2024, 3, 15]])  # → "2024-03-15"

# Partial month (uses calendar.monthrange for exact last day)
format_date_parts([[2024, 3]])      # → "2024-03-31"

# Year only
format_date_parts([[2024]])         # → "2024-12-31"

# Empty/invalid
format_date_parts(None)             # → None
format_date_parts([])               # → None
```

### `parse_date_field()`

Location: `src/bioetl/domain/normalization.py:88-97`

Parses date string to Python `date` object:

```python
from bioetl.domain.normalization import parse_date_field

parse_date_field("2024-03-15")           # → date(2024, 3, 15)
parse_date_field("2024-03-15", "%Y-%m-%d")  # → date(2024, 3, 15)
parse_date_field("invalid")              # → None
parse_date_field(None)                   # → None
```

### `DefaultDataNormalizationService.normalize_partial_date()`

Location: `src/bioetl/domain/services/data_normalization_service.py:186-240`

Service-based partial date normalization:

```python
from bioetl.domain.services.data_normalization_service import (
    DefaultDataNormalizationService,
)

service = DefaultDataNormalizationService()

service.normalize_partial_date("2024-03-15")  # → "2024-03-15"
service.normalize_partial_date("2024-03")     # → "2024-03-30"
service.normalize_partial_date("2024")        # → "2024-12-31"
service.normalize_partial_date(None)          # → None
```

---

## Provider-Specific Implementations

### PubMed

**Date Extractor**: `src/bioetl/application/pipelines/pubmed/extractors/date.py`

Extracts dates from PubMed XML:
- `publication_date` (unified, normalized)
- `pub_date`, `epub_date` (original dates)
- `accepted_date`, `received_date`, `revised_date` (history dates)

**Date Priority** (`_compute_publication_date`):
1. `epub_date` (electronic publication)
2. `pub_date` (print publication)
3. Year from article metadata

```python
# Priority chain for publication_date
publication_date = epub_date or pub_date or f"{year}-12-31"
```

### CrossRef

**Extractors**: `src/bioetl/application/pipelines/crossref/extractors.py`

Uses `format_date_parts()` for date normalization:
- `published_print`, `published_online` (from API date-parts)
- `publication_date` (unified: prefers print over online)

```python
# Date normalization in extractor
published_print = format_date_parts(record.get("published-print", {}).get("date-parts"))
published_online = format_date_parts(record.get("published-online", {}).get("date-parts"))
```

### OpenAlex

**Transformer**: `src/bioetl/application/pipelines/openalex/transformer.py:229-266`

Implements `_normalize_partial_date()` inline:

```python
def _normalize_partial_date(self, date_str: str | None) -> str | None:
    # Full date (YYYY-MM-DD) - unchanged
    # YYYY-MM → YYYY-MM-30
    # YYYY → YYYY-12-31
```

### SemanticScholar

**Transformer**: `src/bioetl/application/pipelines/semanticscholar/transformer.py`

Uses identical `_normalize_partial_date()` implementation:

```python
publication_date = self._normalize_partial_date(raw.get("publicationDate"))
```

### ChEMBL

**Transformer**: `src/bioetl/application/pipelines/chembl/publication_transformer.py`

ChEMBL only provides year information. Uses start-of-year convention:

```python
# Year only → YYYY-01-01 (differs from other pipelines)
publication_date = f"{year}-01-01"
```

**Note**: This differs from the end-of-period strategy used by other pipelines.
ChEMBL publication data focuses on journal metadata where precise dates are unavailable.

---

## Adding Date Handling to New Pipelines

When creating a new publication pipeline:

### 1. Use Centralized Functions When Possible

```python
from bioetl.domain.normalization import format_date_parts, parse_date_field
```

### 2. Implement `_normalize_partial_date()` Method

If the API returns string dates in various formats:

```python
def _normalize_partial_date(self, date_str: str | None) -> str | None:
    """Normalize partial date to YYYY-MM-DD format (end of period)."""
    if not date_str:
        return None

    date_str = str(date_str).strip()

    # Full ISO format (YYYY-MM-DD) - return as-is
    if len(date_str) == 10 and date_str[4] == "-" and date_str[7] == "-":
        return date_str

    # Partial date: YYYY-MM → YYYY-MM-30
    if len(date_str) == 7 and date_str[4] == "-":
        return f"{date_str}-30"

    # Partial date: YYYY → YYYY-12-31
    if len(date_str) == 4 and date_str.isdigit():
        return f"{date_str}-12-31"

    return None
```

### 3. Implement `_compute_publication_date()` Method

For unified publication date with priority chain:

```python
def _compute_publication_date(
    self,
    primary_date: str | None,
    fallback_date: str | None,
) -> str | None:
    """Build unified publication_date, preferring primary source."""
    return self._normalize_partial_date(primary_date) or \
           self._normalize_partial_date(fallback_date)
```

### 4. Add Tests

Create unit tests in `tests/unit/application/pipelines/`:

```python
import pytest

class TestNewProviderDateHandling:
    def test_full_date_unchanged(self, transformer):
        assert transformer._normalize_partial_date("2024-03-15") == "2024-03-15"

    def test_partial_month_normalized(self, transformer):
        assert transformer._normalize_partial_date("2024-03") == "2024-03-30"

    def test_year_only_normalized(self, transformer):
        assert transformer._normalize_partial_date("2024") == "2024-12-31"

    def test_none_returns_none(self, transformer):
        assert transformer._normalize_partial_date(None) is None
```

---

## Content Hash and Dates

When computing content hash for deduplication, dates are normalized to ISO format:

```python
# From domain/transformations.py
# Dates normalized to YYYY-MM-DD before hashing
```

**Excluded from hash**: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_*` (technical metadata)

---

## Testing

Run date-related tests:

```bash
# Unit tests
pytest tests/unit/application/pipelines/test_date_parsing.py -v

# PubMed date extractor tests
pytest tests/unit/pipelines/pubmed/extractors/test_date_extractor.py -v

# Integration tests
pytest tests/integration/pipelines/test_pubmed_date_normalization.py -v
pytest tests/integration/pipelines/test_crossref_date_normalization.py -v
```

---

## Related Documentation

- **Audit Report**: `docs/audits/date-handling-audit-2026-01-19.md`
- **Normalization Functions**: `src/bioetl/domain/normalization.py`
- **Data Normalization Service**: `src/bioetl/domain/services/data_normalization_service.py`
- **RULES.md**: §2.4 Content Hash normalization
