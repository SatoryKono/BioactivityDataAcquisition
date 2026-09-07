"""Exact report artifact selection rejects arbitrary paths and foreign identity."""

import json
import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bioetl.interfaces.http.run_report_ops import load_pipeline_run_report_artifact
from bioetl.interfaces.http._pipeline_run_report_table import (
    _summary_rows_pipeline_run_report,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def report_root(tmp_path: Path) -> Path:
    run = tmp_path / "pipeline" / "chembl_assay" / "run-1"
    run.mkdir(parents=True)
    (run / "pipeline-run-report.json").write_text(
        json.dumps(
            {
                "schema_version": "pipeline_run_report_v1",
                "identity": {"pipeline_name": "chembl_assay", "run_id": "run-1"},
            }
        ),
        encoding="utf-8",
    )
    (run / "pipeline-run-report.md").write_text(
        "# chembl_assay / run-1\n", encoding="utf-8"
    )
    return tmp_path


@pytest.mark.parametrize(
    "fmt, expected",
    [
        ("pipeline_run_report_json", '"run_id": "run-1"'),
        ("pipeline_run_report_md", "# chembl_assay / run-1"),
    ],
)
def test_artifact_returns_original_format(
    report_root: Path, fmt: str, expected: str
) -> None:
    body = load_pipeline_run_report_artifact(
        pipeline="chembl_assay",
        run_id="run-1",
        artifact_format=fmt,
        root=report_root,
    )
    assert expected in body


@pytest.mark.parametrize(
    "pipeline,run_id,fmt",
    [
        ("../secret", "run-1", "pipeline_run_report_json"),
        ("chembl_assay", "../secret", "pipeline_run_report_json"),
        ("chembl_assay", "run-1", "../../.env"),
        ("chembl assay", "run-1", "pipeline_run_report_json"),
        ("chembl_assay", "run/1", "pipeline_run_report_md"),
    ],
)
def test_artifact_rejects_path_inputs(
    report_root: Path, pipeline: str, run_id: str, fmt: str
) -> None:
    with pytest.raises(ValueError):
        load_pipeline_run_report_artifact(
            pipeline=pipeline,
            run_id=run_id,
            artifact_format=fmt,
            root=report_root,
        )


def test_artifact_missing_is_explicit(report_root: Path) -> None:
    assert (
        load_pipeline_run_report_artifact(
            pipeline="chembl_assay",
            run_id="absent",
            artifact_format="pipeline_run_report_md",
            root=report_root,
        )
        is None
    )


def _symlink_or_skip(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314:
            pytest.skip("Windows account cannot create symbolic links")
        raise


def test_artifact_rejects_run_directory_symlink_escape(report_root: Path) -> None:
    confined = report_root / "confined"
    link = confined / "pipeline" / "chembl_assay" / "run-1"
    link.parent.mkdir(parents=True)
    _symlink_or_skip(link, report_root / "pipeline" / "chembl_assay" / "run-1")
    with pytest.raises(ValueError, match="outside the configured report root"):
        load_pipeline_run_report_artifact(
            pipeline="chembl_assay",
            run_id="run-1",
            artifact_format="pipeline_run_report_json",
            root=confined,
        )


@pytest.mark.parametrize("extension", ["json", "md"])
def test_artifact_rejects_file_symlink_escape(
    report_root: Path, extension: str
) -> None:
    path = (
        report_root / "pipeline/chembl_assay/run-1" / f"pipeline-run-report.{extension}"
    )
    outside = report_root / f"other-run-report.{extension}"
    path.rename(outside)
    _symlink_or_skip(path, outside)
    with pytest.raises(ValueError, match="outside the selected run"):
        load_pipeline_run_report_artifact(
            pipeline="chembl_assay",
            run_id="run-1",
            artifact_format="pipeline_run_report_md",
            root=report_root,
        )


def test_artifact_rejects_foreign_identity(report_root: Path) -> None:
    path = report_root / "pipeline/chembl_assay/run-1/pipeline-run-report.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["identity"]["run_id"] = "foreign-run"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="identity"):
        load_pipeline_run_report_artifact(
            pipeline="chembl_assay",
            run_id="run-1",
            artifact_format="pipeline_run_report_md",
            root=report_root,
        )


@pytest.mark.parametrize(
    "identity",
    [
        {"run_id": "-"},
        {"run_id": "run-1", "started_at": "2026-09-06T12:20:00+00:00"},
        {"run_id": "run-1", "completed_at": "2026-09-06T12:21:00+00:00"},
    ],
)
def test_missing_run_times_do_not_offer_range_action(identity) -> None:
    row = _summary_rows_pipeline_run_report({"identity": identity})["summary"][0]
    assert "set_range_to_run" not in row
    assert row["range_action_status"] == "Run timestamps unavailable"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fmt,body,status",
    [
        ("pipeline_run_report_json", "{}", 200),
        ("pipeline_run_report_md", "# Report", 200),
        ("pipeline_run_report_md", None, 404),
    ],
)
async def test_artifact_http_route(monkeypatch, fmt, body, status) -> None:
    from bioetl.interfaces.http import _health_server_observability_routing as routing

    monkeypatch.setattr(
        routing, "load_pipeline_run_report_artifact", lambda **kwargs: body
    )
    host = SimpleNamespace(
        _read_required_param=lambda query, name: query[name],
        _forensic_endpoint_limiter=asyncio.Semaphore(1),
        _send_text_response=AsyncMock(),
        _send_response=AsyncMock(),
        _send_payload_response=AsyncMock(),
    )
    await routing.dispatch_observability_request(
        host,
        writer=None,
        path="/ops/observability/pipeline-run-report-artifact",
        query={"pipeline": "chembl_assay", "run_id": "run-1", "format": fmt},
    )
    if status == 404:
        assert host._send_response.await_args.args[1] == 404
    else:
        assert host._send_text_response.await_args.args == (None, 200, body)
        expected = "application/json" if fmt.endswith("json") else "text/plain"
        assert host._send_text_response.await_args.kwargs["content_type"].startswith(
            expected
        )


@pytest.mark.asyncio
async def test_artifact_http_budget_unavailable(monkeypatch) -> None:
    from bioetl.interfaces.http import _health_server_observability_routing as routing

    monkeypatch.setattr(
        routing,
        "run_bounded_forensic_operation",
        AsyncMock(
            side_effect=routing.ForensicEndpointUnavailable(
                reason="queue_full", status_code=503
            )
        ),
    )
    host = SimpleNamespace(
        _read_required_param=lambda query, name: query[name],
        _forensic_endpoint_limiter=asyncio.Semaphore(1),
        _send_payload_response=AsyncMock(),
    )
    await routing.handle_pipeline_run_report_artifact(
        host,
        None,
        {
            "pipeline": "chembl_assay",
            "run_id": "run-1",
            "format": "pipeline_run_report_json",
        },
    )
    assert host._send_payload_response.await_args.args[1] == 503
    assert host._send_payload_response.await_args.args[2]["status"] == "unavailable"
