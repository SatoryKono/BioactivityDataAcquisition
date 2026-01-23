# ADR-009: PaginatedFetcherMixin Design

**Status:** Accepted
**Date:** 2025-12-22
**Decision makers:** @BioETL-Team

## Context

All data source adapters (ChEMBL, PubChem, UniProt) implement pagination, but each API uses different mechanisms (offset-based, cursor-based, page tokens). The pagination loop logic was duplicated across adapters, leading to inconsistent error handling and limit enforcement. A unified abstraction was needed.

## The Decision

We have implemented **`PaginatedFetcherMixin`** in `infrastructure/adapters/http/pagination.py`:

1. **Mixin pattern**: Composable with any HTTP adapter
2. **Callback-based**: Adapter provides fetch function, mixin handles loop
3. **Generator-based**: Yields items lazily via `AsyncIterator`
4. **Global limit support**: Stops across page boundaries

## Design

```python
class PaginatedFetcherMixin:
    async def paginated_fetch(
        self,
        fetch_func: Callable[[cursor, fetched], Awaitable[tuple[list[T], cursor]]],
        limit: int | None = None,
        initial_cursor: Any | None = None,
    ) -> AsyncIterator[T]:
        ...
```

### Fetch Function Contract

```python
async def fetch_page(cursor: Any | None, fetched: int) -> tuple[list[T], Any | None]:
    """
    Args:
        cursor: Current position (offset, page token, etc.)
        fetched: Items already yielded (for adaptive page sizing)

    Returns:
        (items, next_cursor) - next_cursor is None when no more pages
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
        items = await self._fetch_page(offset)
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
        items, cursor = await self._fetch_page(cursor)
        # ... same loop logic
```

After (shared loop logic):
```python
class ChEMBLAdapter(PaginatedFetcherMixin):
    async def fetch(self, watermark, limit):
        async for item in self.paginated_fetch(self._fetch_page, limit):
            yield item
```

### 2. Consistent Limit Enforcement

The mixin guarantees exact limit enforcement across page boundaries:

```python
# If limit=100 and page_size=30:
# Page 1: items 1-30 (30 yielded)
# Page 2: items 31-60 (60 yielded)
# Page 3: items 61-90 (90 yielded)
# Page 4: items 91-100 (100 yielded, STOP before 101)
```

Without the mixin, adapters might fetch full pages past the limit, wasting API calls.

### 3. Adaptive Page Sizing Support

The `fetched` parameter enables adapters to adjust page size:

```python
async def _fetch_page(self, cursor, fetched):
    remaining = self.total_limit - fetched if self.total_limit else None
    page_size = min(self.default_page_size, remaining or self.default_page_size)
    return await self._api_call(page_size=page_size, cursor=cursor)
```

### 4. Generator-Based Memory Efficiency

Using `AsyncIterator` instead of collecting all items:
- Constant memory regardless of dataset size
- Enables streaming to Bronze layer
- Natural backpressure via async iteration

## Protocol Definition

```python
class PageFetcher(Protocol[T]):
    """Protocol for fetch functions compatible with paginated_fetch."""

    async def __call__(
        self, cursor: Any | None, fetched: int
    ) -> tuple[list[T], Any | None]:
        ...
```

This protocol enables type checking for fetch functions without requiring inheritance.

## Pagination Patterns Supported

| API | Cursor Type | Example |
|-----|-------------|---------|
| ChEMBL | Offset (int) | `offset=1000` |
| PubChem | Page token (str) | `ListKey=xyz123` |
| UniProt | URL (str) | `https://api.../next` |
| Generic | Any | Adapter-defined |

The mixin is agnostic to cursor type—it just passes through.

## Alternatives Considered

### 1. Base Class with Abstract Methods

```python
class PaginatedAdapter(ABC):
    @abstractmethod
    async def fetch_page(self, cursor) -> tuple[list, Any]: ...
```

Rejected because:
- Forces single inheritance
- Doesn't compose well with other mixins
- Tighter coupling than needed

### 2. Decorator Pattern

```python
@paginated(limit_param="limit")
async def fetch(self, watermark, limit):
    return await self._fetch_page(...)
```

Rejected because:
- Magic behavior hidden in decorator
- Harder to debug
- Less explicit control flow

### 3. Utility Function (not mixin)

```python
async def paginated_fetch(fetcher, fetch_func, limit):
    ...
```

Considered but mixin preferred because:
- Cleaner API for adapters (`self.paginated_fetch(...)`)
- Can access adapter state if needed
- More idiomatic for class-based adapters

## Consequences

### Positive
- Single implementation of pagination logic
- Consistent limit enforcement
- Type-safe via Protocol
- Memory-efficient streaming
- Easy to test (mock fetch_func)

### Negative
- **Mixin complexity**: Mixins can make class hierarchies harder to understand. Mitigated by simple, focused interface.
- **Callback overhead**: Slight indirection vs inline loop. Negligible compared to network I/O.

## Usage Example

```python
from bioetl.infrastructure.adapters.http.pagination import PaginatedFetcherMixin

class ChEMBLActivityAdapter(PaginatedFetcherMixin):
    async def fetch(
        self, watermark: Watermark | None, limit: int | None
    ) -> AsyncIterator[dict]:
        async def fetch_page(offset: int | None, fetched: int):
            page = await self.client.get(
                "/activity",
                params={"offset": offset or 0, "limit": self.page_size}
            )
            items = page.json()["activities"]
            next_offset = (offset or 0) + len(items) if items else None
            return items, next_offset

        async for item in self.paginated_fetch(fetch_page, limit=limit):
            yield item
```

## Related ADRs

- ADR-007: Circuit Breaker (wraps fetch calls)
- ADR-008: Graceful Shutdown (can interrupt pagination loop)
