"""Helpers for provider-facing contract snapshot drift checks."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, cast
from collections.abc import Mapping

import pytest

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_SNAPSHOTS_DIR = ROOT / "tests" / "fixtures" / "contracts"
_PATH_TOKEN_RE = re.compile(r"([^\.\[]*)(?:\[(\d+)\])?")
_ALLOWED_TYPE_NAMES = frozenset({"bool", "dict", "float", "int", "list", "null", "str"})


class ContractPathResolutionError(ValueError):
    """Raised when a provider snapshot path cannot be resolved."""


def load_provider_contract_snapshot(
    provider: str, *, version: int = 1
) -> dict[str, Any]:
    """Load provider contract snapshot from the canonical fixture registry."""
    snapshot_path = CONTRACT_SNAPSHOTS_DIR / provider / f"v{version}.json"
    with snapshot_path.open(encoding="utf-8") as handle:
        return cast(dict[str, Any], json.load(handle))


def save_provider_contract_snapshot(
    provider: str,
    snapshot: Mapping[str, Any],
    *,
    version: int = 1,
) -> None:
    """Persist provider contract snapshot to the canonical fixture registry."""
    snapshot_path = CONTRACT_SNAPSHOTS_DIR / provider / f"v{version}.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    with snapshot_path.open("w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2, sort_keys=True)
        handle.write("\n")


def assert_provider_probe_matches_snapshot(
    provider: str,
    probe: str,
    payload: Any,
    *,
    update_snapshots: bool = False,
    version: int = 1,
) -> None:
    """Assert provider payload shape matches the stored probe snapshot."""
    snapshot = load_provider_contract_snapshot(provider, version=version)
    snapshot_probes = snapshot.get("probes", {})
    if probe not in snapshot_probes:
        pytest.fail(
            f"{provider} snapshot registry is missing probe {probe!r}. "
            "Add it to tests/fixtures/contracts before enabling the drift check."
        )

    probe_snapshot = snapshot_probes[probe]
    expected_paths = probe_snapshot.get("paths", {})
    actual_paths = _extract_actual_path_types(payload, expected_paths)

    if update_snapshots:
        updated_snapshot = dict(snapshot)
        updated_probe = dict(probe_snapshot)
        updated_probe["paths"] = actual_paths
        updated_snapshot["probes"] = dict(snapshot_probes)
        updated_snapshot["probes"][probe] = updated_probe
        save_provider_contract_snapshot(provider, updated_snapshot, version=version)
        pytest.skip(
            f"Updated provider contract snapshot for {provider}.{probe} "
            "(UPDATE_SNAPSHOTS=1)"
        )

    mismatches = [
        path
        for path, expected_type in expected_paths.items()
        if actual_paths.get(path) != expected_type
    ]
    if mismatches:
        lines = [f"{provider}.{probe}: provider contract snapshot drift detected"]
        for path in mismatches:
            lines.append(
                f"  {path}: expected {expected_paths[path]!r}, "
                f"got {actual_paths.get(path)!r}"
            )
        lines.append("If intentional, run: UPDATE_SNAPSHOTS=1 pytest ...")
        pytest.fail("\n".join(lines))


def assert_provider_snapshot_registry_shape(snapshot: Mapping[str, Any]) -> None:
    """Validate the minimal provider-facing snapshot registry structure."""
    assert isinstance(snapshot.get("provider"), str) and snapshot["provider"]
    assert snapshot.get("version") == 1
    probes = snapshot.get("probes")
    assert isinstance(probes, dict) and probes

    for probe_name, probe_snapshot in probes.items():
        assert isinstance(probe_name, str) and probe_name
        assert isinstance(probe_snapshot, dict)
        paths = probe_snapshot.get("paths")
        assert isinstance(paths, dict) and paths
        for path, type_name in paths.items():
            assert isinstance(path, str) and path
            assert type_name in _ALLOWED_TYPE_NAMES


def _extract_actual_path_types(
    payload: Any, expected_paths: Mapping[str, Any]
) -> dict[str, str]:
    actual_paths: dict[str, str] = {}
    for path in expected_paths:
        try:
            value = _resolve_path(payload, path)
        except ContractPathResolutionError as exc:
            pytest.fail(
                f"provider contract snapshot path {path!r} could not be resolved: {exc}\n"
                "If this is an intentional API change, run: UPDATE_SNAPSHOTS=1 pytest ..."
            )
        actual_paths[path] = _infer_type_name(value)
    return actual_paths


def _resolve_path(payload: Any, path: str) -> Any:
    current = payload
    for raw_part in path.split("."):
        match = _PATH_TOKEN_RE.fullmatch(raw_part)
        if match is None:
            raise ContractPathResolutionError(f"unsupported path token {raw_part!r}")
        key, raw_index = match.groups()
        if key:
            if not isinstance(current, dict):
                raise ContractPathResolutionError(
                    f"expected dict before key {key!r}, got {_infer_type_name(current)!r}"
                )
            if key not in current:
                raise ContractPathResolutionError(f"missing key {key!r}")
            current = current[key]
        elif raw_index is None:
            raise ContractPathResolutionError(f"empty path token {raw_part!r}")
        if raw_index is None:
            continue
        if not isinstance(current, list):
            raise ContractPathResolutionError(
                f"expected list at {raw_part!r}, got {_infer_type_name(current)!r}"
            )
        index = int(raw_index)
        if index >= len(current):
            raise ContractPathResolutionError(
                f"list at {raw_part!r} has length {len(current)}, missing index {index}"
            )
        current = current[index]
    return current


def _infer_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, dict):
        return "dict"
    if isinstance(value, list):
        return "list"
    if isinstance(value, int) and not isinstance(value, bool):
        return "int"
    if isinstance(value, float):
        return "float"
    return "str"
