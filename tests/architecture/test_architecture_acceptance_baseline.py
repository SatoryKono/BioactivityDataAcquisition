# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture tests for the tracked acceptance baseline contract."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = ROOT / "configs" / "quality" / "architecture_acceptance_baseline.yaml"
EXPECTED_CRITERIA = {
    "canonical_runtime_contexts",
    "control_plane_run_manifest_provenance",
    "run_ledger_lifecycle_timeline",
    "checkpoint_snapshot_only_contract",
    "resume_checkpoint_plus_replay",
    "strict_resume_compatibility_anchors",
    "no_infrastructure_runtime_imports",
    "logger_port_only_correlation_contract",
    "storage_checkpoint_error_consistency",
    "deprecated_value_object_run_manifest_absent",
}


def _load_baseline() -> dict[str, object]:
    with BASELINE_PATH.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    assert isinstance(payload, dict), (
        "architecture_acceptance_baseline.yaml must be a mapping"
    )
    return payload


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


@pytest.mark.architecture
def test_acceptance_baseline_file_is_present_and_scoped() -> None:
    payload = _load_baseline()

    assert payload.get("version") == 1
    assert payload.get("policy_scope") == "architecture_acceptance_baseline"


@pytest.mark.architecture
def test_acceptance_baseline_points_to_existing_source_of_truth_artifacts() -> None:
    payload = _load_baseline()
    source_of_truth = payload.get("source_of_truth", {})

    assert isinstance(source_of_truth, dict) and source_of_truth
    for relative_path in source_of_truth.values():
        assert isinstance(relative_path, str) and relative_path
        assert (ROOT / relative_path).exists(), (
            f"acceptance baseline source artifact missing: {relative_path}"
        )


@pytest.mark.architecture
def test_acceptance_baseline_declares_expected_curated_criteria() -> None:
    payload = _load_baseline()
    criteria = payload.get("criteria")

    assert isinstance(criteria, list) and criteria
    ids = {row.get("id") for row in criteria if isinstance(row, dict)}
    assert ids == EXPECTED_CRITERIA


@pytest.mark.architecture
def test_acceptance_baseline_rows_reference_existing_artifacts() -> None:
    payload = _load_baseline()

    for row in payload["criteria"]:
        assert isinstance(row, dict)
        assert row.get("description")
        source_paths = row.get("source_paths")
        verification_tests = row.get("verification_tests")
        code_anchors = row.get("code_anchors")

        assert isinstance(source_paths, list) and source_paths
        assert isinstance(verification_tests, list) and verification_tests
        assert isinstance(code_anchors, list)

        for relative_path in source_paths + verification_tests:
            assert isinstance(relative_path, str) and relative_path
            assert (ROOT / relative_path).exists(), (
                f"acceptance baseline references missing artifact: {relative_path}"
            )


@pytest.mark.architecture
def test_acceptance_baseline_code_anchors_match_current_runtime_contract() -> None:
    payload = _load_baseline()
    criteria = {row["id"]: row for row in payload["criteria"]}

    context_source = _read("src/bioetl/domain/context.py")
    context_run_source = _read("src/bioetl/domain/context_run.py")
    runtime_context_source = "\n".join([context_source, context_run_source])
    manifest_source = _read("src/bioetl/domain/control_plane/run_manifest.py")
    ledger_source = "\n".join(
        [
            _read("src/bioetl/domain/control_plane/run_ledger.py"),
            _read("src/bioetl/domain/control_plane/_run_ledger_runtime.py"),
            _read("src/bioetl/domain/control_plane/run_ledger_replay.py"),
        ]
    )
    load_service_source = _read(
        "src/bioetl/application/composite/checkpoint/load_service.py"
    )
    runner_service_source = _read(
        "src/bioetl/application/services/execution/pipeline_runner_service.py"
    )

    for anchor in criteria["canonical_runtime_contexts"]["code_anchors"]:
        assert anchor in runtime_context_source

    for anchor in criteria["control_plane_run_manifest_provenance"]["code_anchors"]:
        assert anchor in manifest_source

    for anchor in criteria["run_ledger_lifecycle_timeline"]["code_anchors"]:
        assert anchor in ledger_source

    for anchor in criteria["checkpoint_snapshot_only_contract"]["code_anchors"]:
        assert anchor in _read("src/bioetl/application/composite/checkpoint/state.py")

    for anchor in criteria["resume_checkpoint_plus_replay"]["code_anchors"]:
        assert anchor in load_service_source or anchor in ledger_source

    for anchor in criteria["strict_resume_compatibility_anchors"]["code_anchors"]:
        assert anchor in load_service_source

    for anchor in criteria["logger_port_only_correlation_contract"]["code_anchors"]:
        assert anchor in runtime_context_source or anchor in runner_service_source

    for anchor in criteria["storage_checkpoint_error_consistency"]["code_anchors"]:
        assert anchor in load_service_source or anchor in _read(
            "src/bioetl/application/composite/checkpoint/service.py"
        )


@pytest.mark.architecture
def test_acceptance_baseline_keeps_removed_value_object_manifest_absent() -> None:
    payload = _load_baseline()
    criteria = {row["id"]: row for row in payload["criteria"]}
    deprecated_row = criteria["deprecated_value_object_run_manifest_absent"]

    deprecated_module = (
        ROOT / "src" / "bioetl" / "domain" / "value_objects" / "run_manifest.py"
    )
    assert deprecated_module.parent == ROOT / deprecated_row["source_paths"][0]
    assert not deprecated_module.exists(), (
        "Deprecated value-object RunManifest must remain absent from src/bioetl/domain/value_objects/."
    )
