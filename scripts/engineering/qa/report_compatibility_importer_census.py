#!/usr/bin/env python3
"""Generate a deterministic importer census for retained seams and twin modules."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
DEFAULT_JSON_OUTPUT = (
    PROJECT_ROOT / "reports" / "quality" / "compatibility-importer-census.json"
)
DEFAULT_MD_OUTPUT = (
    PROJECT_ROOT / "reports" / "quality" / "compatibility-importer-census.md"
)
DEFAULT_TWIN_RATCHET = (
    PROJECT_ROOT / "configs" / "quality" / "compatibility_twin_module_ratchet.yaml"
)
DEFAULT_CONFIG_FACADE_RATCHET = (
    PROJECT_ROOT
    / "configs"
    / "quality"
    / "infrastructure_config_root_facade_inventory.yaml"
)
DEFAULT_CONTROL_PLANE_ROOT_FACADE = (
    PROJECT_ROOT
    / "configs"
    / "quality"
    / "application_control_plane_root_facade_inventory.yaml"
)
_INVENTORY_DOC_CELL_COUNT = 10
_DOC_METADATA_FIELDS = (
    "status",
    "canonical_target",
    "owner",
    "introduced_in",
    "review_date",
    "compatibility_role",
    "allowed_call_sites",
    "migration_path",
    "exit_criteria",
)
_CENSUS_METADATA_FIELDS = (
    "status",
    "canonical_target",
    "owner",
    "external_breaking_change_required",
    "internal_callers_zero",
    "usage_classification",
)
# Control-plane package owner identities (python:S1192).
OWNER_CONTROL_PLANE_REPLAY = "bioetl.application.services.control_plane.replay"
OWNER_CONTROL_PLANE_MANIFEST = "bioetl.application.services.control_plane.manifest"
OWNER_CONTROL_PLANE_WORKFLOW = "bioetl.application.services.control_plane.workflow"
COMPATIBILITY_FACADE_INVENTORY_YAML = "compatibility_facade_inventory.yaml"
ARTIFACT_COMPATIBILITY_CENSUS = "compatibility census"
REMOVED_COMPATIBILITY_SURFACES: tuple[dict[str, str], ...] = (
    {
        "issue_id": "4541",
        "surface_id": "historical_replay_certification_service",
        "path": "src/bioetl/application/services/control_plane/historical_replay_certification_service.py",
        "module_name": "bioetl.application.services.control_plane.historical_replay_certification_service",
        "canonical_target": "bioetl.application.services.control_plane.replay.historical_certification_service",
        "owner": OWNER_CONTROL_PLANE_REPLAY,
    },
    {
        "issue_id": "4541",
        "surface_id": "historical_replay_closure_models",
        "path": "src/bioetl/application/services/control_plane/historical_replay_closure_models.py",
        "module_name": "bioetl.application.services.control_plane.historical_replay_closure_models",
        "canonical_target": "bioetl.application.services.control_plane.replay.historical_closure_models",
        "owner": OWNER_CONTROL_PLANE_REPLAY,
    },
    {
        "issue_id": "4541",
        "surface_id": "historical_replay_closure_policy",
        "path": "src/bioetl/application/services/control_plane/historical_replay_closure_policy.py",
        "module_name": "bioetl.application.services.control_plane.historical_replay_closure_policy",
        "canonical_target": "bioetl.application.services.control_plane.replay.historical_closure_policy",
        "owner": OWNER_CONTROL_PLANE_REPLAY,
    },
    {
        "issue_id": "4541",
        "surface_id": "historical_replay_closure_service",
        "path": "src/bioetl/application/services/control_plane/historical_replay_closure_service.py",
        "module_name": "bioetl.application.services.control_plane.historical_replay_closure_service",
        "canonical_target": "bioetl.application.services.control_plane.replay.historical_closure_service",
        "owner": OWNER_CONTROL_PLANE_REPLAY,
    },
    {
        "issue_id": "4541",
        "surface_id": "historical_replay_corpus_models",
        "path": "src/bioetl/application/services/control_plane/historical_replay_corpus_models.py",
        "module_name": "bioetl.application.services.control_plane.historical_replay_corpus_models",
        "canonical_target": "bioetl.application.services.control_plane.replay.historical_corpus_models",
        "owner": OWNER_CONTROL_PLANE_REPLAY,
    },
    {
        "issue_id": "4541",
        "surface_id": "historical_replay_corpus_policy",
        "path": "src/bioetl/application/services/control_plane/historical_replay_corpus_policy.py",
        "module_name": "bioetl.application.services.control_plane.historical_replay_corpus_policy",
        "canonical_target": "bioetl.application.services.control_plane.replay.historical_corpus_policy",
        "owner": OWNER_CONTROL_PLANE_REPLAY,
    },
    {
        "issue_id": "4541",
        "surface_id": "historical_replay_corpus_service",
        "path": "src/bioetl/application/services/control_plane/historical_replay_corpus_service.py",
        "module_name": "bioetl.application.services.control_plane.historical_replay_corpus_service",
        "canonical_target": "bioetl.application.services.control_plane.replay.historical_corpus_service",
        "owner": OWNER_CONTROL_PLANE_REPLAY,
    },
    {
        "issue_id": "4541",
        "surface_id": "historical_replay_universe_policy",
        "path": "src/bioetl/application/services/control_plane/historical_replay_universe_policy.py",
        "module_name": "bioetl.application.services.control_plane.historical_replay_universe_policy",
        "canonical_target": "bioetl.application.services.control_plane.replay.historical_universe_policy",
        "owner": OWNER_CONTROL_PLANE_REPLAY,
    },
    {
        "issue_id": "4541",
        "surface_id": "historical_replay_universe_service",
        "path": "src/bioetl/application/services/control_plane/historical_replay_universe_service.py",
        "module_name": "bioetl.application.services.control_plane.historical_replay_universe_service",
        "canonical_target": "bioetl.application.services.control_plane.replay.historical_universe_service",
        "owner": OWNER_CONTROL_PLANE_REPLAY,
    },
    {
        "issue_id": "4541",
        "surface_id": "replay_bundle_descriptor_service",
        "path": "src/bioetl/application/services/control_plane/replay_bundle_descriptor_service.py",
        "module_name": "bioetl.application.services.control_plane.replay_bundle_descriptor_service",
        "canonical_target": "bioetl.application.services.control_plane.replay.bundle_descriptor_service",
        "owner": OWNER_CONTROL_PLANE_REPLAY,
    },
    {
        "issue_id": "4541",
        "surface_id": "run_manifest_diagnostics",
        "path": "src/bioetl/application/services/control_plane/run_manifest_diagnostics.py",
        "module_name": "bioetl.application.services.control_plane.run_manifest_diagnostics",
        "canonical_target": "bioetl.application.services.control_plane.manifest.diagnostics",
        "owner": OWNER_CONTROL_PLANE_MANIFEST,
    },
    {
        "issue_id": "4541",
        "surface_id": "run_manifest_inspection_service",
        "path": "src/bioetl/application/services/control_plane/run_manifest_inspection_service.py",
        "module_name": "bioetl.application.services.control_plane.run_manifest_inspection_service",
        "canonical_target": "bioetl.application.services.control_plane.manifest.inspection_service",
        "owner": OWNER_CONTROL_PLANE_MANIFEST,
    },
    {
        "issue_id": "4700",
        "surface_id": "run_manifest_replay_taxonomy",
        "path": "src/bioetl/application/services/control_plane/run_manifest_replay_taxonomy.py",
        "module_name": "bioetl.application.services.control_plane.run_manifest_replay_taxonomy",
        "canonical_target": "bioetl.application.services.control_plane.manifest.replay_taxonomy",
        "owner": OWNER_CONTROL_PLANE_MANIFEST,
    },
    {
        "issue_id": "4541",
        "surface_id": "workflow_execution_preparation",
        "path": "src/bioetl/application/services/control_plane/workflow_execution_preparation.py",
        "module_name": "bioetl.application.services.control_plane.workflow_execution_preparation",
        "canonical_target": "bioetl.application.services.control_plane.workflow.execution_preparation",
        "owner": OWNER_CONTROL_PLANE_WORKFLOW,
    },
    {
        "issue_id": "4541",
        "surface_id": "workflow_execution_recording",
        "path": "src/bioetl/application/services/control_plane/workflow_execution_recording.py",
        "module_name": "bioetl.application.services.control_plane.workflow_execution_recording",
        "canonical_target": "bioetl.application.services.control_plane.workflow.execution_recording",
        "owner": OWNER_CONTROL_PLANE_WORKFLOW,
    },
    {
        "issue_id": "4541",
        "surface_id": "workflow_execution_service",
        "path": "src/bioetl/application/services/control_plane/workflow_execution_service.py",
        "module_name": "bioetl.application.services.control_plane.workflow_execution_service",
        "canonical_target": "bioetl.application.services.control_plane.workflow.execution_service",
        "owner": OWNER_CONTROL_PLANE_WORKFLOW,
    },
    {
        "issue_id": "4541",
        "surface_id": "workflow_inspection_service",
        "path": "src/bioetl/application/services/control_plane/workflow_inspection_service.py",
        "module_name": "bioetl.application.services.control_plane.workflow_inspection_service",
        "canonical_target": "bioetl.application.services.control_plane.workflow.inspection_service",
        "owner": OWNER_CONTROL_PLANE_WORKFLOW,
    },
    {
        "issue_id": "4541",
        "surface_id": "workflow_ledger_service",
        "path": "src/bioetl/application/services/control_plane/workflow_ledger_service.py",
        "module_name": "bioetl.application.services.control_plane.workflow_ledger_service",
        "canonical_target": "bioetl.application.services.control_plane.workflow.ledger_service",
        "owner": OWNER_CONTROL_PLANE_WORKFLOW,
    },
    {
        "issue_id": "4541",
        "surface_id": "workflow_manifest_models",
        "path": "src/bioetl/application/services/control_plane/workflow_manifest_models.py",
        "module_name": "bioetl.application.services.control_plane.workflow_manifest_models",
        "canonical_target": "bioetl.application.services.control_plane.workflow.manifest_models",
        "owner": OWNER_CONTROL_PLANE_WORKFLOW,
    },
    {
        "issue_id": "4541",
        "surface_id": "workflow_manifest_service",
        "path": "src/bioetl/application/services/control_plane/workflow_manifest_service.py",
        "module_name": "bioetl.application.services.control_plane.workflow_manifest_service",
        "canonical_target": "bioetl.application.services.control_plane.workflow.manifest_service",
        "owner": OWNER_CONTROL_PLANE_WORKFLOW,
    },
    {
        "issue_id": "4390",
        "surface_id": "metadata_sidecar_adapter",
        "path": "src/bioetl/infrastructure/storage/silver/operations/metadata_sidecar_adapter.py",
        "module_name": "bioetl.infrastructure.storage.silver.operations.metadata_sidecar_adapter",
        "canonical_target": "bioetl.domain.ports.storage.metadata.MetadataCoordinatorPort",
        "owner": "bioetl.infrastructure.storage.silver.operations",
    },
    {
        "issue_id": "4388",
        "surface_id": "checkpoint_compatibility_service_v2",
        "path": "src/bioetl/application/services/checkpoint_compatibility_service_v2.py",
        "module_name": "bioetl.application.services.checkpoint_compatibility_service_v2",
        "canonical_target": "bioetl.application.services.checkpoint.checkpoint_compatibility_service",
        "owner": "bioetl.application.services",
    },
    {
        "issue_id": "4388",
        "surface_id": "legacy_fingerprints",
        "path": "src/bioetl/domain/normalization/legacy_fingerprints.py",
        "module_name": "bioetl.domain.normalization.legacy_fingerprints",
        "canonical_target": "bioetl.domain.normalization.fingerprints",
        "owner": "bioetl.domain.normalization",
    },
)


def _repo_relative_posix(path: Path, repo_root: Path) -> str:
    """Return repo-relative path serialized with stable POSIX separators."""
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        try:
            return path.relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            return path.as_posix()


def _resolve_inventory_path(repo_root: Path, default_path: Path) -> Path:
    """Prefer repo-local inventory files, but allow project defaults in tests."""
    repo_candidate = repo_root / "configs" / "quality" / default_path.name
    if repo_candidate.exists():
        return repo_candidate
    return default_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(PROJECT_ROOT))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-out", default=str(DEFAULT_MD_OUTPUT))
    parser.add_argument("--snapshot-date", default=None)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when committed compatibility census artifacts drift.",
    )
    return parser.parse_args()


def _existing_snapshot_date(path: Path) -> str | None:
    from scripts.engineering.common.repo_paths import resolve_output_path

    safe_path = resolve_output_path(path)
    if not safe_path.exists():
        return None
    payload = json.loads(safe_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    snapshot_date = payload.get("snapshot_date")
    return snapshot_date if isinstance(snapshot_date, str) else None


def _load_retained_entrypoints(path: Path) -> list[dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    rows = payload.get("retained_entrypoints", [])
    assert isinstance(rows, list)
    return [row for row in rows if isinstance(row, dict)]


def _load_first_safe_removal_wave(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    first_wave = payload.get("first_safe_removal_wave", {})
    assert isinstance(first_wave, dict)
    rows = first_wave.get("rows", [])
    assert isinstance(rows, list)
    return {
        "linked_issue": first_wave.get("linked_issue"),
        "review_date": first_wave.get("review_date"),
        "rows": [row for row in rows if isinstance(row, dict)],
    }


def _load_tracked_twin_families(path: Path) -> list[dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    rows = payload.get("families", [])
    assert isinstance(rows, list)
    return [row for row in rows if isinstance(row, dict)]


def _load_config_root_facade_inventory(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_root_facade_inventory(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _usage_classification(row: dict[str, Any]) -> str:
    external_breaking_change_required = bool(
        row.get("external_breaking_change_required")
    )
    internal_callers_zero = bool(row.get("internal_callers_zero"))
    if external_breaking_change_required and internal_callers_zero:
        return "stable_public_api_zero_first_party_src"
    if external_breaking_change_required:
        return "stable_public_api_with_reviewed_first_party_usage"
    return "compatibility_surface_under_active_migration"


def _load_mapping(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a mapping root")
    return payload


def _mapping_rows(
    payload: dict[str, Any], section_name: str
) -> tuple[dict[str, Any], ...]:
    rows = payload.get(section_name, [])
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"{section_name} must contain a list of mappings")
    return tuple(rows)


def _parse_inventory_doc_line(line: str) -> dict[str, Any] | None:
    stripped = line.strip()
    if not stripped.startswith("| `src/bioetl/"):
        return None
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    if len(cells) != _INVENTORY_DOC_CELL_COUNT:
        raise ValueError(f"Unexpected compatibility inventory row format: {line}")
    return {
        "path": cells[0].strip("`"),
        "compatibility_role": cells[1],
        "canonical_target": cells[2].strip("`"),
        "status": cells[3].strip("`"),
        "owner": cells[4].strip("`"),
        "introduced_in": cells[5].strip("`"),
        "allowed_call_sites": cells[6],
        "review_date": cells[7].strip("`"),
        "migration_path": cells[8],
        "exit_criteria": cells[9],
    }


def _index_metadata_rows(
    rows: tuple[dict[str, Any], ...], *, artifact_name: str
) -> dict[str, dict[str, Any]]:
    paths = tuple(str(row.get("path", "")) for row in rows)
    if any(not path for path in paths):
        raise ValueError(f"{artifact_name} contains a row without a path")
    indexed = dict(zip(paths, rows, strict=True))
    if len(indexed) != len(rows):
        raise ValueError(f"{artifact_name} contains duplicate paths")
    return indexed


def _load_inventory_doc_rows(path: Path) -> dict[str, dict[str, Any]]:
    parsed_rows = tuple(
        parsed
        for line in path.read_text(encoding="utf-8").splitlines()
        if (parsed := _parse_inventory_doc_line(line)) is not None
    )
    return _index_metadata_rows(parsed_rows, artifact_name=path.as_posix())


def _normalize_metadata_value(value: Any) -> Any:
    if isinstance(value, str):
        return " ".join(value.split())
    return value


def _row_set_mismatches(
    *,
    artifact_name: str,
    expected_rows: dict[str, dict[str, Any]],
    actual_rows: dict[str, dict[str, Any]],
) -> tuple[str, ...]:
    missing = tuple(sorted(expected_rows.keys() - actual_rows.keys()))
    unexpected = tuple(sorted(actual_rows.keys() - expected_rows.keys()))
    return tuple(
        [f"{artifact_name}: missing row {path}" for path in missing]
        + [f"{artifact_name}: unexpected row {path}" for path in unexpected]
    )


def _field_mismatches(
    *,
    artifact_name: str,
    expected_rows: dict[str, dict[str, Any]],
    actual_rows: dict[str, dict[str, Any]],
    fields: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(
        f"{artifact_name}: {path}.{field}: expected "
        f"{expected_rows[path].get(field)!r}, got {actual_rows[path].get(field)!r}"
        for path in sorted(expected_rows.keys() & actual_rows.keys())
        for field in fields
        if _normalize_metadata_value(expected_rows[path].get(field))
        != _normalize_metadata_value(actual_rows[path].get(field))
    )


def _expected_census_rows(
    retained_rows: tuple[dict[str, Any], ...],
) -> dict[str, dict[str, Any]]:
    return {
        str(row["path"]): {
            **row,
            "usage_classification": _usage_classification(row),
        }
        for row in retained_rows
    }


def _zero_caller_mismatches(
    *,
    expected_rows: dict[str, dict[str, Any]],
    census_rows: dict[str, dict[str, Any]],
) -> tuple[str, ...]:
    return tuple(
        "compatibility census: "
        f"{path} is internal_callers_zero but reports "
        f"{census_rows[path].get('src_importer_count')} src importer(s)"
        for path in sorted(expected_rows.keys() & census_rows.keys())
        if bool(expected_rows[path].get("internal_callers_zero"))
        and census_rows[path].get("src_importer_count") != 0
    )


def validate_compatibility_metadata_consistency(
    repo_root: Path,
    *,
    census_payload: dict[str, object],
) -> tuple[str, ...]:
    """Validate registry, curated docs, and census semantic parity."""
    registry_payload = _load_mapping(
        repo_root / "configs" / "quality" / COMPATIBILITY_FACADE_INVENTORY_YAML
    )
    transition_rows = _mapping_rows(registry_payload, "transition_debt")
    retained_rows = _mapping_rows(registry_payload, "retained_entrypoints")
    registry_doc_rows = _index_metadata_rows(
        (*transition_rows, *retained_rows),
        artifact_name="compatibility registry",
    )
    inventory_doc_rows = _load_inventory_doc_rows(
        repo_root / "docs" / "02-architecture" / "07-compatibility-facade-inventory.md"
    )
    expected_census_rows = _expected_census_rows(retained_rows)
    census_rows = _index_metadata_rows(
        _mapping_rows(census_payload, "retained_entrypoints"),
        artifact_name=ARTIFACT_COMPATIBILITY_CENSUS,
    )
    return (
        *_row_set_mismatches(
            artifact_name="compatibility inventory doc",
            expected_rows=registry_doc_rows,
            actual_rows=inventory_doc_rows,
        ),
        *_field_mismatches(
            artifact_name="compatibility inventory doc",
            expected_rows=registry_doc_rows,
            actual_rows=inventory_doc_rows,
            fields=_DOC_METADATA_FIELDS,
        ),
        *_row_set_mismatches(
            artifact_name=ARTIFACT_COMPATIBILITY_CENSUS,
            expected_rows=expected_census_rows,
            actual_rows=census_rows,
        ),
        *_field_mismatches(
            artifact_name=ARTIFACT_COMPATIBILITY_CENSUS,
            expected_rows=expected_census_rows,
            actual_rows=census_rows,
            fields=_CENSUS_METADATA_FIELDS,
        ),
        *_zero_caller_mismatches(
            expected_rows=expected_census_rows,
            census_rows=census_rows,
        ),
    )


def _print_semantic_consistency_violations(violations: tuple[str, ...]) -> None:
    print("[compatibility-importer-census] FAIL: metadata semantic drift")
    for violation in violations:
        print(f"  - {violation}")


def _surface_classification(
    row: dict[str, Any],
    *,
    src_importer_count: int,
) -> str:
    if str(row.get("status")) != "public-entrypoint":
        return "transitional"
    if src_importer_count > 0:
        return "first-party-active"
    if bool(row.get("external_breaking_change_required")):
        return "external-facing"
    return "confirmed-unused"


def _module_name_from_repo_path(repo_path: str) -> str:
    normalized = repo_path.removeprefix("src/").removesuffix(".py")
    if normalized.endswith("/__init__"):
        normalized = normalized[: -len("/__init__")]
    return normalized.replace("/", ".")


def _parse_module(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())


def _string_literals_from_sequence(node: ast.AST) -> list[str]:
    if not isinstance(node, ast.List | ast.Tuple):
        return []
    values: list[str] = []
    for element in node.elts:
        if isinstance(element, ast.Constant) and isinstance(element.value, str):
            values.append(element.value)
    return values


def _top_level_string_sequence_assignment(
    tree: ast.Module, target_name: str
) -> list[str]:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == target_name
            for target in node.targets
        ):
            continue
        values = _string_literals_from_sequence(node.value)
        if values:
            return values
    return []


def _dict_string_keys(dict_node: ast.Dict) -> list[str]:
    """Extract string constant keys from a dict AST node."""
    keys: list[str] = []
    for key in dict_node.keys:
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            keys.append(key.value)
    return keys


def _assign_targets_name(node: ast.Assign, target_name: str) -> bool:
    """True when any assignment target is the given bare name."""
    return any(
        isinstance(target, ast.Name) and target.id == target_name
        for target in node.targets
    )


def _top_level_dict_node(tree: ast.Module, target_name: str) -> ast.Dict | None:
    """Locate a top-level dict assignment (plain or annotated) by name."""
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if _assign_targets_name(node, target_name) and isinstance(
                node.value, ast.Dict
            ):
                return node.value
            continue
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == target_name
            and isinstance(node.value, ast.Dict)
        ):
            return node.value
    return None


def _top_level_dict_string_keys(tree: ast.Module, target_name: str) -> list[str]:
    dict_node = _top_level_dict_node(tree, target_name)
    if dict_node is None:
        return []
    return _dict_string_keys(dict_node)


def _binding_names_from_node(node: ast.stmt) -> set[str]:
    """Extract top-level binding names introduced by one module body node."""
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        return {node.name}
    if isinstance(node, ast.ImportFrom):
        return {alias.asname or alias.name for alias in node.names}
    if isinstance(node, ast.Assign):
        return {target.id for target in node.targets if isinstance(target, ast.Name)}
    if (
        isinstance(node, ast.AnnAssign)
        and node.value is not None
        and isinstance(node.target, ast.Name)
    ):
        return {node.target.id}
    return set()


def _collect_runtime_binding_names(tree: ast.Module) -> set[str]:
    bindings: set[str] = set()
    for node in tree.body:
        bindings.update(_binding_names_from_node(node))
    return bindings


def _collect_public_top_level_function_names(tree: ast.Module) -> list[str]:
    names: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if node.name.startswith("_"):
            continue
        names.append(node.name)
    return names


def _name_eq_string_literal(test: ast.AST) -> str | None:
    """Return the string literal when test is `name == \"...\"`, else None."""
    if not isinstance(test, ast.Compare):
        return None
    if not isinstance(test.left, ast.Name) or test.left.id != "name":
        return None
    if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
        return None
    if len(test.comparators) != 1:
        return None
    comparator = test.comparators[0]
    if not isinstance(comparator, ast.Constant) or not isinstance(
        comparator.value, str
    ):
        return None
    return comparator.value


def _visit_getattr_if_chain(node: ast.If, names: set[str]) -> None:
    """Collect name==\"...\" branch literals from an if/elif chain."""
    literal = _name_eq_string_literal(node.test)
    if literal is not None:
        names.add(literal)
    for child in node.orelse:
        if isinstance(child, ast.If):
            _visit_getattr_if_chain(child, names)


