"""Canonical DQ-resolution helpers for validated pipeline YAML config."""

from __future__ import annotations

import math
from typing import Protocol

from bioetl.domain.config import DQConfig as DomainDQConfig
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config.converters import dq_overrides_to_domain
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.schemas.pipeline_config_dq import (
    ConditionalValidationConfig,
    CrossFieldValidationConfig,
    FieldValidationConfig,
)
from bioetl.infrastructure.schemas.pipeline_config_dq import (
    DQYamlConfig as InlineDQConfig,
)


class DQConfigResolver(Protocol):
    """Protocol for DQ loaders used during pipeline config resolution."""

    def load(
        self,
        provider: str,
        entity: str,
        inline_overrides: JsonDict | None = None,
    ) -> DomainDQConfig:
        """Load the merged DQ config for one provider/entity pair."""
        ...


_DEFAULT_SOFT_FAIL_THRESHOLD = 0.05
_DEFAULT_HARD_FAIL_THRESHOLD = 0.20


def has_inline_dq_overrides(yaml_config: PipelineYamlConfig) -> bool:
    """Check if YAML config has meaningful inline DQ overrides."""
    dq = yaml_config.dq_overrides
    has_validations = bool(
        dq.field_validations or dq.cross_field_validations or dq.conditional_validations
    )
    has_custom_thresholds = not (
        math.isclose(dq.soft_fail_threshold, _DEFAULT_SOFT_FAIL_THRESHOLD, abs_tol=1e-12)
        and math.isclose(dq.hard_fail_threshold, _DEFAULT_HARD_FAIL_THRESHOLD, abs_tol=1e-12)
    )
    return has_validations or has_custom_thresholds


def field_validation_to_dict(
    fv: FieldValidationConfig,
) -> JsonDict:  # Any: dynamic YAML config values
    """Convert FieldValidationConfig to mergeable file-shape dict."""
    result: JsonDict = {  # Any: dynamic YAML config values
        "field": fv.field,
        "type": fv.type,
        "nullable": fv.nullable,
    }
    if fv.min is not None:
        result["min"] = fv.min
    if fv.max is not None:
        result["max"] = fv.max
    if fv.pattern:
        result["pattern"] = fv.pattern
    if fv.allowed:
        result["allowed"] = list(fv.allowed)
    if fv.validator:
        result["validator"] = fv.validator
    if fv.error_message:
        result["error_message"] = fv.error_message
    return result


def cross_field_validation_to_dict(
    cfv: CrossFieldValidationConfig,
) -> JsonDict:  # Any: dynamic YAML config values
    """Convert CrossFieldValidationConfig to mergeable file-shape dict."""
    result: JsonDict = {  # Any: dynamic YAML config values
        "name": cfv.name,
        "fields": list(cfv.fields),
        "condition": cfv.condition,
    }
    if cfv.severity != "error":
        result["severity"] = cfv.severity
    if cfv.trigger_field:
        result["trigger_field"] = cfv.trigger_field
    if cfv.required_field:
        result["required_field"] = cfv.required_field
    if cfv.validator:
        result["validator"] = cfv.validator
    if cfv.error_message:
        result["error_message"] = cfv.error_message
    return result


def conditional_validation_to_dict(
    cv: ConditionalValidationConfig,
) -> JsonDict:  # Any: dynamic YAML config values
    """Convert ConditionalValidationConfig to mergeable file-shape dict."""
    result: JsonDict = {  # Any: dynamic YAML config values
        "name": cv.name,
        "condition_field": cv.condition_field,
        "condition_value": (
            list(cv.condition_value)
            if isinstance(cv.condition_value, list)
            else cv.condition_value
        ),
        "condition_operator": cv.condition_operator,
    }
    if cv.then_validations:
        result["then_validations"] = [
            field_validation_to_dict(tv) for tv in cv.then_validations
        ]
    return result


def normalize_inline_dq_overrides(
    dq_overrides: InlineDQConfig,
) -> JsonDict:  # Any: dynamic YAML config values
    """Convert inline Pydantic DQ overrides into mergeable file-shape dict."""
    result: JsonDict = {}  # Any: dynamic YAML config values
    result["thresholds"] = {
        "soft_fail": dq_overrides.soft_fail_threshold,
        "hard_fail": dq_overrides.hard_fail_threshold,
    }
    result["strict_validation"] = dq_overrides.strict_validation
    result["invalid_record_policy"] = dq_overrides.invalid_record_policy
    result["report"] = {
        "enabled": dq_overrides.report.enabled,
        "format": dq_overrides.report.format,
        "include_sample_failures": dq_overrides.report.include_sample_failures,
        "sample_size": dq_overrides.report.sample_size,
        "output_path": dq_overrides.report.output_path,
    }

    if dq_overrides.field_validations:
        result["entity_field_validations"] = [
            field_validation_to_dict(fv) for fv in dq_overrides.field_validations
        ]

    if dq_overrides.cross_field_validations:
        result["entity_cross_field_validations"] = [
            cross_field_validation_to_dict(cfv)
            for cfv in dq_overrides.cross_field_validations
        ]

    if dq_overrides.conditional_validations:
        result["entity_conditional_validations"] = [
            conditional_validation_to_dict(cv)
            for cv in dq_overrides.conditional_validations
        ]

    return result


def resolve_pipeline_dq_config(
    yaml_config: PipelineYamlConfig,
    *,
    dq_loader: DQConfigResolver,
) -> DomainDQConfig:
    """Resolve DQ config from hierarchy with optional inline overrides."""
    provider = yaml_config.provider
    entity = yaml_config.entity_type
    dq_config_file = getattr(yaml_config, "dq_config_file", None)
    inline_rules_present = has_inline_dq_overrides(yaml_config)

    if dq_config_file is not None or inline_rules_present:
        inline_overrides = (
            normalize_inline_dq_overrides(yaml_config.dq_overrides)
            if inline_rules_present
            else None
        )
        return dq_loader.load(
            provider=provider,
            entity=entity,
            inline_overrides=inline_overrides,
        )

    try:
        return dq_loader.load(
            provider=provider,
            entity=entity,
            inline_overrides=None,
        )
    except FileNotFoundError:
        return dq_overrides_to_domain(yaml_config)


__all__ = [
    "DQConfigResolver",
    "conditional_validation_to_dict",
    "cross_field_validation_to_dict",
    "field_validation_to_dict",
    "has_inline_dq_overrides",
    "normalize_inline_dq_overrides",
    "resolve_pipeline_dq_config",
]
