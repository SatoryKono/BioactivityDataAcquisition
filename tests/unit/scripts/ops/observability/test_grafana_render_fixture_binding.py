from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ops.observability.grafana import (
    rerender_grafana_screenshots as rerender,
)

pytestmark = pytest.mark.unit


FIXTURE_INDEX_RELATIVE_PATH = Path("tests/fixtures/grafana/dashboard_states/INDEX.json")


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


def _write_registry(root: Path, *, payload: dict[str, object]) -> Path:
    registry = root / "INDEX.json"
    registry.write_text(json.dumps(payload), encoding="utf-8")
    return registry


def test_fixture_state_evidence_binds_validated_registry_and_fixture_hashes(
    tmp_path: Path,
) -> None:
    fixture_manifest = rerender._repo_root() / FIXTURE_INDEX_RELATIVE_PATH

    evidence = rerender._fixture_state_evidence(_config(tmp_path, fixture_manifest))

    assert evidence is not None
    assert evidence["contract"] == "dashboard_state_fixture_v1"
    assert evidence["path"] == str(FIXTURE_INDEX_RELATIVE_PATH)
    assert evidence["cases"] == sorted(evidence["fixtures"])
    assert isinstance(evidence["sha256"], str) and len(evidence["sha256"]) == 64
    fixtures = evidence["fixtures"]
    assert isinstance(fixtures, dict)
    assert fixtures["ok"]["path"].endswith("dashboard_states/ok.json")
    assert isinstance(fixtures["ok"]["sha256"], str)


def test_fixture_state_evidence_fails_closed_for_invalid_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(rerender, "_repo_root", lambda: tmp_path)
    fixture_manifest = _write_registry(
        tmp_path,
        payload={"contract": "unknown", "cases": {}},
    )

    with pytest.raises(ValueError, match="dashboard_state_fixture_v1"):
        rerender._fixture_state_evidence(_config(tmp_path, fixture_manifest))


def test_fixture_state_evidence_fails_closed_for_incompatible_case_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(rerender, "_repo_root", lambda: tmp_path)
    (tmp_path / "ok.json").write_text(
        json.dumps(
            {
                "contract": "dashboard_state_fixture_v1",
                "case": "different_case",
                "classification": "OK",
                "http_status": 200,
            }
        ),
        encoding="utf-8",
    )
    fixture_manifest = _write_registry(
        tmp_path,
        payload={
            "contract": "dashboard_state_fixture_v1",
            "cases": {
                "ok": {
                    "path": "ok.json",
                    "classification": "OK",
                    "http_status": 200,
                }
            },
        },
    )

    with pytest.raises(ValueError, match="contract or case value is invalid"):
        rerender._fixture_state_evidence(_config(tmp_path, fixture_manifest))


def test_parse_args_rejects_invalid_fixture_manifest_before_render(
    tmp_path: Path,
) -> None:
    with pytest.raises(SystemExit):
        rerender._parse_args(
            ["--fixture-manifest", str(tmp_path / "missing-fixture-index.json")]
        )


def test_fixture_state_evidence_is_absent_for_default_live_render(
    tmp_path: Path,
) -> None:
    assert rerender._fixture_state_evidence(_config(tmp_path, None)) is None