def _collect_getattr_branch_names(tree: ast.Module) -> set[str]:
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name != "__getattr__":
            continue
        names: set[str] = set()
        for child in node.body:
            if isinstance(child, ast.If):
                _visit_getattr_if_chain(child, names)
        return names
    return set()


def _duplicates(values: list[str]) -> list[str]:
    counts = Counter(values)
    return sorted(name for name, count in counts.items() if count > 1)


def _export_resolution_providers(
    export_name: str,
    *,
    runtime_bindings: set[str],
    lazy_export_keys: list[str],
    getattr_branch_names: list[str],
) -> list[str]:
    providers: list[str] = []
    if export_name in runtime_bindings:
        providers.append("runtime_binding")
    if export_name in lazy_export_keys:
        providers.append("lazy_export_table")
    if export_name in getattr_branch_names:
        providers.append("dunder_getattr_branch")
    return providers


def _resolution_conflicts_for_exports(
    public_exports: list[str],
    *,
    runtime_bindings: set[str],
    lazy_export_keys: list[str],
    getattr_branch_names: list[str],
) -> dict[str, list[str]]:
    resolution_conflicts: dict[str, list[str]] = {}
    for export_name in public_exports:
        providers = _export_resolution_providers(
            export_name,
            runtime_bindings=runtime_bindings,
            lazy_export_keys=lazy_export_keys,
            getattr_branch_names=getattr_branch_names,
        )
        if len(providers) != 1:
            resolution_conflicts[export_name] = providers
    return resolution_conflicts


