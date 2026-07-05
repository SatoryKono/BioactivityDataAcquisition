from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.engineering.repo import check_scripts_inventory as inventory

pytestmark = pytest.mark.unit


def _manifest_payload(*, generated_at: str, total_scripts: int) -> dict[str, object]:
    return {
        "schema_version": inventory.SCHEMA_VERSION,
        "generated_at": generated_at,
        "summary": {
            "total_scripts": total_scripts,
            "status_counts": {"active": total_scripts},
            "reference_group_coverage": {"scripts": total_scripts},
        },
        "scripts": [
            {
                "path": "scripts/example.py",
                "type": "py",
                "status": "active",
                "agent_usage": [],
                "reference_count": total_scripts,
                "references": [],
            }
        ],
    }


def _write_manifest(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def test_prepare_manifest_write_skips_timestamp_only_rewrites(tmp_path: Path) -> None:
    manifest_path = tmp_path / "scripts_inventory_manifest.json"
    existing = _manifest_payload(
        generated_at="2026-06-29T17:03:11.139176+00:00",
        total_scripts=1,
    )
    _write_manifest(manifest_path, existing)
    refreshed = _manifest_payload(
        generated_at="2026-06-29T17:15:16.900965+00:00",
        total_scripts=1,
    )

    prepared, should_write = inventory._prepare_manifest_write(manifest_path, refreshed)

    assert should_write is False
    assert prepared["generated_at"] == existing["generated_at"]


def test_prepare_manifest_write_updates_when_inventory_body_changes(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "scripts_inventory_manifest.json"
    existing = _manifest_payload(
        generated_at="2026-06-29T17:03:11.139176+00:00",
        total_scripts=1,
    )
    _write_manifest(manifest_path, existing)
    refreshed = _manifest_payload(
        generated_at="2026-06-29T17:15:16.900965+00:00",
        total_scripts=2,
    )

    prepared, should_write = inventory._prepare_manifest_write(manifest_path, refreshed)

    assert should_write is True
    assert prepared["generated_at"] == refreshed["generated_at"]
