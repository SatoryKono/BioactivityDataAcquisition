"""Evaluate context presentation with real JSONata without changing the HTTP API."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
from urllib.parse import quote

import pytest

from scripts.ops.observability.grafana._run_selection_context import (
    RUN_SELECTION_CONTEXT,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("uid", "donor_id"), [("bioetl-overview-v2", 9002), ("bioetl-dq-v2", 9406)]
)
def test_context_uses_uri_encoded_variable_in_backend_only(uid, donor_id):
    root = Path(__file__).resolve().parents[5]
    dashboard = json.loads(
        (root / "grafana/dashboards" / f"{uid}.json").read_text(encoding="utf-8")
    )
    target = next(p for p in dashboard["panels"] if p["id"] == donor_id)["targets"][0]
    assert target["parser"] == "backend"
    assert "${run_id:percentencode}" in target["root_selector"]
    assert (
        "uql" not in target
    )  # JSON literal interpolation must not enter a quoted UQL program.
    if uid == "bioetl-overview-v2":
        status = next(p for p in dashboard["panels"] if p["id"] == 9603)
        projection = next(
            t for t in status["transformations"] if t["id"] == "filterFieldsByName"
        )
        assert "execution_state" in projection["options"]["include"]["names"]


@pytest.mark.parametrize(
    ("requested", "payload", "expected"),
    [
        (
            "-",
            {
                "run_id": "latest",
                "execution_state": "UNFINISHED",
                "verdict": "INCOMPLETE",
            },
            "AUTO · latest run in scope",
        ),
        (["-"], {"run_id": "latest"}, "AUTO · latest run in scope"),
        ("$__all", {"run_id": "latest"}, "AUTO · latest run in scope"),
        (
            "finished",
            {"run_id": "finished", "execution_state": "SUCCESS", "verdict": "OK"},
            "EXPLICIT · requested Run ID",
        ),
        (["finished"], {"run_id": "finished"}, "EXPLICIT · requested Run ID"),
        (
            "id\"; $error('injection'); \"",
            {"run_id": "missing", "verdict": "UNKNOWN"},
            "EXPLICIT · requested Run ID",
        ),
        ("-", {"run_id": "-", "reason": "no_runs_in_scope"}, "NO RUN · empty scope"),
        ("-", {"run_id": None, "reason": "request_failed"}, "Context unavailable"),
    ],
)
def test_query_context_is_explicit_and_clock_is_query_evaluation(
    requested, payload, expected
):
    node = shutil.which("node")
    module = os.environ.get("JSONATA_MODULE")
    if not node or not module or not Path(module).exists():
        pytest.skip("Set JSONATA_MODULE to exercise the real JSONata engine")
    # Grafana's JSON formatter leaves scalar values unquoted. URI encoding
    # inside our own quoted literal also protects quote-bearing URL values.
    value = requested[0] if isinstance(requested, list) else requested
    expression = RUN_SELECTION_CONTEXT.replace(
        "${run_id:percentencode}", quote(value, safe="~()*!.'")
    )
    script = "const fs=require('fs'); const q=JSON.parse(fs.readFileSync(0,'utf8')); require(q.module)(q.expr).evaluate(q.payload).then(x=>process.stdout.write(JSON.stringify(x))).catch(e=>{console.error(e.message);process.exit(1)});"
    before = datetime.now(UTC)
    result = subprocess.run(
        [node, "-e", script],
        input=json.dumps({"module": module, "expr": expression, "payload": payload}),
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    )
    rows = json.loads(result.stdout)
    row = rows[0]
    assert row["context"] == expected
    assert row["_bioetl_frame"] == "selection_context"
    assert row["execution_state"] == payload.get("execution_state", "UNKNOWN")
    assert row["verdict"] == payload.get("verdict", "UNKNOWN")
    checked_at = datetime.fromisoformat(
        row["context_checked_at"].replace("Z", "+00:00")
    )
    assert before <= checked_at <= datetime.now(UTC)
    assert "selection_context" not in payload
