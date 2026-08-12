"""Decode optional sections of a serialized composite configuration."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.domain.composite.cross_validation import (
    ComparisonMethod,
    EnricherFieldPairing,
    FieldComparisonSpec,
)

from .config_cross_validation import CrossValidationConfig
from .config_dq import CompositeDQConfig, DQOverrideConfig
from .config_parsing import (
    optional_float,
    optional_str_tuple,
    require_float,
    require_int,
    str_key_mapping,
)
from .config_runtime import ExecutionConfig, LineageConfig

__all__ = [
    "build_cross_validation_config",
    "build_dq_config",
    "build_execution_config",
    "build_lineage_config",
]


def _one_dq_override(name: str, raw: dict[str, object]) -> DQOverrideConfig:
    return DQOverrideConfig(
        soft_fail_threshold=optional_float(
            raw.get("soft_fail_threshold"),
            f"dq.enricher_overrides[{name}].soft_fail_threshold",
        ),
        hard_fail_threshold=optional_float(
            raw.get("hard_fail_threshold"),
            f"dq.enricher_overrides[{name}].hard_fail_threshold",
        ),
    )


def _build_dq_overrides(
    overrides_raw: dict[str, object],
) -> dict[str, DQOverrideConfig]:
    overrides: dict[str, DQOverrideConfig] = {}
    for name, raw in overrides_raw.items():
        if not isinstance(raw, dict):
            raise ValueError(
                f"dq.enricher_overrides[{name}] must be a dictionary, "
                f"got {type(raw).__name__}"
            )
        overrides[name] = _one_dq_override(name, raw)
    return overrides


def build_dq_config(dq_data: dict[str, object]) -> CompositeDQConfig:
    overrides = _build_dq_overrides(
        str_key_mapping(dq_data.get("enricher_overrides"), "dq.enricher_overrides")
    )
    required_fields = optional_str_tuple(
        dq_data.get("required_fields"), "dq.required_fields"
    )
    return CompositeDQConfig(
        soft_fail_threshold=require_float(
            dq_data.get("soft_fail_threshold"), "dq.soft_fail_threshold", 0.10
        ),
        hard_fail_threshold=require_float(
            dq_data.get("hard_fail_threshold"), "dq.hard_fail_threshold", 0.50
        ),
        enricher_overrides=overrides,
        required_fields=required_fields or (),
    )


def build_execution_config(execution_data: dict[str, object]) -> ExecutionConfig:
    return ExecutionConfig(
        max_concurrency=require_int(
            execution_data.get("max_concurrency"), "execution.max_concurrency", 4
        ),
        checkpoint_enabled=bool(execution_data.get("checkpoint_enabled", True)),
        retry_max_attempts=require_int(
            execution_data.get("retry_max_attempts"),
            "execution.retry_max_attempts",
            3,
        ),
        retry_backoff_multiplier=require_float(
            execution_data.get("retry_backoff_multiplier"),
            "execution.retry_backoff_multiplier",
            2.0,
        ),
    )


def build_lineage_config(lineage_data: dict[str, object]) -> LineageConfig:
    lookup_raw = str_key_mapping(
        lineage_data.get("provider_lookup_fields"),
        "lineage.provider_lookup_fields",
    )
    lookup = {
        provider: {str(key): str(value) for key, value in fields.items()}
        for provider, fields in lookup_raw.items()
        if isinstance(fields, Mapping)
    }
    track_fields = optional_str_tuple(
        lineage_data.get("track_source_for_fields"),
        "lineage.track_source_for_fields",
    )
    return LineageConfig(
        track_field_sources=bool(lineage_data.get("track_field_sources", True)),
        track_timestamps=bool(lineage_data.get("track_timestamps", True)),
        track_status=bool(lineage_data.get("track_status", True)),
        provider_lookup_fields=lookup,
        track_source_for_fields=track_fields or (),
    )


def _comparison_method(raw: object) -> ComparisonMethod:
    if isinstance(raw, ComparisonMethod):
        return raw
    return ComparisonMethod(str(raw if raw is not None else "exact"))


def _one_field_comparison_spec(field: dict[str, object]) -> FieldComparisonSpec:
    return FieldComparisonSpec(
        field_name=str(field.get("field_name") or ""),
        method=_comparison_method(field.get("method", "exact")),
        threshold=float(str(field.get("threshold", 0.0))),
    )


def _field_comparison_specs(fields_raw: object) -> tuple[FieldComparisonSpec, ...]:
    if not isinstance(fields_raw, list | tuple):
        return ()
    return tuple(
        _one_field_comparison_spec(field)
        for field in fields_raw
        if isinstance(field, dict)
    )


def _one_enricher_pairing(raw: dict[str, object]) -> EnricherFieldPairing:
    return EnricherFieldPairing(
        enricher_pipeline=str(raw.get("enricher_pipeline") or ""),
        fields=_field_comparison_specs(raw.get("fields") or ()),
    )


def _enricher_field_pairings(pairings_raw: object) -> tuple[EnricherFieldPairing, ...]:
    if not isinstance(pairings_raw, list | tuple):
        return ()
    return tuple(
        _one_enricher_pairing(raw) for raw in pairings_raw if isinstance(raw, dict)
    )


def build_cross_validation_config(
    cv_data: dict[str, object],
) -> CrossValidationConfig:
    return CrossValidationConfig(
        enabled=bool(cv_data.get("enabled", True)),
        warning_threshold=int(str(cv_data.get("warning_threshold", 1))),
        error_threshold=int(str(cv_data.get("error_threshold", 2))),
        quarantine_threshold=int(str(cv_data.get("quarantine_threshold", 2))),
        fuzzy_threshold=float(str(cv_data.get("fuzzy_threshold", 0.8))),
        numeric_tolerance=float(str(cv_data.get("numeric_tolerance", 0.10))),
        enricher_pairings=_enricher_field_pairings(
            cv_data.get("enricher_pairings") or ()
        ),
    )
