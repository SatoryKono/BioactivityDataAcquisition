"""Support helpers for ``RunContext.create`` input coercion."""

from __future__ import annotations

from datetime import datetime
from typing import cast

from bioetl.domain.types import RunID, RunType
from bioetl.domain.value_objects._run_context_models import RunContextCreateInput

_RUN_CONTEXT_REQUIRED_FIELDS = (
    "run_id",
    "run_type",
    "started_at",
    "provider",
    "entity",
)
_RUN_CONTEXT_OPTIONAL_DEFAULTS: dict[str, object] = {
    "transform_version": None,
    "transform_steps": (),
    "pipeline_version": None,
    "git_commit": None,
    "dependency_lock_hash": None,
    "config_hash": None,
    "resolved_config_hash": None,
    "effective_config_hash": None,
    "manifest_id": None,
    "contract_ref": None,
    "contract_version": None,
    "contract_schema_hash": None,
    "dq_policy_ref": None,
    "rule_bundle_version": None,
    "dq_contract_compatibility_hash": None,
    "effective_config_artifact_id": None,
    "execution_fingerprint": None,
}
_RUN_CONTEXT_ALL_FIELDS = (
    *_RUN_CONTEXT_REQUIRED_FIELDS,
    *_RUN_CONTEXT_OPTIONAL_DEFAULTS.keys(),
)
type _OPTIONAL_STR_ANNOTATION = "str | None"


def _coerce_transform_steps(value: object) -> tuple[str, ...]:
    """Normalize ``transform_steps`` overrides into the canonical tuple form."""
    transform_steps = _coerce_transform_step_sequence(value)
    _validate_transform_step_items(transform_steps)
    return transform_steps


def _coerce_transform_step_sequence(value: object) -> tuple[str, ...]:
    """Convert supported transform-step inputs into a tuple for validation."""
    if value is None:
        return ()
    if isinstance(value, list | tuple):
        transform_steps = tuple(value)
        _validate_transform_step_items(transform_steps)
        return tuple(cast(str, item) for item in transform_steps)
    raise TypeError("RunContext.create() transform_steps must be a sequence of strings")


def _validate_transform_step_items(transform_steps: tuple[object, ...]) -> None:
    """Reject non-string transform-step values before model construction."""
    if any(not isinstance(item, str) for item in transform_steps):
        raise TypeError(
            "RunContext.create() transform_steps must be a sequence of strings"
        )


def _resolve_create_input_value(
    *,
    field_name: str,
    inputs: RunContextCreateInput | None,
    overrides: dict[str, object],
) -> object:
    if field_name in overrides:
        return overrides[field_name]
    if field_name in _RUN_CONTEXT_OPTIONAL_DEFAULTS and inputs is None:
        return _RUN_CONTEXT_OPTIONAL_DEFAULTS[field_name]
    if inputs is None:
        raise TypeError(
            f"RunContext.create() missing required argument: '{field_name}'"
        )
    return getattr(inputs, field_name)


def _ensure_required_create_input_fields(
    inputs: RunContextCreateInput | None,
    overrides: dict[str, object],
) -> None:
    for field_name in _RUN_CONTEXT_REQUIRED_FIELDS:
        _resolve_create_input_value(
            field_name=field_name,
            inputs=inputs,
            overrides=overrides,
        )


def _collect_create_input_values(
    inputs: RunContextCreateInput | None,
    overrides: dict[str, object],
) -> dict[str, object]:
    """Collect field values for ``RunContextCreateInput`` construction."""
    _ensure_required_create_input_fields(inputs, overrides)
    values = {
        field_name: _resolve_create_input_value(
            field_name=field_name,
            inputs=inputs,
            overrides=overrides,
        )
        for field_name in _RUN_CONTEXT_ALL_FIELDS
    }
    values["transform_steps"] = _coerce_transform_steps(values["transform_steps"])
    return values


def coerce_run_context_create_input(
    inputs: RunContextCreateInput | None,
    overrides: dict[str, object],
) -> RunContextCreateInput:
    values = _collect_create_input_values(inputs, overrides)
    return RunContextCreateInput(
        run_id=cast("RunID", values["run_id"]),
        run_type=cast("RunType", values["run_type"]),
        started_at=cast(datetime, values["started_at"]),
        provider=cast(str, values["provider"]),
        entity=cast(str, values["entity"]),
        transform_version=cast(_OPTIONAL_STR_ANNOTATION, values["transform_version"]),
        transform_steps=cast("tuple[str, ...]", values["transform_steps"]),
        pipeline_version=cast(_OPTIONAL_STR_ANNOTATION, values["pipeline_version"]),
        git_commit=cast(_OPTIONAL_STR_ANNOTATION, values["git_commit"]),
        dependency_lock_hash=cast(
            _OPTIONAL_STR_ANNOTATION, values["dependency_lock_hash"]
        ),
        config_hash=cast(_OPTIONAL_STR_ANNOTATION, values["config_hash"]),
        resolved_config_hash=cast(
            _OPTIONAL_STR_ANNOTATION, values["resolved_config_hash"]
        ),
        effective_config_hash=cast(
            _OPTIONAL_STR_ANNOTATION, values["effective_config_hash"]
        ),
        manifest_id=cast(_OPTIONAL_STR_ANNOTATION, values["manifest_id"]),
        contract_ref=cast(_OPTIONAL_STR_ANNOTATION, values["contract_ref"]),
        contract_version=cast(_OPTIONAL_STR_ANNOTATION, values["contract_version"]),
        contract_schema_hash=cast(
            _OPTIONAL_STR_ANNOTATION, values["contract_schema_hash"]
        ),
        dq_policy_ref=cast(_OPTIONAL_STR_ANNOTATION, values["dq_policy_ref"]),
        rule_bundle_version=cast(
            _OPTIONAL_STR_ANNOTATION, values["rule_bundle_version"]
        ),
        dq_contract_compatibility_hash=cast(
            _OPTIONAL_STR_ANNOTATION, values["dq_contract_compatibility_hash"]
        ),
        effective_config_artifact_id=cast(
            _OPTIONAL_STR_ANNOTATION, values["effective_config_artifact_id"]
        ),
        execution_fingerprint=cast(
            _OPTIONAL_STR_ANNOTATION, values["execution_fingerprint"]
        ),
    )
