"""Raw persisted run-manifest schema diagnostics."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Protocol, cast
from uuid import UUID

from bioetl.domain.ports import RawManifestInspection
from bioetl.domain.serialization import deserialize_from_json
from bioetl.domain.types import RunType
from bioetl.infrastructure.control_plane._raw_run_manifest_nested_validation import (
    raw_nested_schema_errors,
)

_REQUIRED_STRING_FIELDS = (
    "manifest_id",
    "execution_fingerprint",
    "schema_version",
    "created_at",
    "run_id",
    "run_type",
    "pipeline_name",
    "provider",
    "entity",
)
_REQUIRED_MAPPING_FIELDS = ("launch_context",)
_REQUIRED_LIST_FIELDS = ("source_refs",)
_OPTIONAL_MAPPING_FIELDS = (
    "runtime_config",
    "resolved_config",
    "code_provenance",
)
_OPTIONAL_LIST_FIELDS = ("planned_artifacts",)
_OPTIONAL_STRING_FIELDS = (
    "workflow_run_id",
    "workflow_name",
    "workflow_step_id",
    "replay_of_run_id",
    "replay_of_manifest_id",
    "replay_capability",
)
_SCHEMA_VERSION_PATTERN = re.compile(r"[0-9]+\.[0-9]+(?:\.[0-9]+)?")


class _RawManifestInspectionHost(Protocol):
    base_path: Path


class RawRunManifestInspectionMixin:
    """Provide bounded pre-coercion diagnostics to file manifest stores."""

    __slots__: tuple[str, ...] = ()

    def inspect_raw_manifest(self, manifest_id: str) -> RawManifestInspection:
        """Inspect raw JSON shape without calling ``RunManifest.from_dict``."""
        host = cast("_RawManifestInspectionHost", cast("object", self))
        path = host.base_path / f"{manifest_id}.json"
        if not path.is_file():
            return RawManifestInspection(False, ("manifest_not_found",))
        try:
            raw_payload = deserialize_from_json(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            return RawManifestInspection(False, ("manifest_parse_error",))
        except (OSError, UnicodeError):
            return RawManifestInspection(False, ("manifest_read_error",))
        if not isinstance(raw_payload, dict):
            return RawManifestInspection(True, ("manifest_payload_not_object",))
        payload = cast("dict[str, object]", raw_payload)
        return RawManifestInspection(
            True,
            _raw_schema_errors(payload, expected_manifest_id=manifest_id),
        )


def _raw_schema_errors(
    payload: dict[str, object],
    *,
    expected_manifest_id: str,
) -> tuple[str, ...]:
    errors: list[str] = []
    _check_required_strings(payload, errors)
    _check_required_containers(payload, errors)
    _check_optional_fields(payload, errors)
    _check_identity_values(payload, expected_manifest_id, errors)
    errors.extend(raw_nested_schema_errors(payload))
    return tuple(sorted(set(errors)))


def _check_required_strings(
    payload: dict[str, object],
    errors: list[str],
) -> None:
    for field in _REQUIRED_STRING_FIELDS:
        if field not in payload:
            errors.append(f"manifest_{field}_missing")
            continue
        value = payload[field]
        if not isinstance(value, str):
            errors.append(f"manifest_{field}_not_string")
        elif not value.strip():
            errors.append(f"manifest_{field}_empty")


def _check_required_containers(
    payload: dict[str, object],
    errors: list[str],
) -> None:
    for field in _REQUIRED_MAPPING_FIELDS:
        if field not in payload:
            errors.append(f"manifest_{field}_missing")
        elif not isinstance(payload[field], dict):
            errors.append(f"manifest_{field}_not_object")
    for field in _REQUIRED_LIST_FIELDS:
        if field not in payload:
            errors.append(f"manifest_{field}_missing")
        elif not isinstance(payload[field], list):
            errors.append(f"manifest_{field}_not_array")


def _check_optional_fields(
    payload: dict[str, object],
    errors: list[str],
) -> None:
    for field in _OPTIONAL_MAPPING_FIELDS:
        if field in payload and not isinstance(payload[field], dict):
            errors.append(f"manifest_{field}_not_object")
    for field in _OPTIONAL_LIST_FIELDS:
        if field in payload and not isinstance(payload[field], list):
            errors.append(f"manifest_{field}_not_array")
    for field in _OPTIONAL_STRING_FIELDS:
        value = payload.get(field)
        if value is not None and not isinstance(value, str):
            errors.append(f"manifest_{field}_not_string")


def _check_identity_values(
    payload: dict[str, object],
    expected_manifest_id: str,
    errors: list[str],
) -> None:
    manifest_id = payload.get("manifest_id")
    if isinstance(manifest_id, str) and manifest_id != expected_manifest_id:
        errors.append("manifest_id_mismatch")
    if _invalid_parsed_text(payload.get("run_id"), UUID):
        errors.append("manifest_run_id_invalid")
    if _invalid_parsed_text(payload.get("created_at"), datetime.fromisoformat):
        errors.append("manifest_created_at_invalid")
    if _invalid_parsed_text(payload.get("run_type"), RunType):
        errors.append("manifest_run_type_invalid")
    schema_version = payload.get("schema_version")
    if isinstance(schema_version, str) and not _SCHEMA_VERSION_PATTERN.fullmatch(
        schema_version
    ):
        errors.append("manifest_schema_version_invalid")


def _invalid_parsed_text(
    value: object,
    parser: Callable[[str], object],
) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parser(value)
    except ValueError:
        return True
    return False


__all__ = ["RawRunManifestInspectionMixin"]
