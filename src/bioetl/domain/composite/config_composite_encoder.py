"""Pure serialization of composite configuration domain models."""

from __future__ import annotations

from bioetl.domain.composite.config_composite_protocols import (
    CompositeConfigProtocol,
    _AggregationConfigProtocol,
    _AggregationFieldProtocol,
    _ColumnGroupProtocol,
    _CrossValidationConfigProtocol,
    _DependencyConfigProtocol,
    _DQConfigProtocol,
    _DQOverrideProtocol,
    _EnricherConfigProtocol,
    _EnricherPairingProtocol,
    _ExecutionConfigProtocol,
    _FieldComparisonProtocol,
    _LineageConfigProtocol,
    _MergeConfigProtocol,
    _SeedConfigProtocol,
)

__all__ = ["composite_to_dict"]


def _dependency_entry(dependency: _DependencyConfigProtocol) -> dict[str, object]:
    entry: dict[str, object] = {
        "pipeline": dependency.pipeline,
        "join_keys": list(dependency.join_keys),
        "required": dependency.required,
        "timeout_seconds": dependency.timeout_seconds,
        "silver_table": dependency.silver_table,
        "key_source": dependency.key_source,
        "filter_field": dependency.filter_field,
        "key_filter": dependency.key_filter,
    }
    filter_fields = getattr(dependency, "filter_fields", None)
    if filter_fields:
        entry["filter_fields"] = list(filter_fields)
    return entry


def _aggregation_field_entry(field: _AggregationFieldProtocol) -> dict[str, object]:
    return {
        "source_field": field.source_field,
        "agg_function": field.agg_function.value,
        "filter_condition": field.filter_condition,
        "output_field": field.output_field,
    }


def _aggregation_to_dict(aggregation: _AggregationConfigProtocol) -> dict[str, object]:
    return {
        "group_by": aggregation.group_by,
        "order_by": list(aggregation.order_by),
        "fields": [_aggregation_field_entry(field) for field in aggregation.fields],
    }


def _enricher_entry(enricher: _EnricherConfigProtocol) -> dict[str, object]:
    entry: dict[str, object] = {
        "pipeline": enricher.pipeline,
        "join_keys": list(enricher.join_keys),
        "required": enricher.required,
        "timeout_seconds": enricher.timeout_seconds,
        "filter_condition": enricher.filter_condition,
        "silver_table": enricher.silver_table,
        "limit": enricher.limit,
        "fallback_strategy": enricher.fallback_strategy.value,
        "cardinality": enricher.cardinality.value,
    }
    aggregation = getattr(enricher, "aggregation", None)
    if aggregation is not None:
        entry["aggregation"] = _aggregation_to_dict(aggregation)
    return entry


def _seed_to_dict(seed: _SeedConfigProtocol) -> dict[str, object]:
    return {
        "pipeline": seed.pipeline,
        "output_keys": list(seed.output_keys),
        "silver_table": seed.silver_table,
        "limit": seed.limit,
    }


def _column_group_entry(group: _ColumnGroupProtocol) -> dict[str, object]:
    return {
        "name": group.name,
        "fields": list(group.fields),
        "pattern": group.pattern,
        "provider_order": list(group.provider_order),
    }


def _merge_to_dict(merge: _MergeConfigProtocol) -> dict[str, object]:
    return {
        "strategy": merge.strategy.value,
        "conflict_resolution": merge.conflict_resolution.value,
        "output_silver_path": merge.output_silver_path,
        "output_gold_path": merge.output_gold_path,
        "sort_by_silver": list(merge.sort_by_silver),
        "sort_by_gold": list(merge.sort_by_gold),
        "field_priorities": {
            key: list(value) for key, value in merge.field_priorities.items()
        },
        "normalization_compatibility_overrides": dict(
            merge.normalization_compatibility_overrides
        ),
        "field_mappings": dict(merge.field_mappings),
        "column_groups": [_column_group_entry(group) for group in merge.column_groups],
        "exclude_fields": list(merge.exclude_fields),
        "preserve_all_sources": merge.preserve_all_sources,
    }


def _dq_override_entry(override: _DQOverrideProtocol) -> dict[str, object]:
    return {
        "soft_fail_threshold": override.soft_fail_threshold,
        "hard_fail_threshold": override.hard_fail_threshold,
    }


def _dq_to_dict(dq: _DQConfigProtocol) -> dict[str, object]:
    return {
        "soft_fail_threshold": dq.soft_fail_threshold,
        "hard_fail_threshold": dq.hard_fail_threshold,
        "required_fields": list(dq.required_fields),
        "enricher_overrides": {
            name: _dq_override_entry(override)
            for name, override in dq.enricher_overrides.items()
        },
    }


def _execution_to_dict(execution: _ExecutionConfigProtocol) -> dict[str, object]:
    return {
        "max_concurrency": execution.max_concurrency,
        "checkpoint_enabled": execution.checkpoint_enabled,
        "retry_max_attempts": execution.retry_max_attempts,
        "retry_backoff_multiplier": execution.retry_backoff_multiplier,
    }


def _lineage_to_dict(lineage: _LineageConfigProtocol) -> dict[str, object]:
    return {
        "track_field_sources": lineage.track_field_sources,
        "track_timestamps": lineage.track_timestamps,
        "track_status": lineage.track_status,
        "provider_lookup_fields": {
            provider: dict(fields)
            for provider, fields in lineage.provider_lookup_fields.items()
        },
        "track_source_for_fields": list(lineage.track_source_for_fields),
    }


def _cv_field_entry(field: _FieldComparisonProtocol) -> dict[str, object]:
    return {
        "field_name": field.field_name,
        "method": getattr(field.method, "value", field.method),
        "threshold": field.threshold,
    }


def _cv_pairing_entry(pairing: _EnricherPairingProtocol) -> dict[str, object]:
    return {
        "enricher_pipeline": pairing.enricher_pipeline,
        "fields": [_cv_field_entry(field) for field in pairing.fields],
    }


def _cross_validation_to_dict(
    cross_validation: _CrossValidationConfigProtocol,
) -> dict[str, object]:
    return {
        "enabled": cross_validation.enabled,
        "warning_threshold": cross_validation.warning_threshold,
        "error_threshold": cross_validation.error_threshold,
        "quarantine_threshold": cross_validation.quarantine_threshold,
        "fuzzy_threshold": cross_validation.fuzzy_threshold,
        "numeric_tolerance": cross_validation.numeric_tolerance,
        "enricher_pairings": [
            _cv_pairing_entry(pairing) for pairing in cross_validation.enricher_pairings
        ],
    }


def composite_to_dict(config: CompositeConfigProtocol) -> dict[str, object]:
    """Convert a composite config to a deterministic serializable mapping."""
    return {
        "name": config.name,
        "version": config.version,
        "seed": _seed_to_dict(config.seed),
        "dependencies": [
            _dependency_entry(dependency) for dependency in config.dependencies
        ],
        "enrichers": [_enricher_entry(enricher) for enricher in config.enrichers],
        "merge": _merge_to_dict(config.merge),
        "dq": _dq_to_dict(config.dq),
        "execution": _execution_to_dict(config.execution),
        "lineage": _lineage_to_dict(config.lineage),
        "cross_validation": _cross_validation_to_dict(config.cross_validation),
    }
