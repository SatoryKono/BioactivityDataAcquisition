"""CI validation for committed control-plane artifact examples."""

from __future__ import annotations

from pathlib import Path

import pytest

import scripts.engineering.ci.validate_control_plane_artifacts as validator
from scripts.engineering.ci.validate_control_plane_artifacts import (
    validate_control_plane_artifacts,
)


ROOT = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.integration


def test_committed_control_plane_artifacts_match_published_contracts() -> None:
    """Committed examples must not drift from current control-plane contracts."""
    violations = validate_control_plane_artifacts(ROOT)
    assert violations == []


def test_control_plane_validator_ignores_untracked_runtime_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Git checkouts validate tracked examples, not local runtime output files."""
    manifest_dir = tmp_path / "data/output/control/run_manifest"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "local-runtime-output.json").write_text(
        "not-json", encoding="utf-8"
    )

    monkeypatch.setattr(validator, "_git_tracked_files", lambda *_args: [])

    violations = validate_control_plane_artifacts(tmp_path)

    assert violations == []


def test_control_plane_validator_checks_metadata_sidecar_examples(
    tmp_path: Path,
) -> None:
    """Metadata sidecar examples must expose runtime and output anchors."""
    sidecar_dir = tmp_path / "data/output/bronze/chembl/activity"
    sidecar_dir.mkdir(parents=True)
    (sidecar_dir / "chembl_activity_metadata.yaml").write_text(
        "\n".join(
            (
                "runtime:",
                "  run_id: run-1",
                "pipeline:",
                "  config_hash: cfg",
                "  contract_ref: chembl.activity",
                "output:",
                "  artifact_id: artifact-1",
                "  lineage_fragment_id: fragment-1",
            )
        ),
        encoding="utf-8",
    )

    violations = validate_control_plane_artifacts(tmp_path)

    assert (
        f"{sidecar_dir / 'chembl_activity_metadata.yaml'}: "
        "missing required field manifest_id"
    ) in violations


def test_control_plane_validator_checks_lineage_fragment_examples(
    tmp_path: Path,
) -> None:
    """Lineage fragment examples must expose fragment, manifest, and run anchors."""
    fragment_dir = tmp_path / "data/output/bronze/chembl/control/lineage/fragments"
    fragment_dir.mkdir(parents=True)
    fragment_path = fragment_dir / "fragment.json"
    fragment_path.write_text(
        '{"fragment_id": "fragment-1", "manifest_id": "manifest-1", '
        '"nodes": [], "edges": []}',
        encoding="utf-8",
    )

    violations = validate_control_plane_artifacts(tmp_path)

    assert f"{fragment_path}: missing required field run_id" in violations
    assert f"{fragment_path}: lineage fragment lacks nodes" in violations
    assert f"{fragment_path}: lineage fragment lacks edges" in violations
