"""Publication and adapter bounded vocabularies for Prometheus labels."""

from __future__ import annotations

import re

__all__ = [
    "_ALLOWED_ADAPTER_OPERATION_LABELS",
    "_ALLOWED_OBSERVABILITY_COMPONENT_LABELS",
    "_ALLOWED_OBSERVABILITY_MODE_LABELS",
    "_ALLOWED_PUBLICATION_STATUS_LABELS",
    "_ALLOWED_PUBLICATION_TARGET_LABELS",
    "_ALLOWED_PUBLICATION_VOCAB_FIELD_LABELS",
    "_ALLOWED_PUBLICATION_VOCAB_HANDLING_LABELS",
    "_ALLOWED_PUBLICATION_VOCAB_PROVIDER_LABELS",
    "_DYNAMIC_ENDPOINT_SEGMENT_PATTERNS",
    "_SOURCE_FILE_CLASS_BY_SUFFIX",
]

_ALLOWED_PUBLICATION_TARGET_LABELS = frozenset(
    {"pushgateway", "metrics_server", "other"}
)
_ALLOWED_PUBLICATION_STATUS_LABELS = frozenset(
    {"success", "failed", "skipped", "disabled", "other"}
)
_ALLOWED_PUBLICATION_VOCAB_PROVIDER_LABELS = frozenset(
    {"crossref", "openalex", "pubmed", "semanticscholar", "other"}
)
_ALLOWED_PUBLICATION_VOCAB_FIELD_LABELS = frozenset(
    {
        "publication_type",
        "type_crossref",
        "publication_types",
        "publication_status",
        "other",
    }
)
_ALLOWED_PUBLICATION_VOCAB_HANDLING_LABELS = frozenset(
    {"preserved_unknown", "collapsed_to_none", "other"}
)
_ALLOWED_OBSERVABILITY_COMPONENT_LABELS = frozenset(
    {"logger", "metrics", "tracing", "audit", "dq_monitor", "other"}
)
_ALLOWED_OBSERVABILITY_MODE_LABELS = frozenset({"active", "noop", "disabled", "other"})
_ALLOWED_ADAPTER_OPERATION_LABELS = frozenset(
    {
        "doi_resolution",
        "fallback_flow",
        "fetch",
        "fetch_batch",
        "fetch_filtered_with_fallback",
        "health_check",
        "search",
        "title_fallback",
        "other",
    }
)

_DYNAMIC_ENDPOINT_SEGMENT_PATTERNS = (
    re.compile(r"^\d+$"),
    re.compile(
        r"^[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}$",
        re.IGNORECASE,
    ),
    re.compile(r"^[\da-f]{16,}$", re.IGNORECASE),
)
_SOURCE_FILE_CLASS_BY_SUFFIX = {
    ".csv": "csv_file",
    ".tsv": "tsv_file",
    ".txt": "text_file",
    ".json": "json_file",
    ".jsonl": "jsonl_file",
    ".yaml": "yaml_file",
    ".yml": "yaml_file",
    ".parquet": "parquet_file",
    ".arrow": "arrow_file",
    ".xlsx": "spreadsheet_file",
    ".xls": "spreadsheet_file",
}
