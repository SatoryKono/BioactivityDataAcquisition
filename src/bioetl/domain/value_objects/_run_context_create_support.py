"""Support helpers for ``RunContext.create`` input coercion."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import cast
from uuid import UUID

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
    "normalization_profile_ref": None,
    "normalization_profile_version": None,
    "normalization_profile_hash": None,
    "dq_contract_compatibility_hash": None,
    "effective_config_artifact_id": None,
    "execution_fingerprint": None,
    "exact_replay": False,
    "required_persistence_profile": None,
    "replay_of_run_id": None,
    "replay_of_manifest_id": None,
    "input_snapshot_fingerprint": None,
}
_RUN_CONTEXT_ALL_FIELDS = (
    *_RUN_CONTEXT_REQUIRED_FIELDS,
    *_RUN_CONTEXT_OPTIONAL_DEFAULTS.keys(),
)


def _coerce_transform_steps(value: object) -> tuple[str, ...]:
    """Normalize ``transform_steps`` overrides into the canonical tuple form."""
    return _coerce_transform_step_sequence(value)


def _coerce_transform_step_sequence(value: object) -> tuple[str, ...]:
    """Convert supported transform-step inputs into a tuple for validation."""
    if value is None:
        return ()
    if isinstance(value, list | tuple):
        transform_steps: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise TypeError(
                    "RunContext.create() transform_steps must be a sequence of strings"
                )
            transform_steps.append(item)
        return tuple(transform_steps)
    raise TypeError("RunContext.create() transform_steps must be a sequence of strings")


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
    value: object = getattr(inputs, field_name)
    return value


def _ensure_required_create_input_fields(
    inputs: RunContextCreateInput | None,
    overrides: dict[str, object],
) -> None:
    for field_name in _RUN_CONTEXT_REQUIRED_FIELDS:
        _ = _resolve_create_input_value(
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


def _require_value[T](
    values: Mapping[str, object],
    field_name: str,
    expected_type: type[T],
) -> T:
    """Return a collected create value after runtime type narrowing."""
    value = values[field_name]
    if not isinstance(value, expected_type):
        raise TypeError(
            f"RunContext.create() {field_name} must be "
            f"{expected_type.__name__}, got {type(value).__name__}"
        )
    return value


def _optional_str_value(
    values: Mapping[str, object],
    field_name: str,
) -> str | None:
    """Return an optional string create value after runtime narrowing."""
    value = values[field_name]
    if value is None or isinstance(value, str):
        return value
    raise TypeError(
        f"RunContext.create() {field_name} must be str or None, "
        f"got {type(value).__name__}"
    )


def _run_id_value(values: Mapping[str, object]) -> RunID:
    """Return the nominal run identifier while preserving legacy string IDs."""
    value = values["run_id"]
    if not isinstance(value, UUID | str):
        raise TypeError(
            "RunContext.create() run_id must be UUID or a legacy string, "
            f"got {type(value).__name__}"
        )
    # RunID is UUID-backed statically, but historical RunContext callers accepted
    # opaque string identifiers. Keep that compatibility cast at this single seam.
    return cast("RunID", value)


def coerce_run_context_create_input(
    inputs: RunContextCreateInput | None,
    overrides: dict[str, object],
) -> RunContextCreateInput:
    values = _collect_create_input_values(inputs, overrides)
    return RunContextCreateInput(
        run_id=_run_id_value(values),
        run_type=_require_value(values, "run_type", RunType),
        started_at=_require_value(values, "started_at", datetime),
        provider=_require_value(values, "provider", str),
        entity=_require_value(values, "entity", str),
        transform_version=_optional_str_value(values, "transform_version"),
        transform_steps=_coerce_transform_steps(values["transform_steps"]),
        pipeline_version=_optional_str_value(values, "pipeline_version"),
        git_commit=_optional_str_value(values, "git_commit"),
        dependency_lock_hash=_optional_str_value(values, "dependency_lock_hash"),
        config_hash=_optional_str_value(values, "config_hash"),
        resolved_config_hash=_optional_str_value(values, "resolved_config_hash"),
        effective_config_hash=_optional_str_value(values, "effective_config_hash"),
        manifest_id=_optional_str_value(values, "manifest_id"),
        contract_ref=_optional_str_value(values, "contract_ref"),
        contract_version=_optional_str_value(values, "contract_version"),
        contract_schema_hash=_optional_str_value(values, "contract_schema_hash"),
        dq_policy_ref=_optional_str_value(values, "dq_policy_ref"),
        rule_bundle_version=_optional_str_value(values, "rule_bundle_version"),
        normalization_profile_ref=_optional_str_value(
            values, "normalization_profile_ref"
        ),
        normalization_profile_version=_optional_str_value(
            values, "normalization_profile_version"
        ),
        normalization_profile_hash=_optional_str_value(
            values, "normalization_profile_hash"
        ),
        dq_contract_compatibility_hash=_optional_str_value(
            values, "dq_contract_compatibility_hash"
        ),
        effective_config_artifact_id=_optional_str_value(
            values, "effective_config_artifact_id"
        ),
        execution_fingerprint=_optional_str_value(values, "execution_fingerprint"),
        exact_replay=_require_value(values, "exact_replay", bool),
        required_persistence_profile=_optional_str_value(
            values, "required_persistence_profile"
        ),
        replay_of_run_id=_optional_str_value(values, "replay_of_run_id"),
        replay_of_manifest_id=_optional_str_value(values, "replay_of_manifest_id"),
        input_snapshot_fingerprint=_optional_str_value(
            values, "input_snapshot_fingerprint"
        ),
    )
