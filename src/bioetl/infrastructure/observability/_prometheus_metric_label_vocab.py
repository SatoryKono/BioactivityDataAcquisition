"""Reviewed bounded vocabularies for Prometheus metric label normalizers."""

from __future__ import annotations

import re

_ALLOWED_REASON_LABELS = frozenset(
    {
        "cross_validation",
        "filtered_out_silver",
        "data_quality",
        "schema_validation",
        "transform_error",
        "validation_error",
        "other",
    }
)
_ALLOWED_FILTER_SOURCE_KIND_LABELS = frozenset(
    {
        "csv_single_column",
        "csv_multi_column",
        "direct_ids",
        "direct_multi_ids",
        "other",
    }
)
_ALLOWED_SILVER_FILTER_REASON_CODE_LABELS = frozenset(
    {
        "required_field_missing",
        "exclude_if_present",
        "column_filter_mismatch",
        "range_filter_mismatch",
        "list_length_filter_mismatch",
        "list_contains_filter_mismatch",
        "required_field_type_mismatch",
        "optional_nonnullable_field_type_mismatch",
        "nullable_field_type_coerced_to_null",
        "other",
    }
)
_ALLOWED_SILVER_FILTER_RULE_TYPE_LABELS = frozenset(
    {
        "required_fields",
        "exclude_if_present",
        "column_filters",
        "range_filters",
        "list_length_filters",
        "list_contains_filters",
        "structural_policy",
        "other",
    }
)
_ALLOWED_SILVER_FILTER_FIELD_LABELS = frozenset(
    {
        "_state",
        "accession",
        "activity_id",
        "assay_description",
        "assay_id",
        "assay_param_id",
        "assay_type",
        "assay_type_description",
        "bao_endpoint",
        "bao_format",
        "bao_label",
        "canonical_smiles",
        "cell_id",
        "cell_name",
        "class_level",
        "component_id",
        "confidence_score",
        "data_validity_comment",
        "description",
        "doc_1",
        "doc_2",
        "doi",
        "inorganic_flag",
        "journal",
        "mapping_status",
        "molecule_id",
        "molecule_type",
        "openalex_id",
        "organism",
        "organism_scientific",
        "other",
        "paper_id",
        "pchembl_value",
        "pmid",
        "potential_duplicate",
        "pref_name",
        "protein_class_id",
        "publication_id",
        "publication_type",
        "publication_year",
        "record_id",
        "relation",
        "relationship_type",
        "sim_id",
        "src_id",
        "standard_flag",
        "standard_relation",
        "standard_type",
        "standard_units",
        "standard_value",
        "structure_type",
        "subcellular_fraction",
        "target_id",
        "target_organism",
        "target_taxonomy_id",
        "target_type",
        "term",
        "term_type",
        "tissue_id",
        "title",
        "type",
        "units",
        "uo_units",
        "value",
    }
)
_ALLOWED_STAGE_LABELS = frozenset(
    {
        "validation",
        "threshold",
        "transform",
        "bronze",
        "silver",
        "gold",
        "postrun",
        "other",
    }
)
_ALLOWED_RUNTIME_STAGE_LABELS = frozenset(
    {
        "pipeline",
        "startup",
        "preflight",
        "lifecycle_clear",
        "execution",
        "postrun",
        "cleanup",
        "bronze",
        "silver",
        "gold",
        "filtered_out",
        "quarantined",
        "transform",
        "validation",
        "write",
        "checkpoint",
        "extract",
        "load",
        "other",
    }
)
_ALLOWED_FLOW_STAGE_LABELS = frozenset(
    {
        "fetched",
        "bronze",
        "silver",
        "gold",
        "filtered_out",
        "quarantined",
        "other",
    }
)
_ALLOWED_RECORD_FLOW_INVARIANT_LABELS = frozenset(
    {
        "fetched_equals_bronze",
        "bronze_partitioned",
        "silver_gold_monotonic",
        "other",
    }
)
_ALLOWED_RECORD_FLOW_INVARIANT_STATUS_LABELS = frozenset(
    {"passed", "violated", "unknown", "other"}
)
_ALLOWED_STAGE_MODEL_STAGE_LABELS = frozenset(
    {
        "input",
        "ingestion",
        "transform",
        "validation",
        "storage",
        "output",
        "bronze",
        "silver",
        "gold",
        "other",
    }
)
_ALLOWED_STAGE_MODEL_OUTCOME_LABELS = frozenset(
    {
        "fetched",
        "bronze_written",
        "records",
        "silver_ready",
        "valid",
        "gold_ready",
        "filtered_out",
        "evaluated",
        "quarantined",
        "skipped",
        "deduplicated",
        "silver_written",
        "gold_written",
        "written",
        "excluded_by_contract",
        "ready",
        "other",
    }
)
_ALLOWED_BATCH_LIFECYCLE_EVENT_LABELS = frozenset(
    {"created", "written", "failed", "other"}
)
_ALLOWED_COMPOSITE_PHASE_RECORD_OUTCOME_LABELS = frozenset(
    {"extracted", "silver", "input", "enriched", "merged", "fully_enriched", "other"}
)
_ALLOWED_COMPOSITE_PHASE_ERROR_KIND_LABELS = frozenset(
    {"failed", "timeout", "record_error", "other"}
)
_ALLOWED_COMPOSITE_PHASE_LOSS_KIND_LABELS = frozenset(
    {"unwritten", "not_found", "partially_enriched", "quarantined", "other"}
)
_ALLOWED_COMPOSITE_PHASE_RETRY_KIND_LABELS = frozenset({"resume", "other"})
_ALLOWED_PHASE_LABELS = frozenset(
    {
        "startup",
        "preflight",
        "lifecycle_clear",
        "execution",
        "postrun",
        "cleanup",
        "preflight_validation",
        "seed",
        "dependencies",
        "enrichment",
        "merge",
        "cross_validation",
        "gold_write",
        "other",
    }
)
_ALLOWED_POSTRUN_PHASE_LABELS = frozenset(
    {
        "dq_evaluation",
        "dq_reports",
        "compaction",
        "vacuum",
        "final_metadata",
        "other",
    }
)
_ALLOWED_SEVERITY_LABELS = frozenset(
    {"soft_fail", "hard_fail", "warning", "error", "other"}
)
_ALLOWED_DQ_DISPOSITION_LABELS = frozenset(
    {"pass", "warn", "quarantine", "skip", "fail", "other"}
)
_ALLOWED_TERMINAL_STATUS_LABELS = frozenset({"success", "failed", "shutdown", "other"})
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
_ALLOWED_DQ_CHECK_TYPE_LABELS = frozenset(
    {
        "anomaly_detection",
        "business_rules",
        "completeness",
        "content_hash_integrity",
        "data_freshness",
        "deduplication_stats",
        "encoding_validation",
        "file_integrity",
        "key_nullability",
        "null_rate",
        "raw_field_presence",
        "record_count",
        "referential_integrity",
        "schema_drift",
        "schema_snapshot",
        "scd_integrity",
        "statistical_profile",
        "type_conformance",
        "uniqueness",
        "value_distribution",
        "other",
    }
)
_ALLOWED_STRUCTURAL_ACTION_LABELS = frozenset(
    {
        "presence_quarantine",
        "required_type_quarantine",
        "nullable_type_to_null",
        "optional_nonnullable_quarantine",
        "other",
    }
)
_ALLOWED_STRUCTURAL_COMPARISON_LABELS = frozenset(
    {
        "structural_pass_silver_filter_pass",
        "structural_pass_silver_filter_reject",
        "structural_reject_silver_filter_pass",
        "structural_reject_silver_filter_reject",
        "other",
    }
)
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
