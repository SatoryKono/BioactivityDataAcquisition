from __future__ import annotations

import json
from pathlib import Path

import pytest

from bioetl.domain.control_plane.run_evidence_location import EvidenceLocationKind
from scripts.engineering.common.repo_paths import REPO_ROOT
from scripts.ops.runtime.migrate_evidence_locations import (
    MigrationTarget,
    execute_migration,
    main,
    read_target_list,
)

_VALID_DIGEST = "0" * 64


def _workflow_target(
    *,
    runtime_source_id: str = _VALID_DIGEST,
    run_id: str = "00000000-0000-0000-0000-000000000000",
) -> MigrationTarget:
    return MigrationTarget(
        kind=EvidenceLocationKind.WORKFLOW,
        owner="test_workflow",
        run_id=run_id,
        runtime_source_id=runtime_source_id,
        relative_data_root="path/to/data",
    )


def test_execute_migration_dry_run_plans_missing(tmp_path: Path) -> None:
    report_root = tmp_path / "reports"
    report_root.mkdir()

    stats = execute_migration(
        [_workflow_target()],
        report_root=report_root,
        dry_run=True,
    )
    assert stats["registered"] == 1
    assert stats["invalid"] == 0
    assert stats["conflict"] == 0


def test_execute_migration_dry_run_flags_invalid(tmp_path: Path) -> None:
    report_root = tmp_path / "reports"
    report_root.mkdir()

    stats = execute_migration(
        [_workflow_target(runtime_source_id="bad")],
        report_root=report_root,
        dry_run=True,
    )
    assert stats["invalid"] == 1
    assert stats["registered"] == 0


def test_execute_migration_apply(tmp_path: Path) -> None:
    report_root = tmp_path / "reports"
    report_root.mkdir()
    targets = [_workflow_target()]

    stats = execute_migration(targets, report_root=report_root, dry_run=False)
    assert stats["registered"] == 1

    # Idempotency
    stats = execute_migration(targets, report_root=report_root, dry_run=False)
    assert stats["already_identical"] == 1


def test_execute_migration_apply_rejects_invalid_runtime_source_id(
    tmp_path: Path,
) -> None:
    report_root = tmp_path / "reports"
    report_root.mkdir()

    stats = execute_migration(
        [_workflow_target(runtime_source_id="not-a-digest")],
        report_root=report_root,
        dry_run=False,
    )
    assert stats["invalid"] == 1
    assert stats["registered"] == 0


def test_read_target_list_rejects_path_escape(tmp_path: Path) -> None:
    outside = tmp_path / "escape.json"
    outside.write_text('{"targets": []}', encoding="utf-8")

    with pytest.raises(ValueError, match="refusing path outside"):
        read_target_list(outside, root=REPO_ROOT)


def test_read_target_list_rejects_missing_targets_key(tmp_path: Path) -> None:
    targets_file = tmp_path / "targets.json"
    targets_file.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="must contain a 'targets' array"):
        read_target_list(targets_file, root=tmp_path)


def test_read_target_list_accepts_confined_path(tmp_path: Path) -> None:
    targets_file = tmp_path / "targets.json"
    targets_file.write_text(
        json.dumps(
            {
                "targets": [
                    {
                        "kind": "workflow",
                        "owner": "demo",
                        "run_id": "00000000-0000-0000-0000-000000000001",
                        "runtime_source_id": "a" * 64,
                        "relative_data_root": "demo/data",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    targets = read_target_list(targets_file, root=tmp_path)
    assert len(targets) == 1
    assert targets[0].owner == "demo"


def test_main_rejects_targets_path_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outside = tmp_path / "escape.json"
    outside.write_text('{"targets": []}', encoding="utf-8")
    monkeypatch.chdir(REPO_ROOT)

    assert main(["--targets", str(outside)]) == 1
