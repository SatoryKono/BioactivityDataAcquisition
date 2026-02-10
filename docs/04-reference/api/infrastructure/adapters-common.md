# Common Adapter Utilities

**Module:** `bioetl.infrastructure.adapters.common`
**Version:** 5.14.0
**Last updated:** 2026-02-10

---

## Overview

The `common` module provides shared utilities and base classes for infrastructure adapters. These components enable consistent API request tracking, title-based fallback search, and text normalization across all provider adapters.

**Key Components:**
- `APIRequestCollector` — Thread-safe request metadata collector
- `BaseTitleFallbackHandler` — Abstract base for title-based DOI resolution
- `normalize_title()`, `titles_match()` — Title normalization and fuzzy matching utilities

---

## APIRequestCollector

**Purpose:** Collects API request metadata for Bronze layer audit trail and rate limit monitoring.

**Thread-safety:** ✅ Safe for concurrent request recording within a single pipeline run.

### Usage

```python
from bioetl.infrastructure.adapters.common import APIRequestCollector

# Initialize collector
collector = APIRequestCollector()

# Record each API request
collector.record_request(
    url="https://api.example.com/data?limit=100",
    method="GET",
    response_size=1024,
    duration_ms=150.5,
    status_code=200,
    rate_limit_remaining=950,  # Optional
    rate_limit_reset=1234567890,  # Optional
)

# Generate Bronze metadata
source_metadata = collector.to_source_metadata()
# Returns: SourceMetadata with aggregate statistics:
#   - total_requests: 1
#   - total_bytes: 1024
#   - avg_duration_ms: 150.5
#   - endpoints_hit: ["https://api.example.com"]
```

### Key Methods

| Method | Description | Thread-safe |
|--------|-------------|-------------|
| `record_request()` | Record API request details | ✅ |
| `to_source_metadata()` | Generate SourceMetadata with aggregates | ✅ |
| `reset()` | Clear all recorded requests | ✅ |

### Integration with Adapters

All HTTP adapters **SHOULD** use `APIRequestCollector` to track API calls:

```python
class MyAdapter:
    def __init__(self, http_client: UnifiedHTTPClient, logger: LoggerPort):
        self._http = http_client
        self._logger = logger
        self._collector = APIRequestCollector()

    async def fetch(self, query: Query) -> AsyncIterator[RawRecord]:
        async for response in self._http.get("/endpoint", params=query.params):
            # Record request
            self._collector.record_request(
                url=str(response.url),
                method="GET",
                response_size=len(response.content),
                duration_ms=response.elapsed.total_seconds() * 1000,
                status_code=response.status_code,
            )

            for record in response.json()["results"]:
                yield RawRecord(
                    data=record,
                    source_metadata=self._collector.to_source_metadata(),
                )
```

**Related ADR:** [ADR-029: Output Metadata Unification](../../02-architecture/decisions/ADR-029-output-metadata-unification.md)

---

## BaseTitleFallbackHandler

**Purpose:** Abstract base class for title-based DOI resolution when batch ID lookup fails.

**Use case:** CrossRef, OpenAlex, and other publication providers often fail to resolve DOIs directly. This handler implements a three-phase fallback strategy:

1. **Phase 1:** Batch ID lookup (implemented by adapter)
2. **Phase 2:** Title fallback for unresolved IDs (`process_missing_dois()`)
3. **Phase 3:** Title-only lookup for entries without IDs (`process_title_only_entries()`)

### Three-Phase Fallback Strategy

```mermaid
flowchart LR
    A[Input: IDs + Titles] --> B{Phase 1: Batch ID}
    B -->|Success| C[Resolved]
    B -->|Fail| D{Phase 2: Title Fallback}
    D -->|Title exists| E[Title search]
    D -->|No title| F[Skip]
    E -->|Found| C
    E -->|Not found| F

    G[Input: Title only] --> H{Phase 3: Title-only}
    H -->|Title exists| I[Title search]
    H -->|No title| F
    I -->|Found| C
    I -->|Not found| F
```

### Abstract Methods

Subclasses **MUST** implement:

```python
@abstractmethod
async def search_by_title(self, title: str) -> dict[str, Any] | None:
    """Provider-specific title search implementation.

    Args:
        title: Normalized title string

    Returns:
        Dict with provider data if found, None otherwise
    """
```

### Event Naming Convention

When `provider_prefix` is set (e.g., `"crossref"`), event names are auto-generated:

