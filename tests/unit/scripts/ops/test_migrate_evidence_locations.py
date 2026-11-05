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


def test_execute_migration_dry_run(tmp_path: Path) -> None:
    report_root = tmp_path / "reports"
    report_root.mkdir()

    targets = [
        MigrationTarget(
            kind=EvidenceLocationKind.WORKFLOW,
            owner="test_workflow",
            run_id="00000000-0000-0000-0000-000000000000",
            runtime_source_id=(
                "0000000000000000000000000000000000000000000000000000000000000000"
            ),
            relative_data_root="path/to/data",
        )
    ]

    stats = execute_migration(targets, report_root=report_root, dry_run=True)
    assert sum(stats.values()) == 0


def test_execute_migration_apply(tmp_path: Path) -> None:
    report_root = tmp_path / "reports"
    report_root.mkdir()

    targets = [
        MigrationTarget(
            kind=EvidenceLocationKind.WORKFLOW,
            owner="test_workflow",
            run_id="00000000-0000-0000-0000-000000000000",
            runtime_source_id=(
                "0000000000000000000000000000000000000000000000000000000000000000"
            ),
            relative_data_root="path/to/data",
        )
    ]

    stats = execute_migration(targets, report_root=report_root, dry_run=False)
    assert stats["registered"] == 1

    # Idempotency
    stats = execute_migration(targets, report_root=report_root, dry_run=False)
    assert stats["already_identical"] == 1


def test_read_target_list_rejects_path_escape(tmp_path: Path) -> None:
    outside = tmp_path / "escape.json"
    outside.write_text('{"targets": []}', encoding="utf-8")

    with pytest.raises(ValueError, match="refusing path outside"):
        read_target_list(outside, root=REPO_ROOT)


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