def _build_public_export_contract_row(
    module_path: Path,
    inventory_row: dict[str, Any],
) -> dict[str, object]:
    tree = _parse_module(module_path)
    export_contract = inventory_row["public_export_contract"]
    assert isinstance(export_contract, dict)
    public_exports = _top_level_string_sequence_assignment(tree, "__all__")
    lazy_export_table_name = export_contract.get("lazy_export_table")
    lazy_export_keys = (
        _top_level_dict_string_keys(tree, str(lazy_export_table_name))
        if isinstance(lazy_export_table_name, str)
        else []
    )
    getattr_branch_names = (
        sorted(_collect_getattr_branch_names(tree))
        if bool(export_contract.get("parse_dunder_getattr_string_branches"))
        else []
    )
    retained_wrapper_contract = sorted(
        str(name) for name in export_contract.get("retained_wrappers_outside_all", [])
    )
    runtime_bindings = _collect_runtime_binding_names(tree)
    public_function_bindings = set(_collect_public_top_level_function_names(tree))
    resolution_conflicts = _resolution_conflicts_for_exports(
        public_exports,
        runtime_bindings=runtime_bindings,
        lazy_export_keys=lazy_export_keys,
        getattr_branch_names=getattr_branch_names,
    )
    public_export_set = set(public_exports)
    lazy_resolution_exports = set(lazy_export_keys) | set(getattr_branch_names)
    retained_wrappers_outside_all = sorted(
        public_function_bindings - lazy_resolution_exports
    )
    return {
        "path": inventory_row["path"],
        "module_name": _module_name_from_repo_path(str(inventory_row["path"])),
        "canonical_target": inventory_row["canonical_target"],
        "max_public_exports": int(export_contract["max_public_exports"]),
        "public_exports": public_exports,
        "public_export_count": len(public_exports),
        "duplicate_public_exports": _duplicates(public_exports),
        "lazy_export_table": lazy_export_table_name,
        "lazy_export_keys": lazy_export_keys,
        "duplicate_lazy_export_keys": _duplicates(lazy_export_keys),
        "orphan_lazy_export_keys": sorted(set(lazy_export_keys) - public_export_set),
        "dunder_getattr_exports": getattr_branch_names,
        "orphan_dunder_getattr_exports": sorted(
            set(getattr_branch_names) - public_export_set
        ),
        "retained_wrapper_contract": retained_wrapper_contract,
        "retained_wrappers_outside_all": retained_wrappers_outside_all,
        "missing_retained_wrappers_outside_all": sorted(
            set(retained_wrapper_contract) - set(retained_wrappers_outside_all)
        ),
        "unexpected_retained_wrappers_outside_all": sorted(
            set(retained_wrappers_outside_all) - set(retained_wrapper_contract)
        ),
        "resolution_conflicts": resolution_conflicts,
    }


