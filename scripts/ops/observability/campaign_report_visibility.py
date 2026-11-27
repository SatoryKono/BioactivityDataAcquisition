"""Source-bound preflight and exact Ops HTTP / Run Explorer verification."""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urlsplit

from bioetl.application.services.run_reports.paths import (
    inspect_report_root_marker,
    inspect_report_root_source_identity,
)
from bioetl.composition.observability_runtime import create_run_report_store

from scripts.engineering.common.repo_paths import ensure_local_http_url
from scripts.ops.observability.campaign_report_artifacts import RunReport
from scripts.ops.observability.validate_live_observability import (
    _auth_header,
    resolve_grafana_password,
    resolve_grafana_username,
)

_PIPELINE_INDEX = "/ops/observability/pipeline-run-reports"
_DASHBOARD = "/api/dashboards/uid/bioetl-run-explorer-v1"
_DATASOURCE = "bioetl-ops-http"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, _req, _fp, _code, _msg, _headers, _newurl):
        return None


@dataclass(frozen=True)
class DashboardAccess:
    ops_url: str
    grafana_url: str
    timeout: float

    def request(
        self, path: str, *, grafana: bool = False, body: dict | None = None
    ) -> dict:
        base = self.grafana_url if grafana else self.ops_url
        url = ensure_local_http_url(base.rstrip("/") + path)
        headers = {"Accept": "application/json"}
        if grafana:
            destination = urlsplit(url)
            if destination.scheme != "https" and destination.hostname not in {
                "localhost",
                "127.0.0.1",
                "::1",
            }:
                raise ValueError(
                    "Grafana authentication requires HTTPS outside loopback"
                )
            password = resolve_grafana_password()
            if not password:
                raise ValueError(
                    "Grafana password is required for campaign verification"
                )
            headers["Authorization"] = _auth_header(
                resolve_grafana_username(), password
            )
            if org_id := os.getenv("GRAFANA_ORG_ID", "").strip():
                headers["X-Grafana-Org-Id"] = org_id
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode()
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), _NoRedirect()
        )
        with opener.open(
            urllib.request.Request(url, data=data, headers=headers),
            timeout=self.timeout,
        ) as response:
            payload = json.load(response)
        if not isinstance(payload, dict):
            raise ValueError(f"Expected a JSON object at {path}")
        return payload

    def preflight(self, target: Path) -> tuple[str, dict]:
        ready = self.request("/health/ready").get("checks", {}).get("report_root", {})
        source_id = ready.get("source_identity_actual")
        if (
            ready.get("status") != "healthy"
            or ready.get("source_identity_state") != "aligned"
            or not isinstance(source_id, str)
            or ready.get("source_identity_expected") != source_id
        ):
            raise ValueError(
                "Ops HTTP report root or runtime source identity is unhealthy"
            )
        store = create_run_report_store()
        marker = inspect_report_root_marker(report_root=target, store=store)
        identity = inspect_report_root_source_identity(
            report_root=target, expected_source_id=source_id, store=store
        )
        if (
            marker.get("status") != "healthy"
            or identity.get("source_identity_state") != "aligned"
        ):
            raise ValueError(
                f"Dashboard report root is missing its matching marker or identity: {target}"
            )
        query = self._panel_query()
        self._query_result(
            query, _query_url(query, lookup="00000000-0000-0000-0000-000000000000")
        )
        return source_id, query

    def _panel_query(self) -> dict:
        dashboard = self.request(_DASHBOARD, grafana=True)["dashboard"]
        panels = [panel for panel in dashboard["panels"] if panel["id"] == 3010]
        if len(panels) != 1 or len(panels[0].get("targets", [])) != 1:
            raise ValueError("Grafana Run Explorer panel 3010 is unavailable")
        panel = panels[0]
        query = panel["targets"][0]
        datasource = query.get("datasource") or panel.get("datasource", {})
        if (
            not query.get("url", "").startswith(f"{_PIPELINE_INDEX}?")
            or "${lookup_run_id:percentencode}" not in query["url"]
            or datasource.get("uid") != _DATASOURCE
            or query.get("hide") is True
        ):
            raise ValueError(
                "Grafana Run Explorer does not have an active Ops HTTP lookup target"
            )
        return {**query, "datasource": datasource}

    def _query_result(self, query: dict, url: str) -> dict:
        end = datetime.now(UTC)
        body = {
            "from": str(int((end - timedelta(hours=12)).timestamp() * 1000)),
            "to": str(int(end.timestamp() * 1000)),
            "queries": [{**query, "url": url}],
        }
        result = self.request("/api/ds/query", grafana=True, body=body)["results"][
            query["refId"]
        ]
        if (
            not isinstance(result, dict)
            or result.get("error")
            or result.get("status", 200) != 200
        ):
            raise ValueError("Grafana Run Explorer datasource query failed")
        if not isinstance(result.get("frames", []), list):
            raise ValueError("Grafana Run Explorer returned invalid data frames")
        return result

    def _report_exists(self, run: RunReport) -> bool:
        if run.kind == "workflow":
            params = {"workflow": run.owner, "workflow_run_id": run.run_id}
            identity_keys = ("workflow_name", "workflow_run_id")
        else:
            params = {"pipeline": run.owner, "run_id": run.run_id}
            identity_keys = ("pipeline_name", "run_id")
        payload = self.request(
            f"/ops/observability/{run.kind}-run-report?{urlencode(params)}"
        )
        identity = payload.get("identity", {})
        return tuple(identity.get(key) for key in identity_keys) == (
            run.owner,
            run.run_id,
        )

    def visible(self, run: RunReport, *, source_id: str, query: dict) -> bool:
        try:
            return self._report_exists(run) and (
                run.kind == "workflow" or self._pipeline_visible(run, source_id, query)
            )
        except HTTPError as exc:
            if exc.code == 404:
                return False
            raise

    def _pipeline_visible(self, run: RunReport, source_id: str, query: dict) -> bool:
        url = _query_url(query, pipeline=run.owner, lookup=run.run_id)
        index = self.request(url)
        if (
            index.get("index_state") != "ok"
            or index.get("source_identity_actual") != source_id
            or not any(
                (row.get("pipeline"), row.get("run_id"), row.get("report_state"))
                == (run.owner, run.run_id, "AVAILABLE")
                for row in index.get("items", [])
            )
        ):
            return False
        result = self._query_result(query, url)
        return any(
            _frame_has_report(frame, run.run_id) for frame in result.get("frames", [])
        )


def _query_url(query: dict, *, pipeline: str = ".*", lookup: str = "") -> str:
    url = query["url"]
    for key, value in {
        "pipeline": pipeline,
        "workflow": ".*",
        "run_type:csv": ".*",
        "run_id": "-",
        "lookup_run_id:percentencode": lookup,
    }.items():
        url = url.replace("${" + key + "}", quote(value, safe=""))
    if "${" in url or "$__" in url:
        raise ValueError("Run Explorer lookup contains unresolved Grafana variables")
    return url


def _frame_has_report(frame: dict, expected_run_id: str) -> bool:
    columns = {
        field["name"]: column
        for field, column in zip(
            frame["schema"]["fields"], frame["data"]["values"], strict=True
        )
    }
    return any(
        run_id == expected_run_id and state == "AVAILABLE"
        for run_id, state in zip(
            columns.get("run_id", []), columns.get("report_state", []), strict=False
        )
    )
