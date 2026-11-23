"""Canonical DQ-resolution helpers for validated pipeline YAML config."""

from __future__ import annotations

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


def has_inline_dq_overrides(yaml_config: PipelineYamlConfig) -> bool:
    """Check if YAML config has meaningful inline DQ overrides."""
    return bool(normalize_inline_dq_overrides(yaml_config.dq_overrides))


def field_validation_to_dict(
    fv: FieldValidationConfig,
) -> JsonDict:  # Any: dynamic YAML config values
    """Convert FieldValidationConfig to mergeable file-shape dict."""
    return fv.model_dump(exclude_unset=True, mode="json")


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


def _normalize_inline_dq_settings(
    dq_overrides: InlineDQConfig,
) -> JsonDict:
    """Keep only explicitly supplied scalar and report settings."""
    result: JsonDict = {}
    supplied = dq_overrides.model_fields_set
    thresholds: JsonDict = {}
    for source, target in (
        ("soft_fail_threshold", "soft_fail"),
        ("hard_fail_threshold", "hard_fail"),
    ):
        if source in supplied:
            thresholds[target] = getattr(dq_overrides, source)
    if thresholds:
        result["thresholds"] = thresholds
    for field in ("strict_validation", "invalid_record_policy"):
        if field in supplied:
            result[field] = getattr(dq_overrides, field)
    if "report" in supplied:
        report = dq_overrides.report.model_dump(exclude_unset=True, by_alias=True)
        if report:
            result["report"] = report
    return result


def normalize_inline_dq_overrides(
    dq_overrides: InlineDQConfig,
) -> JsonDict:  # Any: dynamic YAML config values
    """Convert inline Pydantic DQ overrides into mergeable file-shape dict."""
    result = _normalize_inline_dq_settings(dq_overrides)
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
