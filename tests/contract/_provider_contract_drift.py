"""Helpers for provider-facing contract snapshot drift checks."""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
import re
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_SNAPSHOTS_DIR = ROOT / "tests" / "fixtures" / "contracts"
_PATH_TOKEN_RE = re.compile(r"([^\.\[]*)(?:\[(\d+)\])?")
_ALLOWED_TYPE_NAMES = frozenset({"bool", "dict", "float", "int", "list", "null", "str"})
_BREAKING_SEVERITY = "breaking"
_WARNING_SEVERITY = "warning"
_BENIGN_SEVERITY = "benign"
_SEVERITY_RANK = {
    _BENIGN_SEVERITY: 0,
    _WARNING_SEVERITY: 1,
    _BREAKING_SEVERITY: 2,
}


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
    import pytest

    snapshot = load_provider_contract_snapshot(provider, version=version)
    snapshot_probes = snapshot.get("probes", {})
    if probe not in snapshot_probes:
        pytest.fail(
            f"{provider} snapshot registry is missing probe {probe!r}. "
            "Add it to tests/fixtures/contracts before enabling the drift check."
        )

    probe_snapshot = snapshot_probes[probe]
    expected_paths = probe_snapshot.get("paths", {})
    if update_snapshots:
        actual_paths = _extract_actual_path_types(payload, expected_paths)
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

    report = compare_provider_probe_to_snapshot(
        provider,
        probe,
        payload,
        version=version,
    )
    difference_count = cast(int, report["difference_count"])
    if difference_count:
        lines = [
            f"{provider}.{probe}: provider contract snapshot drift detected",
            f"entity={report['entity']}",
            f"severity={report['severity']}",
            f"paths_checked={report['paths_checked']}",
            f"mismatched_paths={difference_count}",
        ]
        for difference in cast(list[dict[str, Any]], report["differences"]):
            path = cast(str, difference["path"])
            expected_type = cast(str | None, difference["expected_type"])
            actual_type = cast(str | None, difference["actual_type"])
            detail = cast(str, difference["detail"])
            remediation = cast(str, difference["remediation"])
            lines.append(
                f"  {path}: expected {expected_type!r}, got {actual_type!r} "
                f"({difference['severity']}; {detail}; remediation={remediation})"
            )
        lines.append("If intentional, run: UPDATE_SNAPSHOTS=1 pytest ...")
        pytest.fail("\n".join(lines))


def compare_provider_probe_to_snapshot(
    provider: str,
    probe: str,
    payload: Any,
    *,
    version: int = 1,
) -> dict[str, Any]:
    """Build a machine-readable drift report for a provider probe."""
    snapshot = load_provider_contract_snapshot(provider, version=version)
    snapshot_probes = snapshot.get("probes", {})
    if probe not in snapshot_probes:
        raise AssertionError(
            f"{provider} snapshot registry is missing probe {probe!r}. "
            "Add it to tests/fixtures/contracts before enabling the drift check."
        )

    probe_snapshot = cast(Mapping[str, Any], snapshot_probes[probe])
    expected_paths = cast(Mapping[str, str], probe_snapshot.get("paths", {}))
    entity = _infer_entity(provider=provider, probe=probe)
    actual_paths: dict[str, str] = {}
    differences: list[dict[str, Any]] = []

    for path, expected_type in expected_paths.items():
        try:
            value = _resolve_path(payload, path)
        except ContractPathResolutionError as exc:
            differences.append(
                {
                    "path": path,
                    "kind": "missing_path",
                    "expected_type": expected_type,
                    "actual_type": None,
                    "severity": _BREAKING_SEVERITY,
                    "detail": str(exc),
                    "remediation": _remediation_for_difference(
                        kind="missing_path",
                        expected_type=expected_type,
                        actual_type=None,
                    ),
                }
            )
            continue

        actual_type = _infer_type_name(value)
        actual_paths[path] = actual_type
        if actual_type == expected_type:
            continue
        differences.append(
            {
                "path": path,
                "kind": "type_changed",
                "expected_type": expected_type,
                "actual_type": actual_type,
                "severity": _classify_type_change(
                    expected_type=expected_type,
                    actual_type=actual_type,
                ),
                "detail": _describe_type_change(
                    expected_type=expected_type,
                    actual_type=actual_type,
                ),
                "remediation": _remediation_for_difference(
                    kind="type_changed",
                    expected_type=expected_type,
                    actual_type=actual_type,
                ),
            }
        )

    severity = _max_severity(
        cast(list[str], [difference["severity"] for difference in differences])
    )
    return {
        "provider": provider,
        "entity": entity,
        "probe": probe,
        "version": version,
        "paths_checked": len(expected_paths),
        "difference_count": len(differences),
        "severity": severity,
        "status": "match" if not differences else "drift",
        "expected_paths": dict(expected_paths),
        "actual_paths": actual_paths,
        "differences": differences,
    }


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
    import pytest

    actual_paths: dict[str, str] = {}
    for path in expected_paths:
        try:
            value = _resolve_path(payload, path)
        except ContractPathResolutionError as exc:
            pytest.fail(
                "provider contract snapshot path could not be resolved\n"
                f"severity={_BREAKING_SEVERITY}\n"
                f"path={path!r}\n"
                f"error={exc}\n"
                "If this is an intentional API change, run: UPDATE_SNAPSHOTS=1 pytest ..."
            )
        actual_paths[path] = _infer_type_name(value)
    return actual_paths


