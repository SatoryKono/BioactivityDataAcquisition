"""Nested raw run-manifest validators kept separate from store I/O."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import cast

_CODE_PROVENANCE_STRING_FIELDS = (
    "pipeline_version",
    "git_commit",
    "source_revision_state",
    "dependency_lock_hash",
    "config_hash",
    "resolved_config_hash",
    "effective_config_hash",
    "source_fingerprint",
    "contract_ref",
    "contract_version",
    "contract_schema_hash",
    "dq_policy_ref",
    "rule_bundle_version",
    "normalization_profile_ref",
    "normalization_profile_version",
    "normalization_profile_hash",
    "dq_contract_compatibility_hash",
    "effective_config_artifact_id",
)
_SNAPSHOT_OPTIONAL_STRING_FIELDS = (
    "immutable_uri",
    "query_fingerprint",
    "storage_provider",
    "object_bucket",
    "object_key",
    "object_version_id",
    "etag",
    "last_modified",
)


def raw_nested_schema_errors(payload: Mapping[str, object]) -> tuple[str, ...]:
    """Return bounded nested-container and scalar diagnostics."""
    errors: list[str] = []
    _check_code_provenance(payload.get("code_provenance"), errors)
    _check_source_refs(payload.get("source_refs"), errors)
    _check_planned_artifacts(payload.get("planned_artifacts"), errors)
    return tuple(sorted(set(errors)))


def _check_code_provenance(raw_value: object, errors: list[str]) -> None:
    if not isinstance(raw_value, dict):
        return
    payload = cast("Mapping[str, object]", raw_value)
    _check_optional_strings(
        payload,
        _CODE_PROVENANCE_STRING_FIELDS,
        "manifest_code_provenance",
        errors,
    )


def _check_source_refs(raw_sources: object, errors: list[str]) -> None:
    if not isinstance(raw_sources, list):
        return
    for raw_item in cast("list[object]", raw_sources):
        item = cast("Mapping[str, object]", raw_item)
        if not isinstance(item, dict):
            errors.append("manifest_source_ref_not_object")
            continue
        _check_required_strings(
            item,
            ("provider", "entity", "pipeline_name"),
            "manifest_source_ref",
            errors,
        )
        _check_optional_strings(item, ("query",), "manifest_source_ref", errors)
        if "input_snapshots" not in item:
            errors.append("manifest_source_ref_input_snapshots_missing")
            continue
        snapshots = item["input_snapshots"]
        if not isinstance(snapshots, list):
            errors.append("manifest_source_ref_input_snapshots_not_array")
            continue
        _check_input_snapshots(cast("list[object]", snapshots), errors)


def _check_input_snapshots(snapshots: list[object], errors: list[str]) -> None:
    for snapshot in snapshots:
        if not isinstance(snapshot, dict):
            errors.append("manifest_input_snapshot_not_object")
            continue
        payload = cast("Mapping[str, object]", snapshot)
        _check_required_strings(
            payload,
            ("snapshot_id", "content_hash"),
            "manifest_input",
            errors,
        )
        _check_optional_strings(
            payload,
            _SNAPSHOT_OPTIONAL_STRING_FIELDS,
            "manifest_input",
            errors,
        )
        captured_at = payload.get("captured_at")
        if captured_at is not None and not isinstance(captured_at, str):
            errors.append("manifest_input_captured_at_not_string")
        elif isinstance(captured_at, str):
            try:
                _ = datetime.fromisoformat(captured_at)
            except ValueError:
                errors.append("manifest_input_captured_at_invalid")


def _check_planned_artifacts(raw_artifacts: object, errors: list[str]) -> None:
    if not isinstance(raw_artifacts, list):
        return
    for raw_item in cast("list[object]", raw_artifacts):
        if not isinstance(raw_item, dict):
            errors.append("manifest_planned_artifact_not_object")
            continue
        item = cast("Mapping[str, object]", raw_item)
        _check_required_strings(
            item,
            ("layer", "path"),
            "manifest_planned_artifact",
            errors,
        )


def _check_required_strings(
    payload: Mapping[str, object],
    fields: tuple[str, ...],
    prefix: str,
    errors: list[str],
) -> None:
    for field in fields:
        if field not in payload:
            errors.append(f"{prefix}_{field}_missing")
            continue
        value = payload[field]
        if not isinstance(value, str):
            errors.append(f"{prefix}_{field}_not_string")
        elif not value.strip():
            errors.append(f"{prefix}_{field}_empty")


def _check_optional_strings(
    payload: Mapping[str, object],
    fields: tuple[str, ...],
    prefix: str,
    errors: list[str],
) -> None:
    for field in fields:
        value = payload.get(field)
        if value is not None and not isinstance(value, str):
            errors.append(f"{prefix}_{field}_not_string")


__all__ = ["raw_nested_schema_errors"]