| Event | When Emitted | Metrics Key |
|-------|--------------|-------------|
| `{provider}_no_fallback_title` | Phase 2/3: No title available | `crossref_no_fallback_title` |
| `{provider}_title_fallback_attempt` | Phase 2: Starting title search | `crossref_title_fallback_attempt` |
| `{provider}_title_fallback_success` | Phase 2: Title match found | `crossref_title_fallback_success` |
| `{provider}_title_fallback_not_found` | Phase 2: No match | `crossref_title_fallback_not_found` |
| `{provider}_title_only_attempt` | Phase 3: Starting title-only search | `crossref_title_only_attempt` |
| `{provider}_title_only_success` | Phase 3: Title match found | `crossref_title_only_success` |
| `{provider}_title_only_not_found` | Phase 3: No match | `crossref_title_only_not_found` |

### Example Implementation

```python
from bioetl.infrastructure.adapters.common import BaseTitleFallbackHandler

class CrossRefTitleFallback(BaseTitleFallbackHandler):
    def __init__(
        self,
        http_client: UnifiedHTTPClient,
        logger: LoggerPort,
        metrics: MetricsPort,
    ):
        super().__init__(logger, provider_prefix="crossref")
        self._http = http_client
        self._metrics = metrics

    async def search_by_title(self, title: str) -> dict[str, Any] | None:
        """Search CrossRef by title."""
        response = await self._http.get(
            "/works",
            params={"query.title": title, "rows": 1},
        )

        if not response.json().get("message", {}).get("items"):
            return None

        return response.json()["message"]["items"][0]
```

**Related ADR:** [ADR-030: Publication Pagination Strategy](../../02-architecture/decisions/ADR-030-publication-pagination-strategy.md)

---

## Title Normalization Utilities

### normalize_title()

**Purpose:** Normalize publication titles for fuzzy matching.

**Transformations:**
- Convert to lowercase
- Remove punctuation (except hyphens)
- Collapse multiple spaces
- Strip leading/trailing whitespace

```python
from bioetl.infrastructure.adapters.common import normalize_title

title = "The Quick Brown Fox: A Study"
normalized = normalize_title(title)
# Returns: "the quick brown fox a study"
```

### titles_match()

**Purpose:** Fuzzy title comparison using Levenshtein distance.

**Algorithm:** Normalized Levenshtein ratio with configurable threshold.

```python
from bioetl.infrastructure.adapters.common import titles_match

title1 = "The Quick Brown Fox"
title2 = "Quick Brown Fox"

match = titles_match(title1, title2, threshold=0.85)
# Returns: True (similarity >= 85%)
```

**Default threshold:** 0.85 (85% similarity required)

---

## Architecture Integration

### Layer Placement

```
infrastructure/adapters/
├── common/               # ← Shared utilities
│   ├── api_request_collector.py
│   ├── base_title_fallback.py
│   └── title_matching.py
├── chembl/               # Uses APIRequestCollector
├── pubmed/               # Uses BaseTitleFallbackHandler + title_matching
├── crossref/             # Uses BaseTitleFallbackHandler + title_matching
└── openalex/             # Uses BaseTitleFallbackHandler + title_matching
```

### Dependency Rules

**MUST:**
- All adapters **MUST** use `APIRequestCollector` for Bronze metadata
- Publication adapters **SHOULD** extend `BaseTitleFallbackHandler` when title fallback is needed
- Adapters **MUST NOT** import from other adapter modules (only from `common/`)

**Related:**
- [ADR-005: Composition Layer Separation](../../02-architecture/decisions/ADR-005-composition-layer-separation.md)
- [ARCH-001: Import Matrix](../../../00-project/RULES.md#arch-001-import-matrix)

---

## Testing

All common utilities have comprehensive unit tests:

```bash
# Test APIRequestCollector
pytest tests/unit/infrastructure/adapters/common/test_api_request_collector.py

# Test title matching
pytest tests/unit/infrastructure/adapters/common/test_title_matching.py

# Test title fallback base class
pytest tests/unit/infrastructure/adapters/common/test_base_title_fallback.py
```

**Test coverage:** 95%+ for all common utilities

---

## See Also

- [Infrastructure Layer Overview](infrastructure.md)
- [ADR-029: Output Metadata Unification](../../02-architecture/decisions/ADR-029-output-metadata-unification.md)
- [ADR-030: Publication Pagination Strategy](../../02-architecture/decisions/ADR-030-publication-pagination-strategy.md)
- [ADR-032: Unified HTTP Client Pattern](../../02-architecture/decisions/ADR-032-unified-http-client.md)
