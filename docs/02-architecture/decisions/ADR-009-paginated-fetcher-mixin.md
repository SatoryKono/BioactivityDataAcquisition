______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-009: PaginatedFetcherMixin Design

**Date:** 2025-12-22
**Status:** Accepted
**Decision makers:** @BioETL-Team

## Context

All data source adapters (ChEMBL, PubChem, UniProt) implement pagination, but each API uses different mechanisms (offset-based, cursor-based, page tokens). The pagination loop logic was duplicated across adapters, leading to inconsistent error handling and limit enforcement. A unified abstraction was needed.

## Decision

We have implemented **`PaginatedFetcherMixin`** in `infrastructure/adapters/http/pagination.py`:

1. **Mixin pattern**: Composable with any HTTP adapter
1. **Callback-based**: Adapter provides fetch function, mixin handles loop
1. **Generator-based**: Yields items lazily via `AsyncIterator`
1. **Global limit support**: Stops across page boundaries

## Design

```python
class PaginatedFetcherMixin:
    async def paginated-fetch(
        self,
        fetch-func: Callable[[cursor, fetched], Awaitable[tuple[list[T], cursor]]],
        limit: int | None = None,
        initial-cursor: Any | None = None,
    ) -> AsyncIterator[T]:
        ...
```

### Fetch Function Contract

```python
async def fetch-page(cursor: Any | None, fetched: int) -> tuple[list[T], Any | None]:
    """
    Args:
        cursor: Current position (offset, page token, etc.)
        fetched: Items already yielded (for adaptive page sizing)

    Returns:
        (items, next-cursor) - next-cursor is None when no more pages
    """
```

## Justification

### 1. DRY Principle

Before (duplicated in each adapter):

```python
# ChEMBL adapter
async def fetch(self, watermark, limit):
    offset = 0
    while True:
        items = await self.-fetch-page(offset)
        if not items:
            break
        for item in items:
            yield item
            if limit and yielded >= limit:
                return
        offset += len(items)

# PubChem adapter (same logic, different cursor)
async def fetch(self, watermark, limit):
    cursor = None
    while True:
        items, cursor = await self.-fetch-page(cursor)
        # ... same loop logic
```

After (shared loop logic):

```python
class ChEMBLAdapter(PaginatedFetcherMixin):
    async def fetch(self, watermark, limit):
        async for item in self.paginated-fetch(self.-fetch-page, limit):
            yield item
```

### 2. Consistent Limit Enforcement

The mixin guarantees exact limit enforcement across page boundaries:

```python
# If limit=100 and page-size=30:
# Page 1: items 1-30 (30 yielded)
# Page 2: items 31-60 (60 yielded)
# Page 3: items 61-90 (90 yielded)
# Page 4: items 91-100 (100 yielded, STOP before 101)
```

Without the mixin, adapters might fetch full pages past the limit, wasting API calls.

### 3. Adaptive Page Sizing Support

The `fetched` parameter enables adapters to adjust page size:

```python
async def -fetch-page(self, cursor, fetched):
    remaining = self.total-limit - fetched if self.total-limit else None
    page-size = min(self.default-page-size, remaining or self.default-page-size)
    return await self.-api-call(page-size=page-size, cursor=cursor)
```

### 4. Generator-Based Memory Efficiency

Using `AsyncIterator` instead of collecting all items:

- Constant memory regardless of dataset size
- Enables streaming to Bronze layer
- Natural backpressure via async iteration

## Protocol Definition

```python
class PageFetcher(Protocol[T]):
    """Protocol for fetch functions compatible with paginated-fetch."""

    async def --call--(
        self, cursor: Any | None, fetched: int
    ) -> tuple[list[T], Any | None]:
        ...
```

This protocol enables type checking for fetch functions without requiring inheritance.

## Pagination Patterns Supported

| API     | Cursor Type      | Example               |
| ------- | ---------------- | --------------------- |
| ChEMBL  | Offset (int)     | `offset=1000`         |
| PubChem | Page token (str) | `ListKey=xyz123`      |
| UniProt | URL (str)        | `https://api.../next` |
| Generic | Any              | Adapter-defined       |

