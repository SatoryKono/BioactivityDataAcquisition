"""Persisted selector options must preserve scope and fail closed on corruption."""

import json
from pathlib import Path

import pytest
from tests.conftest import _is_wsl

from bioetl.interfaces.http._report_selector_options import supplement_report_options

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "zone,clock", [("UTC", "11:00 UTC"), ("Europe/Kiev", "14:00 EEST")]
)
def test_report_fallback_uses_selector_timezone(tmp_path, zone, clock):
    _report(tmp_path, status="failed")
    payload = supplement_report_options(
        {"items": []},
        dimension="run_id",
        response_shape="options",
        scopes={},
        root=tmp_path,
        timezone=zone,
    )
    assert payload["items"][0]["value"] == "run-a"
    assert payload["items"][0]["text"].startswith(f"2026-09-15 {clock} ·")


def _report(root: Path, run_id: str = "run-a", **overrides: str) -> Path:
    path = root / "pipeline" / "chembl_assay" / run_id / "pipeline-run-report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    identity = {
        "pipeline_name": "chembl_assay",
        "run_id": run_id,
        "workflow_id": "chembl_baseline",
        "run_type": "backfill",
        "started_at": "2026-09-15T11:00:00+00:00",
        "status": "success",
    }
    identity.update(overrides)
    path.write_text(
        json.dumps({"schema_version": "pipeline_run_report_v1", "identity": identity}),
        encoding="utf-8",
    )
    return path


def _options(root: Path, **scopes: tuple[str, ...]) -> dict:
    return supplement_report_options(
        {"items": []},
        dimension="run_type",
        response_shape="options",
        scopes=scopes,
        root=root,
    )


def test_report_only_historical_run_supplies_type(tmp_path: Path) -> None:
    _report(tmp_path)
    assert _options(
        tmp_path, workflow=("chembl_baseline",), pipeline=("chembl_assay",)
    ) == {"items": [{"text": "backfill", "value": "backfill"}]}


@pytest.mark.parametrize(
    "scope",
    [
        {"workflow": ("other",)},
        {"pipeline": ("other",)},
        {"run_type": ("incremental",)},
        {"run_id": ("other",)},
        {"run_status": ("failed",)},
    ],
)
def test_foreign_context_does_not_supply_options(tmp_path: Path, scope: dict) -> None:
    _report(tmp_path)
    assert _options(tmp_path, **scope) == {"items": []}


def test_empty_catalog_stays_empty(tmp_path: Path) -> None:
    assert _options(tmp_path) == {"items": []}


def test_selected_pipeline_does_not_read_foreign_report_identity(
    tmp_path: Path, monkeypatch
) -> None:
    from bioetl.interfaces.http import _report_selector_options as module

    _report(tmp_path)
    original = module.list_pipeline_reports
    owners = []

    def record_scope(**kwargs):
        owners.append(kwargs.get("pipeline_name"))
        return original(**kwargs)

    monkeypatch.setattr(module, "list_pipeline_reports", record_scope)
    assert _options(tmp_path, pipeline=("chembl_assay",))["items"]
    assert owners == ["chembl_assay"]


def test_manifest_backed_pipeline_does_not_reload_duplicate_reports(
    tmp_path: Path, monkeypatch
) -> None:
    from unittest.mock import Mock
    from bioetl.interfaces.http import _report_selector_options as module

    _report(tmp_path)
    check = Mock(side_effect=AssertionError("duplicate must not contribute evidence"))
    monkeypatch.setattr(module, "_checked_identity", check)
    payload = {"items": [{"text": "chembl_assay", "value": "chembl_assay"}]}
    assert (
        module.supplement_report_options(
            payload,
            dimension="pipeline",
            response_shape="options",
            scopes={},
            root=tmp_path,
        )
        == payload
    )
    check.assert_not_called()


@pytest.mark.asyncio
async def test_filter_catalog_reads_overlap_without_losing_options(monkeypatch) -> None:
    if _is_wsl():
        pytest.skip("WSL inline to_thread - skipping")
    if _is_wsl():
        pytest.skip("WSL inline to_thread - skipping")
