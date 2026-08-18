from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ops.observability.grafana import (
    rerender_grafana_screenshots as rerender,
)

pytestmark = pytest.mark.unit


def _config(tmp_path: Path, fixture_manifest: Path | None) -> rerender.RenderConfig:
    return rerender.RenderConfig(
        base_url="http://localhost:3000",
        username="admin",
        password="",
        service_account_token="",
        output_dir=tmp_path,
        width=1024,
        height=900,
        timeout_seconds=30.0,
        selected_uids=("bioetl-runtime",),
        fallback="playwright",
        fixture_manifest=fixture_manifest,
    )


def test_fixture_state_evidence_binds_contract_path_hash_and_cases(
    tmp_path: Path,
) -> None:
    fixture_manifest = tmp_path / "INDEX.json"
    fixture_manifest.write_text(
        json.dumps(
            {
                "contract": "dashboard_state_fixture_v1",
                "cases": {"warn": {}, "ok": {}},
            }
        ),
        encoding="utf-8",
    )

    evidence = rerender._fixture_state_evidence(_config(tmp_path, fixture_manifest))

    assert evidence is not None
    assert evidence["contract"] == "dashboard_state_fixture_v1"
    assert evidence["path"] == "INDEX.json"
    assert evidence["cases"] == ["ok", "warn"]
    assert isinstance(evidence["sha256"], str) and len(evidence["sha256"]) == 64


def test_fixture_state_evidence_fails_closed_for_invalid_registry(
    tmp_path: Path,
) -> None:
    fixture_manifest = tmp_path / "INDEX.json"
    fixture_manifest.write_text(
        json.dumps({"contract": "unknown", "cases": []}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="dashboard_state_fixture_v1"):
        rerender._fixture_state_evidence(_config(tmp_path, fixture_manifest))


def test_fixture_state_evidence_is_absent_for_default_live_render(
    tmp_path: Path,
) -> None:
    assert rerender._fixture_state_evidence(_config(tmp_path, None)) is None