The mixin is agnostic to cursor type—it just passes through.

## Alternatives Considered

### 1. Base Class with Abstract Methods

```python
class PaginatedAdapter(ABC):
    @abstractmethod
    async def fetch-page(self, cursor) -> tuple[list, Any]: ...
```

Rejected because:

- Forces single inheritance
- Doesn't compose well with other mixins
- Tighter coupling than needed

### 2. Decorator Pattern

```python
@paginated(limit-param="limit")
async def fetch(self, watermark, limit):
    return await self.-fetch-page(...)
```

Rejected because:

- Magic behavior hidden in decorator
- Harder to debug
- Less explicit control flow

### 3. Utility Function (not mixin)

```python
async def paginated-fetch(fetcher, fetch-func, limit):
    ...
```

Considered but mixin preferred because:

- Cleaner API for adapters (`self.paginated-fetch(...)`)
- Can access adapter state if needed
- More idiomatic for class-based adapters

## Consequences

### Positive

- Single implementation of pagination logic
- Consistent limit enforcement
- Type-safe via Protocol
- Memory-efficient streaming
- Easy to test (mock fetch-func)

### Negative

- **Mixin complexity**: Mixins can make class hierarchies harder to understand. Mitigated by simple, focused interface.
- **Callback overhead**: Slight indirection vs inline loop. Negligible compared to network I/O.

## Usage Example

```python
from bioetl.infrastructure.adapters.http.pagination import PaginatedFetcherMixin


class UniProtAdapter(PaginatedFetcherMixin):
    async def fetch(
        self, watermark: Watermark | None, limit: int | None
    ) -> AsyncIterator[dict]:
        async def fetch_page(offset: int | None, fetched: int):
            page = await self.client.get(
                "/uniprotkb/search", params={"cursor": offset, "size": self.page_size}
            )
            items = page.json()["results"]
            next_cursor = page.headers.get("x-next-cursor")
            return items, next_cursor

        async for item in self.paginated_fetch(fetch_page, limit=limit):
            yield item
```

> **Note:** ChEMBL uses a specialized `ChemblFetchPagingMixin` instead of the generic `PaginatedFetcherMixin`.

## References

- ADR-007: Circuit Breaker (wraps fetch calls)
- ADR-008: Graceful Shutdown (can interrupt pagination loop)
- ADR-030: Full Scan Loading Strategy (uses pagination for complete data loads)
- ADR-031: Loading Strategy Formalization (orchestrates paginated fetches across providers)

## Compliance

| Control      | Requirement                                                                | Status | Evidence                             |
| ------------ | -------------------------------------------------------------------------- | ------ | ------------------------------------ |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-009-paginated-fetcher-mixin.md` |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted`                           |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                     |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria` |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                         |

## Rollout

- Rollout steps MUST be sequenced before broad adoption.
- Documentation, configuration, and test surfaces SHOULD be updated in the same change set when the decision is implemented.
- Breaking or migration-sensitive adoption SHOULD include an explicit transition window.

## Rollback

- Rollback MUST identify the last known-good behavior or artifact set.
- If the decision changes contracts, configuration, or storage semantics, rollback SHOULD include data and compatibility checks.
- Rollback triggers SHOULD be observable through tests, runtime signals, or regression symptoms.

## Verification

- Verify architecture, configuration, and documentation changes against the current codebase.
- Run the relevant tests, validators, or parity checks before considering the ADR fully adopted.
- Confirm downstream docs and contracts reflect the same decision boundaries.

## Acceptance Criteria

- [ ] The decision is documented with current status, date, and owner metadata.
- [ ] The implementation path or adoption boundary is testable and linked from the ADR.
- [ ] Supersession or migration impact is documented when the decision changes an earlier posture.
- [ ] Related docs, contracts, and operational guidance are aligned with this ADR.
