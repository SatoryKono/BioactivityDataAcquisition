# Internal Type Mappings

*Status: Active | Class: internal | Last Updated: 2026-04-24*

## Overview

This document describes the internal type mappings used across different providers. These mappings standardize provider-specific types to a common internal representation.

## CrossRef Type Mappings

### Mapping Table

| CrossRef Type         | Internal Type | Description                    |
| --------------------- | ------------- | ------------------------------ |
| `journal-article`     | `PUBLICATION` | Standard journal article       |
| `posted-content`      | `PREPRINT`    | Preprint or working paper      |
| `proceedings-article` | `PUBLICATION` | Conference proceedings article |
| `book-chapter`        | `PUBLICATION` | Book chapter                   |
| `dissertation`        | `PUBLICATION` | Thesis or dissertation         |
| `report`              | `REPORT`      | Technical or research report   |
| `dataset`             | `DATASET`     | Dataset publication            |
| `other`               | `OTHER`       | Other publication types        |

### Implementation Notes

1. **Normalization**: CrossRef types are normalized to uppercase internal types
1. **Fallback**: Unknown types map to `OTHER`
1. **Usage**: Used in publication enrichment pipelines

## OpenAlex Type Mappings

### Mapping Table

| OpenAlex Type                | Internal Type | Description         |
| ---------------------------- | ------------- | ------------------- |
| `article`, `journal-article` | `PUBLICATION` | Journal articles    |
| `book-chapter`, `book`       | `PUBLICATION` | Books and chapters  |
| `proceedings-article`        | `PUBLICATION` | Conference articles |
| `preprint`, `posted-content` | `PREPRINT`    | Preprints           |
| `dataset`                    | `DATASET`     | Datasets            |
| `dissertation`, `thesis`     | `PUBLICATION` | Theses              |
| `report`                     | `REPORT`      | Reports             |
| `other`                      | `OTHER`       | Other types         |

### Implementation Notes

1. **Multiple Mappings**: Some OpenAlex types map to the same internal type
1. **Consistency**: Designed to be consistent with CrossRef mappings where possible
1. **Extensibility**: New OpenAlex types can be added without breaking existing mappings

## PubMed Type Mappings

### Mapping Table

| PubMed Type       | Internal Type | Description                |
| ----------------- | ------------- | -------------------------- |
| `Journal Article` | `PUBLICATION` | Standard journal article   |
| `Review`          | `PUBLICATION` | Review article             |
| `Clinical Trial`  | `PUBLICATION` | Clinical trial publication |
| `Meta-Analysis`   | `PUBLICATION` | Meta-analysis              |
| `Case Reports`    | `PUBLICATION` | Case report                |
| `Editorial`       | `PUBLICATION` | Editorial                  |
| `Letter`          | `PUBLICATION` | Letter to editor           |
| `Other`           | `OTHER`       | Other publication types    |

## Implementation Pattern

### Type Mapping Function

```python
def map_crossref_type(crossref_type: str) -> str:
    """Map CrossRef type to internal type."""
    mapping = {
        "journal-article": "PUBLICATION",
        "posted-content": "PREPRINT",
        "proceedings-article": "PUBLICATION",
        "book-chapter": "PUBLICATION",
        "dissertation": "PUBLICATION",
        "report": "REPORT",
        "dataset": "DATASET",
        # Default fallback
        "other": "OTHER",
    }
    return mapping.get(crossref_type.lower(), "OTHER")
```

### Usage in Pipelines

```python
# In publication transformer
internal_type = map_crossref_type(record["type"])
standardized_record = {
    **record,
    "internal_type": internal_type,
    "type_normalized": True,
}
```

## Related Documentation

- [CrossRef Publication Pipeline](../providers/crossref/publication.md)
- [OpenAlex Publication Pipeline](../providers/openalex/publication.md)
- [PubMed Publication Pipeline](../providers/pubmed/publication.md)
- [Internal/Extended Index](index.md)
