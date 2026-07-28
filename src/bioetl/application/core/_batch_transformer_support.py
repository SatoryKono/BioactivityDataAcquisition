"""Private helpers for BatchTransformer construction paths."""

from __future__ import annotations

from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.application.core.record_processor_config import RecordProcessorConfig

def build_default_normalization_processor(
    config: RecordProcessorConfig,
) -> RecordNormalizationProcessor | None:
    """Build the default normalization stage from record-processor config."""
    if not config.normalization_enabled:
        return None
    return RecordNormalizationProcessor(
        provider=config.provider,
        entity_type=config.entity_type,
        rule_set=config.normalization_rule_set,
        allow_compatibility_fallback=config.allow_compatibility_fallback,
        content_hash_policy_authoritative=config.content_hash_policy_authoritative,
        content_hash_include_fields=config.content_hash_include_fields,
        content_hash_exclude_fields=config.content_hash_exclude_fields,
        content_hash_policy_by_version=config.content_hash_policy_by_version,
    )

def merge_named_keys(
    base: dict[str, object] | None,
    legacy: dict[str, object],
    keys: tuple[str, ...],
) -> dict[str, object]:
    """Copy base and overlay non-None legacy values for the given keys."""
    resolved = dict(base or {})
    for key in keys:
        value = legacy.pop(key, None)
        if value is not None:
            resolved[key] = value
    return resolved

def resolve_transformer_bags(
    runtime: dict[str, object] | None,
    callbacks: dict[str, object] | None,
    legacy: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    """Merge runtime/callback dicts with transitional kwargs; reject unknowns."""
    resolved_runtime = merge_named_keys(
        runtime,
        legacy,
        ("error_classifier", "quarantine_manager", "batch_metrics"),
    )
    resolved_callbacks = merge_named_keys(
        callbacks,
        legacy,
        ("transform_callback", "gold_filter_callback", "gold_transform_callback"),
    )
    if legacy:
        raise TypeError(
            "BatchTransformer() got unexpected keyword argument(s): "
            + ", ".join(sorted(str(k) for k in legacy))
        )
    return resolved_runtime, resolved_callbacks

def begin_batch_metrics_if_present(batch_metrics: object) -> None:
    """Invoke optional BatchMetrics begin_batch hook when available."""
    begin_batch = getattr(batch_metrics, "begin_batch", None)
    if callable(begin_batch):
        begin_batch()
