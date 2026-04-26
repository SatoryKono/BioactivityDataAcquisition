# Extended Ports

*Status: Active | Class: internal | Last Updated: 2026-04-24*

## Overview

This document describes extended ports that provide additional functionality beyond the base interfaces. These are considered part of the internal/extended material.

## FilterableDataSourcePort

### Purpose

`FilterableDataSourcePort` extends `DataSourcePort` with server-side filtering capabilities.

### Interface

```python
class FilterableDataSourcePort(DataSourcePort, Protocol):
    """Extended port with server-side filtering capabilities."""

    async def fetch_filtered(
        self,
        filters: list[FilterSpec],
        limit: int | None = None
    ) -> list[dict]:
        """Fetch records with server-side filtering."""
        ...

    async def fetch_multi_filtered(
        self,
        filter_groups: list[list[FilterSpec]],
        limit: int | None = None
    ) -> list[dict]:
        """Fetch records with multi-group filtering (OR between groups, AND within group)."""
        ...

    async def fetch_filtered_with_fallback(
        self,
        filters: list[FilterSpec],
        limit: int | None = None
    ) -> list[dict]:
        """Fetch with filtering, falling back to client-side filtering if server-side fails."""
        ...
```

### Implementation Notes

1. **Fallback Behavior**: The `fetch_filtered_with_fallback` method provides resilience by falling back to client-side filtering when server-side filtering is unavailable.

2. **Filter Specification**: Uses `FilterSpec` objects to define filter criteria:
   ```python
   @dataclass
   class FilterSpec:
       field: str
       operator: str  # "eq", "neq", "gt", "lt", "contains", etc.
       value: Any
       case_sensitive: bool = False
   ```

3. **Performance**: Server-side filtering is preferred for performance, but client-side fallback ensures functionality.

### Usage Pattern

```python
# Preferred: Use server-side filtering when available
records = await data_source.fetch_filtered([
    FilterSpec(field="status", operator="eq", value="active"),
    FilterSpec(field="type", operator="eq", value="journal-article")
])

# Fallback: Use when server-side filtering might fail
records = await data_source.fetch_filtered_with_fallback([
    FilterSpec(field="doi", operator="contains", value="10.1038")
])
```

## Implementation Status

### Current Implementations

| Provider | Base Port | Extended Port |
|----------|-----------|---------------|
| ChEMBL | ✓ | ✓ |
| CrossRef | ✓ | ✓ |
| OpenAlex | ✓ | ✓ |
| PubChem | ✓ | ✓ |
| PubMed | ✓ | ✓ |
| UniProt | ✓ | ✓ |

### Implementation Notes by Provider

#### ChEMBL
- Full server-side filtering support
- Supports complex multi-field queries
- Fallback to client-side filtering for unsupported operators

#### CrossRef
- Server-side filtering for DOI and publication date
- Client-side fallback for other fields
- Rate-limited filtering operations

#### OpenAlex
- Comprehensive server-side filtering
- Supports nested field filtering
- Fallback for complex boolean queries

## Related Documentation

- [Data Source Ports API Reference](../api/domain.md#data-source-ports)
- [Provider-Specific Implementations](../providers/README.md)
- [Internal/Extended Index](index.md)