_PUBLIC_EXPORT_ROW_KEYS = frozenset(
    {
        "path",
        "module_name",
        "canonical_target",
        "max_public_exports",
        "public_exports",
        "public_export_count",
        "duplicate_public_exports",
        "lazy_export_table",
        "lazy_export_keys",
        "duplicate_lazy_export_keys",
        "orphan_lazy_export_keys",
        "dunder_getattr_exports",
        "orphan_dunder_getattr_exports",
        "retained_wrapper_contract",
        "retained_wrappers_outside_all",
        "missing_retained_wrappers_outside_all",
        "unexpected_retained_wrappers_outside_all",
        "resolution_conflicts",
    }
)


def _build_removed_surface_rows(
    repo_root: Path,
    collect_exact_module_import_usage: Any,
) -> list[dict[str, object]]:
    removed_surface_rows: list[dict[str, object]] = []
    for row in REMOVED_COMPATIBILITY_SURFACES:
        usage = collect_exact_module_import_usage(repo_root, row["module_name"])
        src_importers = sorted(usage["src"])
        test_importers = sorted(usage["tests"])
        removed_surface_rows.append(
            {
                **row,
                "path_exists": (repo_root / row["path"]).exists(),
                "src_importers": src_importers,
                "test_importers": test_importers,
                "src_importer_count": len(src_importers),
                "test_importer_count": len(test_importers),
            }
        )
    return removed_surface_rows


