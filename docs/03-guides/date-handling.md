______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Date Handling Guide

This guide documents how dates are processed, normalized, and validated across BioETL pipelines.

______________________________________________________________________

## Overview

BioETL normalizes all publication dates to **ISO 8601 format (YYYY-MM-DD)** for consistency across
providers. Partial dates (year-only or year-month) are normalized using the **end-of-period** strategy.

______________________________________________________________________

## End-of-Period Normalization Strategy

When a date has incomplete precision (e.g., only year or year-month), BioETL normalizes to the
**end of the period**:

| Input        | Output       | Rationale                            |
| ------------ | ------------ | ------------------------------------ |
| `2024-03-15` | `2024-03-15` | Full date, unchanged                 |
| `2024-03`    | `2024-03-30` | End of month (day 30 for simplicity) |
| `2024`       | `2024-12-31` | End of year                          |

**Why end-of-period?**

End-of-period normalization ensures that:

1. Date range queries include all records from partial periods
1. Publications from "2024" appear in queries for "dates ≤ 2024-12-31"
1. Sorting by date places partial dates at the end of their period

______________________________________________________________________

## Core Functions

### `format-date-parts()` (CrossRef)

Location: `src/bioetl/domain/normalization.py:56-73`

Converts CrossRef API date-parts format to ISO string:

```python
from bioetl.domain.normalization import format-date-parts

# Full date
format-date-parts([[2024, 3, 15]])  # → "2024-03-15"

# Partial month (uses calendar.monthrange for exact last day)
format-date-parts([[2024, 3]])      # → "2024-03-31"

# Year only
format-date-parts([[2024]])         # → "2024-12-31"

# Empty/invalid
format-date-parts(None)             # → None
format-date-parts([])               # → None
```

### `parse-date-field()`

Location: `src/bioetl/domain/normalization.py:88-97`

Parses date string to Python `date` object:

```python
from bioetl.domain.normalization import parse-date-field

parse-date-field("2024-03-15")           # → date(2024, 3, 15)
parse-date-field("2024-03-15", "%Y-%m-%d")  # → date(2024, 3, 15)
parse-date-field("invalid")              # → None
parse-date-field(None)                   # → None
```

### `DefaultDataNormalizer.normalize-partial-date()`

Location: `src/bioetl/domain/behavior/data_normalization_service.py:186-240`

Service-based partial date normalization:

```python
from bioetl.domain.behavior.data-normalization-service import (
    DefaultDataNormalizer,
)

service = DefaultDataNormalizer()

service.normalize-partial-date("2024-03-15")  # → "2024-03-15"
service.normalize-partial-date("2024-03")     # → "2024-03-30"
service.normalize-partial-date("2024")        # → "2024-12-31"
service.normalize-partial-date(None)          # → None
```

______________________________________________________________________

## Provider-Specific Implementations

### PubMed

**Date Extractor**: `src/bioetl/application/pipelines/pubmed/extractors/date.py`

Extracts dates from PubMed XML:

- `publication-date` (unified, normalized)
- `pub-date`, `epub-date` (original dates)
- `accepted-date`, `received-date`, `revised-date` (history dates)

**Date Priority** (`-compute-publication-date`):

1. `epub-date` (electronic publication)
1. `pub-date` (print publication)
1. Year from article metadata

```python
# Priority chain for publication-date
publication - date = epub - date or pub - date or f"{year}-12-31"
```

### CrossRef

**Extractors**: `src/bioetl/application/pipelines/crossref/extractors.py`

Uses `format-date-parts()` for date normalization:

- `published-print`, `published-online` (from API date-parts)
- `publication-date` (unified: prefers print over online)

```python
# Date normalization in extractor
published - print = (
    format - date - parts(record.get("published-print", {}).get("date-parts"))
)
published - online = (
    format - date - parts(record.get("published-online", {}).get("date-parts"))
)
```

### OpenAlex

**Transformer**: `src/bioetl/application/pipelines/openalex/transformer.py:229-266`

Implements `-normalize-partial-date()` inline:

```python
def -normalize-partial-date(self, date-str: str | None) -> str | None:
    # Full date (YYYY-MM-DD) - unchanged
    # YYYY-MM → YYYY-MM-30
    # YYYY → YYYY-12-31
```

### SemanticScholar

**Transformer**: `src/bioetl/application/pipelines/semanticscholar/transformer.py`

Uses identical `-normalize-partial-date()` implementation:

```python
publication-date = self.-normalize-partial-date(raw.get("publicationDate"))
```

### ChEMBL

**Transformer**: `src/bioetl/application/pipelines/chembl/publication_transformer.py`

ChEMBL only provides year information. Uses start-of-year convention:

```python
# Year only → YYYY-01-01 (differs from other pipelines)
publication - date = f"{year}-01-01"
```

**Note**: This differs from the end-of-period strategy used by other pipelines.
ChEMBL publication data focuses on journal metadata where precise dates are unavailable.

______________________________________________________________________

## Adding Date Handling to New Pipelines

When creating a new publication pipeline:

### 1. Use Centralized Functions When Possible

```python
from bioetl.domain.normalization import format-date-parts, parse-date-field
```

### 2. Implement `-normalize-partial-date()` Method

If the API returns string dates in various formats:

```python
def -normalize-partial-date(self, date-str: str | None) -> str | None:
    """Normalize partial date to YYYY-MM-DD format (end of period)."""
    if not date-str:
        return None

    date-str = str(date-str).strip()

    # Full ISO format (YYYY-MM-DD) - return as-is
    if len(date-str) == 10 and date-str[4] == "-" and date-str[7] == "-":
        return date-str

    # Partial date: YYYY-MM → YYYY-MM-30
    if len(date-str) == 7 and date-str[4] == "-":
        return f"{date-str}-30"

    # Partial date: YYYY → YYYY-12-31
    if len(date-str) == 4 and date-str.isdigit():
        return f"{date-str}-12-31"

    return None
```

### 3. Implement `-compute-publication-date()` Method

For unified publication date with priority chain:

```python
def -compute-publication-date(
    self,
    primary-date: str | None,
    fallback-date: str | None,
) -> str | None:
    """Build unified publication-date, preferring primary source."""
    return self.-normalize-partial-date(primary-date) or \
           self.-normalize-partial-date(fallback-date)
```

### 4. Add Tests

Create unit tests in `tests/unit/application/pipelines/`:

```python
import pytest

class TestNewProviderDateHandling:
    def test-full-date-unchanged(self, transformer):
        assert transformer.-normalize-partial-date("2024-03-15") == "2024-03-15"

    def test-partial-month-normalized(self, transformer):
        assert transformer.-normalize-partial-date("2024-03") == "2024-03-30"

    def test-year-only-normalized(self, transformer):
        assert transformer.-normalize-partial-date("2024") == "2024-12-31"

    def test-none-returns-none(self, transformer):
        assert transformer.-normalize-partial-date(None) is None
```

______________________________________________________________________

## Content Hash and Dates

When computing content hash for deduplication, dates are normalized to ISO format:

```python
# From domain/transformations.py
# Dates normalized to YYYY-MM-DD before hashing
```

**Excluded from hash**: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_*` (technical metadata)

______________________________________________________________________

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

______________________________________________________________________

## Related Documentation

- **Audit Report**: `docs/audits/date-handling-audit-2026-01-19.md`
- **Normalization Functions**: `src/bioetl/domain/normalization.py`
- **Data Normalization Service**: `src/bioetl/domain/behavior/data_normalization_service.py`
- **RULES.md**: §2.4 Content Hash normalization
