"""Persisted selector options must preserve scope and fail closed on corruption."""

import json
from pathlib import Path

import pytest

from bioetl.interfaces.http._report_selector_options import supplement_report_options

pytestmark = pytest.mark.unit


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


def test_duplicates_and_all_are_supported(tmp_path: Path) -> None:
    _report(tmp_path)
    _report(tmp_path, "run-b")
    assert _options(tmp_path, pipeline=("$__all",)) == {
        "items": [{"text": "backfill", "value": "backfill"}]
    }


@pytest.mark.parametrize("damage", ["identity", "json", "schema"])
def test_corrupt_reports_are_errors(tmp_path: Path, damage: str) -> None:
    path = _report(tmp_path)
    if damage == "identity":
        _report(tmp_path, pipeline_name="other")
    else:
        path.write_text("{" if damage == "json" else "{}", encoding="utf-8")
    with pytest.raises(ValueError, match="selector report"):
        _options(tmp_path)


def test_report_run_id_label_and_catalog_value_deduplicate(tmp_path: Path) -> None:
    _report(tmp_path)
    payload = supplement_report_options(
        {"items": [{"text": "SELECT RUN", "value": "-"}]},
        dimension="run_id",
        response_shape="options",
        scopes={},
        root=tmp_path,
    )
    assert payload["items"][1]["value"] == "run-a"
    assert "chembl_assay" in payload["items"][1]["text"]
    assert (
        supplement_report_options(
            payload,
            dimension="run_id",
            response_shape="options",
            scopes={},
            root=tmp_path,
        )
        == payload
    )


@pytest.mark.asyncio
async def test_http_handler_merges_report_only_options(
    tmp_path: Path, monkeypatch
) -> None:
    from unittest.mock import AsyncMock, Mock
    from bioetl.interfaces.http._health_server_routing_support import (
        handle_control_plane_filter_options,
    )
    from bioetl.interfaces.http.health_server_routing_mixin import (
        HealthServerRoutingMixin,
    )

    _report(tmp_path)
    monkeypatch.setenv("BIOETL_REPORT_ROOT", str(tmp_path))
    host = HealthServerRoutingMixin()
    host._run_manifest_port = Mock()
    host._run_manifest_port.list_all.return_value = ()
    host._run_ledger_port = None
    host._workflow_manifest_port = None
    host._send_payload_response = AsyncMock()
    await handle_control_plane_filter_options(
        host,
        None,
        {
            "dimension": "run_type",
            "response_shape": "options",
            "workflow": "chembl_baseline",
            "pipeline": "chembl_assay",
        },
    )
    assert host._send_payload_response.call_args.args[1:] == (
        200,
        {"items": [{"text": "backfill", "value": "backfill"}]},
    )