def _public_export_owner_usage_row(
    retained_row: dict[str, object],
) -> dict[str, object]:
    return {
        **{
            key: value
            for key, value in retained_row.items()
            if key in _PUBLIC_EXPORT_ROW_KEYS
        },
        "owner": retained_row["owner"],
        "status": retained_row["status"],
        "external_breaking_change_required": retained_row[
            "external_breaking_change_required"
        ],
        "internal_callers_zero": retained_row["internal_callers_zero"],
        "usage_classification": retained_row["usage_classification"],
        "surface_classification": retained_row["surface_classification"],
        "consumer_class": retained_row["consumer_class"],
        "sunset_status": retained_row["sunset_status"],
        "src_importer_count": retained_row["src_importer_count"],
        "test_importer_count": retained_row["test_importer_count"],
    }


def _retained_entrypoint_base_row(
    row: dict[str, Any], *, importer_map: dict[str, Any]
) -> dict[str, object]:
    repo_path = str(row["path"])
    module_name = _module_name_from_repo_path(repo_path)
    importers = importer_map.get(module_name, {"src": (), "tests": ()})
    src_importers = list(importers.get("src", ()))
    test_importers = list(importers.get("tests", ()))
    src_importer_count = len(src_importers)
    retained_row: dict[str, object] = {
        "path": repo_path,
        "module_name": module_name,
        "status": row.get("status"),
        "canonical_target": row.get("canonical_target"),
        "owner": row.get("owner"),
        "external_breaking_change_required": bool(
            row.get("external_breaking_change_required")
        ),
        "internal_callers_zero": bool(row.get("internal_callers_zero")),
        "usage_classification": _usage_classification(row),
        "src_importers": src_importers,
        "test_importers": test_importers,
        "src_importer_count": src_importer_count,
        "test_importer_count": len(test_importers),
    }
    retained_row["surface_classification"] = _surface_classification(
        row,
        src_importer_count=src_importer_count,
    )
    retained_row["consumer_class"] = retained_row["usage_classification"]
    retained_row["sunset_status"] = retained_row["surface_classification"]
    return retained_row


def _attach_public_export_contract(
    repo_root: Path,
    inventory_row: dict[str, Any],
    retained_row: dict[str, object],
) -> dict[str, object] | None:
    export_contract = inventory_row.get("public_export_contract")
    if not isinstance(export_contract, dict):
        return None
    export_row = _build_public_export_contract_row(
        repo_root / str(inventory_row["path"]), inventory_row
    )
    retained_row.update(
        {
            key: value
            for key, value in export_row.items()
            if key not in {"path", "module_name", "canonical_target"}
        }
    )
    return _public_export_owner_usage_row(retained_row)


