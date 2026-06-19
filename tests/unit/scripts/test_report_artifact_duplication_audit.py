"""Unit tests for config/contract/registry artifact duplication audit."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.engineering.qa.report_artifact_duplication_audit import (
    collect_artifact_duplication_report,
)

pytestmark = pytest.mark.unit


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_collect_artifact_duplication_report_groups_exact_byte_duplicates(
    tmp_path,
) -> None:
    shared_payload = "shared: true\n"
    _write(
        tmp_path / "configs" / "entities" / "chembl" / "activity.yaml",
        shared_payload,
    )
    _write(
        tmp_path / "tests" / "fixtures" / "contracts" / "chembl.yaml",
        shared_payload,
    )
    _write(
        tmp_path / "configs" / "quality" / "contract_registry.yaml",
        "registry: unique\n",
    )

    report = collect_artifact_duplication_report(tmp_path)

    assert report["total_files"] == 3
    assert report["scope_file_counts"] == {
        "config": 1,
        "contract": 1,
        "registry": 1,
    }
    assert report["duplicate_groups"] == 1
    assert report["duplicate_files"] == 2
    assert report["groups"] == [
        {
            "sha256": "d4875c06b3c45e78843ac27915b105911e8675070225a996ed82410321839a90",
            "file_count": 2,
            "total_bytes": 26,
            "scope_counts": {"config": 1, "contract": 1},
            "paths": [
                "configs/entities/chembl/activity.yaml",
                "tests/fixtures/contracts/chembl.yaml",
            ],
        }
    ]
