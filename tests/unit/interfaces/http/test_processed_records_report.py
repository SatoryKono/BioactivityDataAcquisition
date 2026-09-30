"""Saved reports preserve exact scope, recorded zeros and missing counts."""

from copy import deepcopy

import pytest

from bioetl.interfaces.http import _processed_records_report as subject


@pytest.fixture
def report(monkeypatch):
    value = {
        "identity": {
            "pipeline_name": "chembl_assay",
            "run_id": "run-1",
            "run_type": "backfill",
        },
        "layers": {
            "bronze_records": 100,
            "silver_valid": 100,
            "silver_filtered_out": 0,
        },
    }
    monkeypatch.setattr(subject, "load_pipeline_run_report_payload", lambda **_: value)
    return value


def test_report_counts_do_not_need_control_plane_ledger(report):
    result = subject.saved_report_records(
        pipeline="chembl_assay", run_id="run-1", run_type="backfill"
    )
    assert result["source"] == "saved_pipeline_run_report"
    rows = result["rows"]
    assert [(r["value"].strip(), r["percentage"]) for r in rows[:3]] == [
        ("100", "100.0%"),
        ("100", "100.0%"),
        ("0", "0.0%"),
    ]
    assert rows[3]["value"] == "UNKNOWN"
    assert rows[3]["percentage"] == "UNKNOWN"


@pytest.mark.parametrize(
    "field,value",
    [("run_id", "other"), ("pipeline_name", "other"), ("run_type", "incremental")],
)
def test_rejects_another_scope(report, field, value):
    report["identity"][field] = value
    assert (
        subject.saved_report_records(
            pipeline="chembl_assay", run_id="run-1", run_type="backfill"
        )
        is None
    )


def test_missing_denominator_is_not_zero(report):
    del report["layers"]["bronze_records"]
    before = deepcopy(report)
    result = subject.saved_report_records(
        pipeline="chembl_assay", run_id="run-1", run_type="backfill"
    )
    assert result["rows"][1]["value"].strip() == "100"
    assert result["rows"][1]["percentage"] == "UNKNOWN"
    assert report == before


@pytest.mark.asyncio
async def test_endpoint_prefers_report_even_without_ledger(report):
    import asyncio
    from types import SimpleNamespace

    from bioetl.interfaces.http._health_server_records_table import (
        handle_processed_records_table,
    )

    report["identity"]["run_id"] = "a80b7ec4-0bce-5a34-86bd-c21e376fa198"
    responses = []

    async def send(writer, status, payload):
        responses.append((status, payload))

    host = SimpleNamespace(
        _read_required_param=lambda query, name: query[name],
        _read_optional_param=lambda query, name: query.get(name),
        _run_ledger_port=None,
        _forensic_endpoint_limiter=asyncio.Semaphore(1),
        _send_payload_response=send,
    )
    await handle_processed_records_table(
        host,
        None,
        {
            "pipeline": "chembl_assay",
            "run_id": report["identity"]["run_id"],
            "run_type": "backfill",
        },
    )
    assert responses[0][0] == 200
    assert responses[0][1]["source"] == "saved_pipeline_run_report"
    assert responses[0][1]["rows"][0]["value"] == "100"