def _build_retained_rows(
    repo_root: Path,
    retained_entrypoints: list[dict[str, Any]],
    importer_map: dict[str, Any],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    retained_rows: list[dict[str, object]] = []
    retained_public_export_rows: list[dict[str, object]] = []
    for row in retained_entrypoints:
        retained_row = _retained_entrypoint_base_row(row, importer_map=importer_map)
        export_owner_row = _attach_public_export_contract(repo_root, row, retained_row)
        if export_owner_row is not None:
            retained_public_export_rows.append(export_owner_row)
        retained_rows.append(retained_row)
    return retained_rows, retained_public_export_rows


def _build_first_safe_removal_wave_rows(
    first_safe_removal_wave: dict[str, Any],
    importer_map: dict[str, Any],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in first_safe_removal_wave["rows"]:
        repo_path = str(row["path"])
        module_name = _module_name_from_repo_path(repo_path)
        importers = importer_map.get(module_name, {"src": (), "tests": ()})
        rows.append(
            {
                "path": repo_path,
                "module_name": module_name,
                "owner": row.get("owner"),
                "previous_status": row.get("previous_status"),
                "surface_classification": row.get(
                    "surface_classification",
                    "confirmed-unused",
                ),
                "action": row.get("action"),
                "rationale": row.get("rationale"),
                "migration_prerequisites": list(row.get("migration_prerequisites", [])),
                "src_importers": list(importers.get("src", ())),
                "test_importers": list(importers.get("tests", ())),
                "src_importer_count": len(importers.get("src", ())),
                "test_importer_count": len(importers.get("tests", ())),
            }
        )
    return rows


def _build_twin_rows(
    twin_pairs: list[dict[str, Any]],
    importer_map: dict[str, Any],
) -> list[dict[str, object]]:
    twin_rows: list[dict[str, object]] = []
    for pair in twin_pairs:
        public_importers = importer_map.get(
            pair.get("public_module", ""), {"src": (), "tests": ()}
        )
        private_importers = importer_map.get(
            pair.get("private_module", ""), {"src": (), "tests": ()}
        )
        twin_rows.append(
            {
                **pair,
                "public_src_importer_count": len(public_importers.get("src", ())),
                "public_test_importer_count": len(public_importers.get("tests", ())),
                "private_src_importer_count": len(private_importers.get("src", ())),
                "private_test_importer_count": len(private_importers.get("tests", ())),
                "public_src_importers": list(public_importers.get("src", ())),
                "private_src_importers": list(private_importers.get("src", ())),
            }
        )
    return twin_rows


def _build_tracked_twin_rows(
    tracked_twin_families: list[dict[str, Any]],
    twin_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    twin_rows_by_public_module = {
        str(row["public_module"]): row for row in twin_rows if isinstance(row, dict)
    }
    tracked_twin_rows: list[dict[str, object]] = []
    for family in tracked_twin_families:
        public_module = str(family.get("public_module", ""))
        live_row = twin_rows_by_public_module.get(public_module)
        if live_row is None:
            continue
        tracked_twin_rows.append(
            {
                **family,
                "current_public_src_importer_count": live_row[
                    "public_src_importer_count"
                ],
                "current_private_src_importer_count": live_row[
                    "private_src_importer_count"
                ],
                "current_public_src_importers": live_row["public_src_importers"],
                "current_private_src_importers": live_row["private_src_importers"],
            }
        )
    return tracked_twin_rows


def _build_config_symbol_rows(
    config_root_facade_inventory: dict[str, Any],
    config_root_usage: dict[str, Any],
) -> list[dict[str, object]]:
    configured_symbols = config_root_facade_inventory["symbols"]
    assert isinstance(configured_symbols, list)
    configured_symbols_by_name = {
        str(row["symbol"]): row for row in configured_symbols if isinstance(row, dict)
    }
    config_src_usage = config_root_usage["src"]
    config_symbol_paths: dict[str, list[str]] = {}
    for importer_path, imported_names in config_src_usage.items():
        for imported_name in imported_names:
            config_symbol_paths.setdefault(imported_name, []).append(importer_path)

    config_symbol_rows: list[dict[str, object]] = []
    for symbol_name, row in configured_symbols_by_name.items():
        current_paths = sorted(config_symbol_paths.get(symbol_name, []))
        config_symbol_rows.append(
            {
                **row,
                "current_src_importer_count": len(current_paths),
                "current_src_importers": current_paths,
            }
        )
    return config_symbol_rows


def _census_summary(
    *,
    retained_rows: list[dict[str, object]],
    removed_surface_rows: list[dict[str, object]],
    twin_rows: list[dict[str, object]],
    tracked_twin_rows: list[dict[str, object]],
    config_symbol_rows: list[dict[str, object]],
    config_src_usage: dict[str, Any],
    control_plane_root_usage: dict[str, Any],
    retained_public_export_rows: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "retained_entrypoint_count": len(retained_rows),
        "retained_public_entrypoint_burden": sum(
            _int_row_value(row, "src_importer_count") for row in retained_rows
        ),
        "removed_compatibility_surface_count": len(removed_surface_rows),
        "removed_compatibility_surfaces_with_src_importers": sum(
            1
            for row in removed_surface_rows
            if _int_row_value(row, "src_importer_count") > 0
        ),
        "removed_compatibility_surfaces_with_test_importers": sum(
            1
            for row in removed_surface_rows
            if _int_row_value(row, "test_importer_count") > 0
        ),
        "removed_compatibility_surfaces_still_present": sum(
            1 for row in removed_surface_rows if row["path_exists"]
        ),
        "twin_pair_count": len(twin_rows),
        "twin_pairs_with_private_src_importers": sum(
            1
            for row in twin_rows
            if _int_row_value(row, "private_src_importer_count") > 0
        ),
        "twin_pairs_without_public_src_importers": sum(
            1
            for row in twin_rows
            if _int_row_value(row, "public_src_importer_count") == 0
        ),
        "tracked_twin_family_count": len(tracked_twin_rows),
        "config_root_symbol_count": len(config_symbol_rows),
        "config_root_src_importer_count": len(config_src_usage),
        "control_plane_root_src_importer_count": len(control_plane_root_usage["src"]),
        "retained_public_export_facade_count": len(retained_public_export_rows),
        "retained_public_export_facades_with_duplicate_exports": sum(
            1
            for row in retained_public_export_rows
            if row["duplicate_public_exports"] or row["duplicate_lazy_export_keys"]
        ),
        "retained_public_export_facades_with_resolution_conflicts": sum(
            1 for row in retained_public_export_rows if row["resolution_conflicts"]
        ),
        "retained_public_export_facades_with_wrapper_contract_drift": sum(
            1
            for row in retained_public_export_rows
            if row["missing_retained_wrappers_outside_all"]
            or row["unexpected_retained_wrappers_outside_all"]
        ),
    }


def _int_row_value(row: dict[str, object], key: str) -> int:
    """Return one validated integer field from a generated census row."""
    value = row.get(key)
    return value if isinstance(value, int) else 0


def build_compatibility_importer_census(
    repo_root: Path, *, snapshot_date: str | None = None
) -> dict[str, object]:
    """Build a deterministic importer census for retained seams and twin modules.

    NOSONAR - S3776: complexity 28 exceeds 15; extraction would obscure compatibility census logic
    """
    from scripts.engineering.qa.import_graph_inventory import (
        collect_bioetl_importers,
        collect_exact_module_import_usage,
        find_public_private_twin_modules,
    )

    importer_map = collect_bioetl_importers(repo_root)
    retained_entrypoints = _load_retained_entrypoints(
        repo_root / "configs" / "quality" / COMPATIBILITY_FACADE_INVENTORY_YAML
    )
    first_safe_removal_wave = _load_first_safe_removal_wave(
        repo_root / "configs" / "quality" / COMPATIBILITY_FACADE_INVENTORY_YAML
    )
    twin_pairs = find_public_private_twin_modules(repo_root)
    twin_ratchet_path = _resolve_inventory_path(repo_root, DEFAULT_TWIN_RATCHET)
    tracked_twin_families = _load_tracked_twin_families(twin_ratchet_path)
    config_root_facade_path = _resolve_inventory_path(
        repo_root, DEFAULT_CONFIG_FACADE_RATCHET
    )
    config_root_facade_inventory = _load_config_root_facade_inventory(
        config_root_facade_path
    )
    control_plane_root_facade_path = _resolve_inventory_path(
        repo_root, DEFAULT_CONTROL_PLANE_ROOT_FACADE
    )
    control_plane_root_facade_inventory = _load_root_facade_inventory(
        control_plane_root_facade_path
    )
    config_root_usage = collect_exact_module_import_usage(
        repo_root,
        str(config_root_facade_inventory["target_module"]),
    )
    control_plane_root_usage = collect_exact_module_import_usage(
        repo_root,
        str(control_plane_root_facade_inventory["target_module"]),
    )
    removed_surface_rows = _build_removed_surface_rows(
        repo_root, collect_exact_module_import_usage
    )
    retained_rows, retained_public_export_rows = _build_retained_rows(
        repo_root, retained_entrypoints, importer_map
    )
    first_safe_removal_wave_rows = _build_first_safe_removal_wave_rows(
        first_safe_removal_wave, importer_map
    )
    twin_rows = _build_twin_rows(twin_pairs, importer_map)
    tracked_twin_rows = _build_tracked_twin_rows(tracked_twin_families, twin_rows)
    config_symbol_rows = _build_config_symbol_rows(
        config_root_facade_inventory, config_root_usage
    )

    return {
        "snapshot_date": snapshot_date or date.today().isoformat(),
        "inventory_source": f"configs/quality/{COMPATIBILITY_FACADE_INVENTORY_YAML}",
        "twin_ratchet_source": _repo_relative_posix(twin_ratchet_path, repo_root),
        "config_root_facade_source": _repo_relative_posix(
            config_root_facade_path,
            repo_root,
        ),
        "control_plane_root_facade_source": _repo_relative_posix(
            control_plane_root_facade_path,
            repo_root,
        ),
        "summary": _census_summary(
            retained_rows=retained_rows,
            removed_surface_rows=removed_surface_rows,
            twin_rows=twin_rows,
            tracked_twin_rows=tracked_twin_rows,
            config_symbol_rows=config_symbol_rows,
            config_src_usage=config_root_usage["src"],
            control_plane_root_usage=control_plane_root_usage,
            retained_public_export_rows=retained_public_export_rows,
        ),
        "retained_entrypoints": retained_rows,
        "retained_entrypoint_owner_usage_map": retained_rows,
        "retained_public_export_facades": retained_public_export_rows,
        "retained_public_export_owner_usage_map": retained_public_export_rows,
        "first_safe_removal_wave": {
            "linked_issue": first_safe_removal_wave["linked_issue"],
            "review_date": first_safe_removal_wave["review_date"],
            "rows": first_safe_removal_wave_rows,
        },
        "removed_compatibility_surfaces": removed_surface_rows,
        "twin_pairs": twin_rows,
        "tracked_twin_families": tracked_twin_rows,
        "config_root_facade": {
            "target_module": config_root_facade_inventory["target_module"],
            "new_src_import_policy": config_root_facade_inventory[
                "new_src_import_policy"
            ],
            "symbols": config_symbol_rows,
        },
        "control_plane_root_facade": {
            "target_module": control_plane_root_facade_inventory["target_module"],
            "new_src_import_policy": control_plane_root_facade_inventory[
                "new_src_import_policy"
            ],
            "owner": control_plane_root_facade_inventory.get("owner"),
            "src_importers": sorted(control_plane_root_usage["src"]),
            "src_importer_count": len(control_plane_root_usage["src"]),
        },
    }


def _md_yes_no(value: object) -> str:
    """Render a boolean-ish value as yes/no for markdown tables."""
    return "yes" if value else "no"


def _md_join_or_none(values: object) -> str:
    """Join string-ish values for a markdown cell, or ``none`` when empty."""
    if not values:
        return "none"
    if isinstance(values, (list, tuple, set)):
        rendered = [str(item) for item in values]
        return ", ".join(rendered) if rendered else "none"
    return str(values)


def _md_summary_lines(
    payload: dict[str, object], summary: dict[str, object]
) -> list[str]:
    """Render the census summary bullet list."""
    return [
        "# Compatibility Importer Census",
        "",
        f"- snapshot_date: {payload['snapshot_date']}",
        f"- retained_entrypoint_count: {summary['retained_entrypoint_count']}",
        "- retained_public_entrypoint_burden: "
        f"{summary['retained_public_entrypoint_burden']}",
        f"- removed_compatibility_surface_count: {summary['removed_compatibility_surface_count']}",
        "- removed_compatibility_surfaces_with_src_importers: "
        f"{summary['removed_compatibility_surfaces_with_src_importers']}",
        "- removed_compatibility_surfaces_with_test_importers: "
        f"{summary['removed_compatibility_surfaces_with_test_importers']}",
        f"- removed_compatibility_surfaces_still_present: {summary['removed_compatibility_surfaces_still_present']}",
        f"- twin_pair_count: {summary['twin_pair_count']}",
        f"- tracked_twin_family_count: {summary['tracked_twin_family_count']}",
        f"- config_root_symbol_count: {summary['config_root_symbol_count']}",
        f"- config_root_src_importer_count: {summary['config_root_src_importer_count']}",
        "- control_plane_root_src_importer_count: "
        f"{summary['control_plane_root_src_importer_count']}",
        f"- retained_public_export_facade_count: {summary['retained_public_export_facade_count']}",
        "- retained_public_export_facades_with_duplicate_exports: "
        f"{summary['retained_public_export_facades_with_duplicate_exports']}",
        "- retained_public_export_facades_with_resolution_conflicts: "
        f"{summary['retained_public_export_facades_with_resolution_conflicts']}",
        "- retained_public_export_facades_with_wrapper_contract_drift: "
        f"{summary['retained_public_export_facades_with_wrapper_contract_drift']}",
        "- purpose: measure sanctioned public seams and underscore/public twin usage",
    ]


def _md_retained_entrypoint_lines(retained_rows: list[object]) -> list[str]:
    lines = [
        "",
        "## Retained Entrypoints",
        "",
        "| Path | src importers | test importers |",
        "| --- | ---: | ---: |",
    ]
    for row in retained_rows:
        assert isinstance(row, dict)
        lines.append(
            f"| `{row['path']}` | {row['src_importer_count']} | {row['test_importer_count']} |"
        )
    return lines


def _md_retained_owner_usage_lines(
    retained_owner_usage_rows: list[object],
) -> list[str]:
    lines = [
        "",
        "## Retained Entrypoint Owner/Usage Map",
        "",
        "| Path | Owner | Usage classification | Surface classification | Internal callers zero | "
        "External breaking change required | src importers | test importers |",
        "| --- | --- | --- | --- | --- | --- | ---: | ---: |",
    ]
    for row in retained_owner_usage_rows:
        assert isinstance(row, dict)
        lines.append(
            f"| `{row['path']}` | `{row['owner']}` | `{row['usage_classification']}` | "
            f"`{row['surface_classification']}` | "
            f"{_md_yes_no(row['internal_callers_zero'])} | "
            f"{_md_yes_no(row['external_breaking_change_required'])} | "
            f"{row['src_importer_count']} | {row['test_importer_count']} |"
        )
    return lines


def _md_public_export_wrapper_cell(row: dict[str, object]) -> str:
    """Render retained-wrapper + drift cell for a public export facade row."""
    wrapper_names = sorted(_string_values(row.get("retained_wrappers_outside_all")))
    wrapper_drift = sorted(
        _string_values(row.get("missing_retained_wrappers_outside_all"))
        | _string_values(row.get("unexpected_retained_wrappers_outside_all"))
    )
    wrapper_cell = ", ".join(wrapper_names) if wrapper_names else "none"
    if wrapper_drift:
        wrapper_cell = f"{wrapper_cell} (drift: {', '.join(wrapper_drift)})"
    return wrapper_cell


def _string_values(value: object) -> set[str]:
    """Narrow a generated sequence-like field to its string members."""
    if not isinstance(value, (list, tuple, set)):
        return set()
    return {item for item in value if isinstance(item, str)}


def _md_public_export_lines(public_export_rows: list[object]) -> list[str]:
    lines = [
        "",
        "## Retained Public Export Facades",
        "",
        "| Path | Public exports | Lazy exports | Retained wrappers outside "
        "`__all__` | Duplicate exports | Resolution conflicts |",
        "| --- | ---: | ---: | --- | --- | --- |",
    ]
    for row in public_export_rows:
        assert isinstance(row, dict)
        duplicate_exports = sorted(
            set(row["duplicate_public_exports"])
            | set(row["duplicate_lazy_export_keys"])
        )
        conflicts = sorted(row["resolution_conflicts"])
        lines.append(
            f"| `{row['path']}` | {row['public_export_count']} | "
            f"{len(row['lazy_export_keys']) + len(row['dunder_getattr_exports'])} | "
            f"{_md_public_export_wrapper_cell(row)} | "
            f"{_md_join_or_none(duplicate_exports)} | "
            f"{_md_join_or_none(conflicts)} |"
        )
    return lines


def _md_public_export_owner_usage_lines(
    public_export_owner_usage_rows: list[object],
) -> list[str]:
    lines = [
        "",
        "## Retained Public Export Facade Owner/Usage Map",
        "",
        "| Path | Owner | Usage classification | Surface classification | "
        "src importers | test importers | Public exports |",
        "| --- | --- | --- | --- | ---: | ---: | ---: |",
    ]
    for row in public_export_owner_usage_rows:
        assert isinstance(row, dict)
        lines.append(
            f"| `{row['path']}` | `{row['owner']}` | `{row['usage_classification']}` | "
            f"`{row['surface_classification']}` | "
            f"{row['src_importer_count']} | {row['test_importer_count']} | "
            f"{row['public_export_count']} |"
        )
    return lines


def _md_first_safe_removal_wave_lines(
    first_safe_removal_wave: dict[str, object],
) -> list[str]:
    lines = [
        "",
        "## First Safe Removal Wave",
        "",
        f"- linked_issue: {first_safe_removal_wave['linked_issue']}",
        f"- review_date: {first_safe_removal_wave['review_date']}",
        "",
        "| Path | Owner | Previous status | Surface classification | src importers | test importers | Action |",
        "| --- | --- | --- | --- | ---: | ---: | --- |",
    ]
    removal_rows = first_safe_removal_wave["rows"]
    assert isinstance(removal_rows, list)
    for row in removal_rows:
        assert isinstance(row, dict)
        lines.append(
            f"| `{row['path']}` | `{row['owner']}` | `{row['previous_status']}` | "
            f"`{row['surface_classification']}` | {row['src_importer_count']} | "
            f"{row['test_importer_count']} | `{row['action']}` |"
        )
        prerequisites = row.get("migration_prerequisites", [])
        assert isinstance(prerequisites, list)
        if prerequisites:
            lines.append(
                f"Migration prerequisites for `{row['path']}`: "
                + "; ".join(str(item) for item in prerequisites)
            )
    return lines


def _md_removed_surface_lines(removed_rows: list[object]) -> list[str]:
    lines = [
        "",
        "## Removed Compatibility Surfaces",
        "",
        "| Module | Path exists | src importers | test importers | Canonical target |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for row in removed_rows:
        assert isinstance(row, dict)
        lines.append(
            f"| `{row['module_name']}` | "
            f"{_md_yes_no(row['path_exists'])} | "
            f"{row['src_importer_count']} | "
            f"{row['test_importer_count']} | "
            f"`{row['canonical_target']}` |"
        )
    return lines


def _md_twin_module_lines(twin_rows: list[object]) -> list[str]:
    lines = [
        "",
        "## Twin Modules",
        "",
        "| Public module | Public src | Private src |",
        "| --- | ---: | ---: |",
    ]
    for row in twin_rows:
        assert isinstance(row, dict)
        lines.append(
            f"| `{row['public_module']}` | {row['public_src_importer_count']} | "
            f"{row['private_src_importer_count']} |"
        )
    return lines


def _md_tracked_twin_family_lines(
    *,
    payload: dict[str, object],
    tracked_twin_rows: list[object],
) -> list[str]:
    lines = [
        "",
        "## Tracked Twin Family Ratchet",
        "",
        f"- inventory_source: `{payload['twin_ratchet_source']}`",
        "",
        "| Family | Canonical first-party module | Current public src | "
        "Current private src | Max public src | Max private src |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in tracked_twin_rows:
        assert isinstance(row, dict)
        lines.append(
            f"| `{row['family_id']}` | `{row['canonical_first_party_module']}` | "
            f"{row['current_public_src_importer_count']} | "
            f"{row['current_private_src_importer_count']} | "
            f"{row['max_public_src_importers']} | "
            f"{row['max_private_src_importers']} |"
        )
    return lines


def _md_config_root_facade_lines(
    *,
    payload: dict[str, object],
    config_root_facade: dict[str, object],
) -> list[str]:
    symbol_rows = config_root_facade["symbols"]
    assert isinstance(symbol_rows, list)
    lines = [
        "",
        "## Infrastructure Config Root Facade",
        "",
        f"- inventory_source: `{payload['config_root_facade_source']}`",
        f"- target_module: `{config_root_facade['target_module']}`",
        f"- new_src_import_policy: `{config_root_facade['new_src_import_policy']}`",
        "",
        "| Symbol | Current src importers | Max src importers | Canonical target |",
        "| --- | ---: | ---: | --- |",
    ]
    for row in symbol_rows:
        assert isinstance(row, dict)
        lines.append(
            f"| `{row['symbol']}` | {row['current_src_importer_count']} | "
            f"{row['max_src_importers']} | `{row['canonical_target']}` |"
        )
    return lines


def _md_control_plane_root_facade_lines(
    *,
    payload: dict[str, object],
    control_plane_root_facade: dict[str, object],
) -> list[str]:
    return [
        "",
        "## Application Control-Plane Root Facade",
        "",
        f"- inventory_source: `{payload['control_plane_root_facade_source']}`",
        f"- target_module: `{control_plane_root_facade['target_module']}`",
        "- new_src_import_policy: "
        f"`{control_plane_root_facade['new_src_import_policy']}`",
        f"- src_importer_count: {control_plane_root_facade['src_importer_count']}",
        "",
    ]


def _render_markdown(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    retained_rows = payload["retained_entrypoints"]
    retained_owner_usage_rows = payload["retained_entrypoint_owner_usage_map"]
    public_export_rows = payload["retained_public_export_facades"]
    public_export_owner_usage_rows = payload["retained_public_export_owner_usage_map"]
    first_safe_removal_wave = payload["first_safe_removal_wave"]
    removed_rows = payload["removed_compatibility_surfaces"]
    twin_rows = payload["twin_pairs"]
    tracked_twin_rows = payload["tracked_twin_families"]
    config_root_facade = payload["config_root_facade"]
    control_plane_root_facade = payload["control_plane_root_facade"]
    assert isinstance(summary, dict)
    assert isinstance(retained_rows, list)
    assert isinstance(retained_owner_usage_rows, list)
    assert isinstance(public_export_rows, list)
    assert isinstance(public_export_owner_usage_rows, list)
    assert isinstance(first_safe_removal_wave, dict)
    assert isinstance(removed_rows, list)
    assert isinstance(twin_rows, list)
    assert isinstance(tracked_twin_rows, list)
    assert isinstance(config_root_facade, dict)
    assert isinstance(control_plane_root_facade, dict)

    lines: list[str] = []
    lines.extend(_md_summary_lines(payload, summary))
    lines.extend(_md_retained_entrypoint_lines(retained_rows))
    lines.extend(_md_retained_owner_usage_lines(retained_owner_usage_rows))
    lines.extend(_md_public_export_lines(public_export_rows))
    lines.extend(_md_public_export_owner_usage_lines(public_export_owner_usage_rows))
    lines.extend(_md_first_safe_removal_wave_lines(first_safe_removal_wave))
    lines.extend(_md_removed_surface_lines(removed_rows))
    lines.extend(_md_twin_module_lines(twin_rows))
    lines.extend(
        _md_tracked_twin_family_lines(
            payload=payload, tracked_twin_rows=tracked_twin_rows
        )
    )
    lines.extend(
        _md_config_root_facade_lines(
            payload=payload, config_root_facade=config_root_facade
        )
    )
    lines.extend(
        _md_control_plane_root_facade_lines(
            payload=payload,
            control_plane_root_facade=control_plane_root_facade,
        )
    )
    return "\n".join(lines)


def main() -> int:
    from scripts.engineering.common.repo_paths import resolve_output_path

    args = _parse_args()
    repo_root = resolve_output_path(args.repo_root)
    json_out = resolve_output_path(args.json_out, root=repo_root)
    md_out = resolve_output_path(args.md_out, root=repo_root)
    snapshot_date = args.snapshot_date
    payload = build_compatibility_importer_census(
        repo_root,
        snapshot_date=snapshot_date
        or (_existing_snapshot_date(json_out) if args.check else None)
        or date.today().isoformat(),
    )
    rendered_json = json.dumps(payload, indent=2) + "\n"
    rendered_markdown = _render_markdown(payload)
    semantic_violations = validate_compatibility_metadata_consistency(
        repo_root,
        census_payload=payload,
    )
    if semantic_violations:
        _print_semantic_consistency_violations(semantic_violations)
        return 1
    if args.check:
        if not json_out.exists():
            print(f"[compatibility-importer-census] missing JSON artifact: {json_out}")
            return 1
        if not md_out.exists():
            print(
                f"[compatibility-importer-census] missing Markdown artifact: {md_out}"
            )
            return 1
        if json_out.read_text(encoding="utf-8") != rendered_json:
            print(
                "[compatibility-importer-census] FAIL: JSON artifact drifted: "
                f"{json_out}"
            )
            return 1
        if md_out.read_text(encoding="utf-8") != rendered_markdown:
            print(
                "[compatibility-importer-census] FAIL: Markdown artifact drifted: "
                f"{md_out}"
            )
            return 1
        print("[compatibility-importer-census] PASS: artifacts are up to date")
        return 0

    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(rendered_json, encoding="utf-8")
    md_out.write_text(rendered_markdown, encoding="utf-8")
    summary = payload["summary"]
    assert isinstance(summary, dict)
    print(
        "[compatibility-importer-census] "
        f"retained_entrypoints={summary['retained_entrypoint_count']}; "
        f"twin_pairs={summary['twin_pair_count']}; "
        f"json={json_out}; markdown={md_out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
