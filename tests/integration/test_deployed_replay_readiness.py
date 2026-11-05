"""Opt-in, read-only acceptance against the actual deployed health server.

Set BIOETL_REPLAY_ACCEPTANCE_CATALOG to a saved pipeline-run-reports JSON
catalog containing the exact successful run IDs to verify. No provider calls
or pipeline execution occur here. The default endpoint is loopback port 8000.
"""

import json
import os
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.integration
_catalog_path = os.environ.get("BIOETL_REPLAY_ACCEPTANCE_CATALOG")
if not _catalog_path:
    pytest.skip("requires a pinned deployed-run catalog", allow_module_level=True)
_catalog = json.loads(Path(_catalog_path).read_text(encoding="utf-8-sig"))
_runs = _catalog["items"]
if not _runs:
    raise ValueError("deployed replay acceptance requires at least one pinned run")


@pytest.mark.parametrize(
    "run", _runs, ids=lambda run: f"{run['pipeline']}-{run['run_id']}"
)
def test_deployed_selected_run_is_ready(run):
    with httpx.Client(
        base_url=os.environ.get(
            "BIOETL_REPLAY_ACCEPTANCE_URL", "http://127.0.0.1:8000"
        ),
        trust_env=False,
        timeout=30,
    ) as client:
        catalog_response = client.get(
            "/ops/observability/pipeline-run-reports", params={"limit": 1000}
        )
        catalog_response.raise_for_status()
        catalog = catalog_response.json()
        assert catalog["source_identity_actual"] == _catalog["source_identity_actual"]
        assert catalog["source_identity_state"] == "aligned"
        assert any(
            item["run_id"] == run["run_id"] and item["pipeline"] == run["pipeline"]
            for item in catalog["items"]
        )
        response = client.get(
            "/ops/observability/selected-run-status",
            params={
                "pipeline": run["pipeline"],
                "run_id": run["run_id"],
                "run_type": run["run_type"],
            },
        )
        response.raise_for_status()
        result = response.json()
        readiness = result["replay_readiness"][0]
        assert readiness["run_id"] == run["run_id"]
        assert readiness["pipeline"] == run["pipeline"]
        assert readiness["verdict"] == "READY", result
        assert readiness["domain_verdict"] == "exact_replay_ready"
        assert result["verdict"] == "OK", result
        assert result["evidence_completeness"] == "COMPLETE", result


@pytest.mark.parametrize("run", _runs, ids=lambda run: run["run_id"])
@pytest.mark.parametrize("selector", ["run_id", "pipeline", "run_type"])
def test_deployed_wrong_selector_cannot_be_ready(run, selector):
    params = {name: run[name] for name in ("pipeline", "run_id", "run_type")}
    params[selector] = "rebuild" if selector == "run_type" else "unknown-run"
    if selector == "run_type" and run["run_type"] == "rebuild":
        params[selector] = "incremental"
    with httpx.Client(
        base_url=os.environ.get(
            "BIOETL_REPLAY_ACCEPTANCE_URL", "http://127.0.0.1:8000"
        ),
        trust_env=False,
        timeout=30,
    ) as client:
        response = client.get("/ops/observability/selected-run-status", params=params)
        response.raise_for_status()
        assert response.json()["replay_readiness"][0]["verdict"] != "READY"
