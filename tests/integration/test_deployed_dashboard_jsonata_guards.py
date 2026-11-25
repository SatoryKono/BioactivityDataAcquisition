"""Opt-in, read-only checks of generated queries on the deployed JSONata engine.

BIOETL_GRAFANA_ACCEPTANCE_URL and BIOETL_GRAFANA_ACCEPTANCE_AUTH select the
existing Grafana service. Requests evaluate inline fixtures; no dashboards or
BioETL evidence are written.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import quote

import httpx
import pytest

pytestmark = pytest.mark.integration
_BASE_URL = os.environ.get("BIOETL_GRAFANA_ACCEPTANCE_URL")
if not _BASE_URL:
    pytest.skip(
        "requires an explicitly selected Grafana service", allow_module_level=True
    )

_ROOT = Path(__file__).resolve().parents[2]
_COMPLETE = {
    "rows": [
        {"name": "present", "present": True, "priority": "P2"},
        {"name": "missing", "present": False, "priority": "P1"},
    ],
    "presentation_trust": {"trust_status": "OK", "reasons_count": 0},
    "replay_readiness": [{"verdict": "READY"}],
    "replay_checks": [{"code": "config", "result": "pass"}],
}


@pytest.fixture
def client():
    auth = os.environ.get("BIOETL_GRAFANA_ACCEPTANCE_AUTH")
    assert auth, "selected Grafana acceptance requires authorization"
    with httpx.Client(
        base_url=_BASE_URL, headers={"Authorization": auth}, trust_env=False, timeout=30
    ) as session:
        yield session


@pytest.mark.parametrize("profile", ["dashboards", "dashboards-adaptive"])
@pytest.mark.parametrize(
    "candidate,accepted",
    [
        (
            "https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/docs/04-reference/passports/pipelines/chembl-target.md",
            True,
        ),
        (
            "https://example.org/blob/main/docs/04-reference/passports/pipelines/chembl-target.md",
            False,
        ),
        (
            "https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/docs/04-reference/passports/workflows/chembl-target.md",
            False,
        ),
        ("javascript:alert(1)", False),
        (None, False),
        (42, False),
    ],
)
def test_pipeline_passport_link_has_only_the_canonical_origin(
    client, profile, candidate, accepted
):
    dashboard = json.loads(
        (_ROOT / "grafana" / profile / "bioetl-run-explorer-v1.json").read_text(
            encoding="utf-8"
        )
    )
    target = next(p for p in dashboard["panels"] if p["id"] == 3010)["targets"][0]
    target.update(
        source="inline",
        data=json.dumps(
            {
                "index_state": "ok",
                "items": [
                    {
                        "pipeline": "chembl_target",
                        "provider": "chembl",
                        "pipeline_passport_url": candidate,
                        "run_id": "00000000-0000-4000-8000-000000000119",
                    }
                ],
            }
        ),
    )
    target.pop("url", None)
    response = client.post(
        "/api/ds/query", json={"queries": [target], "from": "now-1m", "to": "now"}
    )
    response.raise_for_status()
    result = response.json()["results"]["A"]
    assert not result.get("error"), result.get("error")
    frame = result["frames"][0]
    names = [field["name"] for field in frame["schema"]["fields"]]
    row = dict(
        zip(names, [values[0] for values in frame["data"]["values"]], strict=True)
    )
    assert row["pipeline_passport_url"] == (candidate if accepted else "")


def _rows(
    client: httpx.Client, profile: str, panel: int, run_id: str, payload: dict
) -> list[dict]:
    dashboard = json.loads(
        (_ROOT / "grafana" / profile / "bioetl-control-plane-v1.json").read_text(
            encoding="utf-8"
        )
    )
    target = next(p for p in dashboard["panels"] if p["id"] == panel)["targets"][0]
    target.update(source="inline", data=json.dumps(payload))
    target.pop("url", None)
    target["root_selector"] = target["root_selector"].replace(
        "${run_id:percentencode}", quote(run_id, safe="")
    )
    response = client.post(
        "/api/ds/query",
        json={"queries": [target], "from": "now-1m", "to": "now"},
    )
    result = response.json().get("results", {}).get("A", {})
    assert not result.get("error"), result.get("error")
    response.raise_for_status()
    frames = result.get("frames", [])
    assert frames, "query returned no data frames"
    rows = []
    for frame in frames:
        names = [field["name"] for field in frame["schema"]["fields"]]
        rows.extend(
            dict(zip(names, values, strict=True))
            for values in zip(*frame["data"]["values"], strict=True)
        )
    assert rows, "query returned no state rows"
    return rows


@pytest.mark.parametrize("profile", ["dashboards", "dashboards-adaptive"])
@pytest.mark.parametrize("panel", [9408, 9418])
@pytest.mark.parametrize("run_id", ["", "-", "All", "$__all", "__all", "*"])
def test_no_selection_cannot_become_ready(client, profile, panel, run_id):
    rows = _rows(client, profile, panel, run_id, _COMPLETE)
    if panel == 9408:
        assert [row["status"] for row in rows] == ["SELECT RUN"]
    else:
        assert {row["_bioetl_frame"] for row in rows} == {
            "trust",
            "replay_readiness",
            "replay_checks",
        }
        assert (
            next(r for r in rows if r["_bioetl_frame"] == "trust")["trust_status"]
            == "SELECT RUN"
        )
        assert (
            next(r for r in rows if r["_bioetl_frame"] == "replay_readiness")["verdict"]
            == "SELECT RUN"
        )


@pytest.mark.parametrize("profile", ["dashboards", "dashboards-adaptive"])
@pytest.mark.parametrize("panel", [9408, 9418])
@pytest.mark.parametrize(
    "status", ["scope_resolve_timeout", "evidence_build_timeout", "QUERY ERROR"]
)
def test_source_error_cannot_become_ready(client, profile, panel, status):
    rows = _rows(
        client,
        profile,
        panel,
        "12345678-1234-4234-8234-123456789012",
        {**_COMPLETE, "status": status},
    )
    if panel == 9408:
        assert [row["status"] for row in rows] == ["QUERY ERROR"]
    else:
        assert (
            next(r for r in rows if r["_bioetl_frame"] == "trust")["trust_status"]
            == "QUERY ERROR"
        )
        assert (
            next(r for r in rows if r["_bioetl_frame"] == "replay_readiness")["verdict"]
            == "QUERY ERROR"
        )


@pytest.mark.parametrize("profile", ["dashboards", "dashboards-adaptive"])
@pytest.mark.parametrize("panel", [9408, 9418])
def test_selected_run_retains_evidence(client, profile, panel):
    rows = _rows(
        client, profile, panel, "12345678-1234-4234-8234-123456789012", _COMPLETE
    )
    if panel == 9408:
        assert [row["name"] for row in rows] == ["missing", "present"]
    else:
        assert (
            next(r for r in rows if r["_bioetl_frame"] == "trust")["trust_status"]
            == "OK"
        )
        assert (
            next(r for r in rows if r["_bioetl_frame"] == "replay_readiness")["verdict"]
            == "READY"
        )