def _path_token(raw_part: str) -> tuple[str, str | None]:
    match = _PATH_TOKEN_RE.fullmatch(raw_part)
    if match is None:
        raise ContractPathResolutionError(f"unsupported path token {raw_part!r}")
    return match.groups()


def _resolve_mapping_key(current: Any, key: str) -> Any:
    if not isinstance(current, dict):
        raise ContractPathResolutionError(
            f"expected dict before key {key!r}, got {_infer_type_name(current)!r}"
        )
    if key not in current:
        raise ContractPathResolutionError(f"missing key {key!r}")
    return current[key]


def _resolve_list_index(current: Any, raw_part: str, raw_index: str) -> Any:
    if not isinstance(current, list):
        raise ContractPathResolutionError(
            f"expected list at {raw_part!r}, got {_infer_type_name(current)!r}"
        )
    index = int(raw_index)
    if index >= len(current):
        raise ContractPathResolutionError(
            f"list at {raw_part!r} has length {len(current)}, missing index {index}"
        )
    return current[index]


def _resolve_path_token(current: Any, raw_part: str) -> Any:
    key, raw_index = _path_token(raw_part)
    if key:
        current = _resolve_mapping_key(current, key)
    elif raw_index is None:
        raise ContractPathResolutionError(f"empty path token {raw_part!r}")
    if raw_index is None:
        return current
    return _resolve_list_index(current, raw_part, raw_index)


def _resolve_path(payload: Any, path: str) -> Any:
    current = payload
    for raw_part in path.split("."):
        current = _resolve_path_token(current, raw_part)
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


def _classify_type_change(*, expected_type: str, actual_type: str) -> str:
    if actual_type == "null" and expected_type != "null":
        return _WARNING_SEVERITY
    if {expected_type, actual_type} <= {"int", "float"}:
        return _WARNING_SEVERITY
    return _BREAKING_SEVERITY


def _describe_type_change(*, expected_type: str, actual_type: str) -> str:
    if actual_type == "null" and expected_type != "null":
        return "path became nullable"
    if {expected_type, actual_type} <= {"int", "float"}:
        return "numeric type changed"
    return "provider-facing path type changed"


def _remediation_for_difference(
    *,
    kind: str,
    expected_type: str,
    actual_type: str | None,
) -> str:
    if kind == "missing_path":
        return (
            "update adapter/schema/config/docs for a removed provider field, or "
            "refresh fixture only after verifying the provider docs"
        )
    if actual_type == "null" and expected_type != "null":
        return (
            "update schema nullability or transformer fallback; refresh fixture only "
            "if provider nullable behavior is expected"
        )
    if actual_type is not None and {expected_type, actual_type} <= {"int", "float"}:
        return (
            "update numeric schema/coercion expectation or refresh fixture after "
            "confirming provider numeric type semantics"
        )
    return (
        "update adapter/schema/config/docs for provider contract drift, then refresh "
        "fixture only when the new provider shape is intentional"
    )


def _infer_entity(*, provider: str, probe: str) -> str:
    if provider in {"crossref", "openalex", "pubmed", "semanticscholar"}:
        return "publication"
    if provider == "pubchem":
        return "compound"
    if provider == "uniprot":
        return "taxonomy" if probe == "taxonomy_endpoint" else "protein"
    if provider == "chembl":
        for entity in ("activity", "molecule", "target"):
            if probe.startswith(entity):
                return entity
    return "unknown"


def _max_severity(severities: list[str]) -> str:
    if not severities:
        return _BENIGN_SEVERITY
    return max(severities, key=lambda value: _SEVERITY_RANK.get(value, -1))
