"""Validate committed control-plane artifact examples against current contracts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

_JSON_GLOB = "*.json"


def validate_control_plane_artifacts(root: Path) -> list[str]:
    """Return contract violations for committed control-plane artifacts."""
    control_root = root / "data" / "output" / "control"
    violations: list[str] = []
    _validate_effective_config_artifacts(control_root, violations)
    _validate_run_manifests(control_root, violations)
    _validate_run_ledgers(control_root, violations)
    _validate_metadata_sidecar_examples(root, violations)
    _validate_lineage_fragment_examples(root, violations)
    return violations


def _validate_effective_config_artifacts(
    control_root: Path,
    violations: list[str],
) -> None:
    effective_root = control_root / "effective_config"
    for path in sorted(effective_root.glob(_JSON_GLOB)):
        _validate_semantic_effective_config_file(path, violations)

    occurrence_root = effective_root / "_occurrences"
    for path in sorted(occurrence_root.glob(_JSON_GLOB)):
        _validate_effective_config_occurrence_file(path, violations)


def _validate_semantic_effective_config_file(
    path: Path,
    violations: list[str],
) -> None:
    payload = _load_json_object(path, violations)
    if payload is None:
        return
    if "occurrence_envelope" in payload:
        violations.append(
            f"{path}: semantic effective-config artifact contains occurrence_envelope"
        )
    semantic = payload.get("semantic_artifact")
    if not isinstance(semantic, dict):
        violations.append(f"{path}: missing semantic_artifact object")
        return
    if "occurrence_envelope" in semantic:
        violations.append(
            f"{path}: nested semantic_artifact contains occurrence_envelope"
        )
    _require_fields(
        path,
        semantic,
        violations,
        ("artifact_id", "resolved_config_hash", "effective_config_hash"),
    )
    if semantic.get("artifact_id") != payload.get("artifact_id"):
        violations.append(f"{path}: top-level artifact_id differs from semantic id")


def _validate_effective_config_occurrence_file(
    path: Path,
    violations: list[str],
) -> None:
    payload = _load_json_object(path, violations)
    if payload is None:
        return
    _require_fields(path, payload, violations, ("artifact_id", "run_id"))
    if not isinstance(payload.get("occurrence_envelope"), dict):
        violations.append(f"{path}: occurrence file lacks occurrence_envelope")


def _validate_run_manifests(control_root: Path, violations: list[str]) -> None:
    for path in sorted((control_root / "run_manifest").glob(_JSON_GLOB)):
        _validate_run_manifest_file(path, violations)


def _validate_run_manifest_file(path: Path, violations: list[str]) -> None:
    payload = _load_json_object(path, violations)
    if payload is None:
        return
    _require_fields(
        path,
        payload,
        violations,
        (
            "manifest_id",
            "run_id",
            "execution_fingerprint",
            "code_provenance",
            "source_refs",
            "replay_capability",
        ),
    )
    code_provenance = payload.get("code_provenance")
    if not isinstance(code_provenance, dict):
        return
    _require_fields(
        path,
        code_provenance,
        violations,
        ("config_hash", "effective_config_artifact_id"),
    )
    if _is_strict_replay_manifest(payload) and not code_provenance.get("git_commit"):
        violations.append(f"{path}: strict replay manifest lacks git_commit")
    if payload.get(
        "replay_capability"
    ) == "exact_replay_supported" and not _manifest_has_input_snapshots(payload):
        violations.append(
            f"{path}: exact replay manifest lacks immutable input snapshots"
        )


def _validate_run_ledgers(control_root: Path, violations: list[str]) -> None:
    for path in sorted((control_root / "run_ledger").glob("*.jsonl")):
        seen_entries = False
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if not line.strip():
                continue
            seen_entries = True
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                violations.append(f"{path}:{line_number}: invalid JSONL entry: {exc}")
                continue
            if not isinstance(payload, dict):
                violations.append(f"{path}:{line_number}: ledger entry is not object")
                continue
            _require_fields(
                path,
                payload,
                violations,
                ("entry_id", "manifest_id", "run_id", "event_type", "event_family"),
                line_number=line_number,
            )
        if not seen_entries:
            violations.append(f"{path}: empty run ledger")


def _validate_metadata_sidecar_examples(root: Path, violations: list[str]) -> None:
    """Validate bounded committed sidecar examples against control-plane anchors."""
    for path in sorted(
        (root / "data" / "output" / "bronze").glob("*/*/*_metadata.yaml")
    ):
        payload = _load_yaml_object(path, violations)
        if payload is None:
            continue
        runtime = payload.get("runtime")
        pipeline = payload.get("pipeline")
        output = payload.get("output")
        if not isinstance(runtime, dict):
            violations.append(f"{path}: metadata sidecar lacks runtime object")
            continue
        if not isinstance(pipeline, dict):
            violations.append(f"{path}: metadata sidecar lacks pipeline object")
            continue
        if not isinstance(output, dict):
            violations.append(f"{path}: metadata sidecar lacks output object")
            continue
        _require_fields(path, runtime, violations, ("run_id", "manifest_id"))
        _require_fields(
            path,
            pipeline,
            violations,
            ("config_hash", "contract_ref"),
        )
        _require_fields(
            path, output, violations, ("artifact_id", "lineage_fragment_id")
        )


def _validate_lineage_fragment_examples(root: Path, violations: list[str]) -> None:
    """Validate committed lineage fragments expose manifest/run identity anchors."""
    fragment_root = root / "data" / "output" / "bronze" / "chembl" / "control"
    for path in sorted((fragment_root / "lineage" / "fragments").glob("*.json")):
        payload = _load_json_object(path, violations)
        if payload is None:
            continue
        _require_fields(
            path, payload, violations, ("fragment_id", "run_id", "manifest_id")
        )
        nodes = payload.get("nodes")
        edges = payload.get("edges")
        if not isinstance(nodes, list) or not nodes:
            violations.append(f"{path}: lineage fragment lacks nodes")
        if not isinstance(edges, list) or not edges:
            violations.append(f"{path}: lineage fragment lacks edges")


def _load_json_object(path: Path, violations: list[str]) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        violations.append(f"{path}: invalid JSON: {exc}")
        return None
    if not isinstance(payload, dict):
        violations.append(f"{path}: JSON payload is not an object")
        return None
    return payload


def _load_yaml_object(path: Path, violations: list[str]) -> dict[str, Any] | None:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        violations.append(f"{path}: invalid YAML: {exc}")
        return None
    if not isinstance(payload, dict):
        violations.append(f"{path}: YAML payload is not an object")
        return None
    return payload


def _require_fields(
    path: Path,
    payload: dict[str, Any],
    violations: list[str],
    fields: tuple[str, ...],
    *,
    line_number: int | None = None,
) -> None:
    location = f"{path}:{line_number}" if line_number is not None else str(path)
    for field_name in fields:
        if payload.get(field_name) is None:
            violations.append(f"{location}: missing required field {field_name}")


def _is_strict_replay_manifest(payload: dict[str, Any]) -> bool:
    launch_context = payload.get("launch_context")
    launch = launch_context if isinstance(launch_context, dict) else {}
    return bool(launch.get("exact_replay")) or launch.get(
        "required_persistence_profile"
    ) in {"replay_ready", "forensic_grade"}


def _manifest_has_input_snapshots(payload: dict[str, Any]) -> bool:
    source_refs = payload.get("source_refs")
    if not isinstance(source_refs, list):
        return False
    return any(
        isinstance(source_ref, dict) and bool(source_ref.get("input_snapshots"))
        for source_ref in source_refs
    )


def main(argv: list[str] | None = None) -> int:
    """Run the committed control-plane artifact validator."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root containing data/output/control",
    )
    args = parser.parse_args(argv)
    violations = validate_control_plane_artifacts(args.root)
    if violations:
        for violation in violations:
            print(violation)
        return 1
    print("control-plane artifact validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
