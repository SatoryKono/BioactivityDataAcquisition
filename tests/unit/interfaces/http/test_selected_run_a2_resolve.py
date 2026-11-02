"""Phase 3a §3.2 — A2 latest auto-select and empty-catalog «НЕТ ЗАПУСКОВ»."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.types import RunID, RunType
from bioetl.interfaces.http._selected_run_a2_resolve import (
    NO_RUNS_REASON,
    is_unresolved_run_id,
    resolve_a2_latest_run_id,
)
from bioetl.interfaces.http.selected_run_status import handle_selected_run_status

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 8, 10, 8, 30, tzinfo=UTC)


def _run_id(index: int) -> RunID:
    return RunID(UUID(int=index))


def _manifest(index: int, *, pipeline: str = "chembl_assay") -> RunManifest:
    provider, entity = pipeline.split("_", 1)
    return RunManifest(
        manifest_id=f"manifest-{index}",
        execution_fingerprint=f"fingerprint-{index}",
        schema_version="1.0",
        created_at=_NOW + timedelta(minutes=index),
        run_id=_run_id(index),
        run_type=RunType.INCREMENTAL,
        pipeline_name=pipeline,
        provider=provider,
        entity=entity,
        launch_context={},
        runtime_config={},
        resolved_config={},
    )


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, True),
        ("-", True),
        ("", True),
        ("All", True),
        ("$__all", True),
        ("11111111-1111-4111-8111-111111111111", False),
    ],
)
def test_unresolved_run_id_sentinels(value: str | None, expected: bool) -> None:
    assert is_unresolved_run_id(value) is expected


def test_resolve_latest_in_pipeline_scope() -> None:
    older = _manifest(1)
    newer = _manifest(2)
    other = _manifest(3, pipeline="chembl_activity")
    latest = resolve_a2_latest_run_id(
        manifests=(older, newer, other),
        ledger_port=None,
        pipeline="chembl_assay",
        query={"pipeline": "chembl_assay"},
    )
    assert latest == str(newer.run_id)


def test_resolve_empty_scope_returns_none() -> None:
    latest = resolve_a2_latest_run_id(
        manifests=(_manifest(1, pipeline="chembl_activity"),),
        ledger_port=None,
        pipeline="chembl_assay",
        query={"pipeline": "chembl_assay", "run_type": "backfill"},
    )
    assert latest is None


def test_filter_change_reselects_latest_in_new_scope() -> None:
    assay = _manifest(1, pipeline="chembl_assay")
    activity = _manifest(2, pipeline="chembl_activity")
    assert (
        resolve_a2_latest_run_id(
            manifests=(assay, activity),
            ledger_port=None,
            pipeline="chembl_assay",
            query={"pipeline": "chembl_assay"},
        )
        == str(assay.run_id)
    )
    assert (
        resolve_a2_latest_run_id(
            manifests=(assay, activity),
            ledger_port=None,
            pipeline="chembl_activity",
            query={"pipeline": "chembl_activity"},
        )
        == str(activity.run_id)
    )


def _host() -> MagicMock:
    import asyncio

    host = MagicMock()
    host._read_required_param.side_effect = lambda q, key: q[key]
    host._read_optional_param.side_effect = lambda q, key: q.get(key)
    host._forensic_endpoint_limiter = asyncio.Semaphore(2)
    host._run_manifest_port = MagicMock()
    host._run_ledger_port = None
    host._run_report_store = MagicMock()
    host._send_payload_response = AsyncMock()
    return host


async def test_handle_unresolved_run_id_auto_selects_latest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = str(_run_id(9))
    host = _host()
    monkeypatch.setattr(
        "bioetl.interfaces.http.selected_run_status.list_a2_catalog",
        lambda *_a, **_k: ((_manifest(9),), ()),
    )
    monkeypatch.setattr(
        "bioetl.interfaces.http.selected_run_status.resolve_a2_latest_run_id",
        lambda **_kwargs: selected,
    )

    def fake_load(**kwargs: Any) -> dict[str, object]:
        assert kwargs["run_id"] == selected
        return {
            "pipeline": "chembl_assay",
            "run_id": selected,
            "verdict": "OK",
            "execution_state": "SUCCESS",
            "reason": "checked",
        }

    monkeypatch.setattr(
        "bioetl.interfaces.http.selected_run_status.load_selected_run_status",
        fake_load,
    )
    monkeypatch.setattr(
        "bioetl.interfaces.http.selected_run_status.scope_matches",
        lambda *_a, **_k: True,
    )
    await handle_selected_run_status(
        host, MagicMock(), {"pipeline": "chembl_assay", "run_id": "-"}
    )
    payload = host._send_payload_response.await_args.args[2]
    assert payload["run_id"] == selected
    assert payload["verdict"] == "OK"


async def test_handle_empty_catalog_emits_no_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _host()
    monkeypatch.setattr(
        "bioetl.interfaces.http.selected_run_status.list_a2_catalog",
        lambda *_a, **_k: ((), ()),
    )
    monkeypatch.setattr(
        "bioetl.interfaces.http.selected_run_status.resolve_a2_latest_run_id",
        lambda **_kwargs: None,
    )
    await handle_selected_run_status(
        host, MagicMock(), {"pipeline": "chembl_assay", "run_id": "-"}
    )
    payload = host._send_payload_response.await_args.args[2]
    assert payload["verdict"] == "НЕТ ЗАПУСКОВ"
    assert payload["reason"] == NO_RUNS_REASON
    assert payload["presentation_summary"][0]["execution_state"] == "НЕТ ЗАПУСКОВ"


async def test_handle_explicit_url_run_id_wins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    explicit = str(_run_id(42))
    host = _host()
    resolve = MagicMock(return_value=str(_run_id(1)))
    monkeypatch.setattr(
        "bioetl.interfaces.http.selected_run_status.resolve_a2_latest_run_id",
        resolve,
    )

    def fake_load(**kwargs: Any) -> dict[str, object]:
        assert kwargs["run_id"] == explicit
        return {
            "pipeline": "chembl_assay",
            "run_id": explicit,
            "verdict": "OK",
            "execution_state": "SUCCESS",
            "reason": "checked",
        }

    monkeypatch.setattr(
        "bioetl.interfaces.http.selected_run_status.load_selected_run_status",
        fake_load,
    )
    monkeypatch.setattr(
        "bioetl.interfaces.http.selected_run_status.scope_matches",
        lambda *_a, **_k: True,
    )
    await handle_selected_run_status(
        host,
        MagicMock(),
        {"pipeline": "chembl_assay", "run_id": explicit},
    )
    resolve.assert_not_called()
    payload = host._send_payload_response.await_args.args[2]
    assert payload["run_id"] == explicit
