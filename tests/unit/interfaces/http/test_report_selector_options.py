"""Persisted selector options must preserve scope and fail closed on corruption."""

import json
from pathlib import Path

import pytest
from tests.conftest import _is_wsl

from bioetl.interfaces.http._report_selector_options import supplement_report_options

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "zone,started,label",
    [
        ("UTC", "2026-09-15T11:00:00+00:00", "2026-09-15 11:00 UTC"),
        ("Europe/Kiev", "2026-09-15T11:00:00+00:00", "2026-09-15 14:00 EEST"),
        ("Europe/Kiev", "2026-10-25T00:30:00+00:00", "2026-10-25 03:30 EEST"),
        ("Europe/Kiev", "2026-10-25T01:30:00+00:00", "2026-10-25 03:30 EET"),
        ("UTC", "invalid", "UNKNOWN"),
    ],
)
def test_report_fallback_uses_selector_timezone(tmp_path, zone, started, label):
    _report(tmp_path, status="failed", started_at=started)
    payload = supplement_report_options(
        {"items": []},
        dimension="run_id",
        response_shape="options",
        scopes={},
        root=tmp_path,
        timezone=zone,
    )
    assert payload["items"][0]["value"] == "run-a"
    assert payload["items"][0]["text"].startswith(f"{label} ·")


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


def test_identity_snapshot_avoids_reread_but_refreshes_next_request(
    tmp_path, monkeypatch
):
    from unittest.mock import Mock
    from bioetl.interfaces.http import _report_selector_options as module

    _report(tmp_path)
    duplicate_read = Mock(side_effect=AssertionError("already read in this request"))
    monkeypatch.setattr(module, "load_pipeline_run_report_payload", duplicate_read)
    assert _options(tmp_path)["items"] == [{"text": "backfill", "value": "backfill"}]
    _report(tmp_path, run_type="incremental")
    assert _options(tmp_path)["items"] == [
        {"text": "incremental", "value": "incremental"}
    ]
    duplicate_read.assert_not_called()


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
        pytest.skip("WSL inline to_thread - skipping thread overlap check")
    import asyncio
    from threading import Barrier
    from unittest.mock import AsyncMock, Mock

    from bioetl.interfaces.http import _health_server_routing_support as module
    from bioetl.interfaces.http.health_server_routing_mixin import (
        HealthServerRoutingMixin,
    )

    barrier = Barrier(2, timeout=2)

    def manifests():
        return ()

    def build_options(**kwargs):
        # Report I/O must overlap ledger-backed label construction too, not
        # merely the initial manifest scan; otherwise their costs add up.
        barrier.wait()
        return {"items": [{"text": "chembl_assay", "value": "chembl_assay"}]}

    def reports(scopes):
        barrier.wait()
        return []

    host = HealthServerRoutingMixin()
    host._forensic_endpoint_limiter = asyncio.Semaphore(4)
    host._run_manifest_port = Mock()
    host._run_manifest_port.list_all.side_effect = manifests
    host._run_ledger_port = None
    host._workflow_manifest_port = None
    host._send_payload_response = AsyncMock()
    monkeypatch.setattr(module, "load_report_selector_entries", reports)
    monkeypatch.setattr(module, "build_selector_filter_options_payload", build_options)
    budget = AsyncMock(wraps=module.run_bounded_forensic_operation)
    monkeypatch.setattr(module, "run_bounded_forensic_operation", budget)
    await module.handle_control_plane_filter_options(
        host, None, {"dimension": "pipeline", "response_shape": "options"}
    )
    assert host._send_payload_response.call_args.args[1] == 200
    assert budget.call_args.kwargs["timeout_seconds"] == 20.0
    assert host._send_payload_response.call_args.args[2]["items"] == [
        {"text": "chembl_assay", "value": "chembl_assay"}
    ]


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
    import asyncio

    host._forensic_endpoint_limiter = asyncio.Semaphore(4)
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
