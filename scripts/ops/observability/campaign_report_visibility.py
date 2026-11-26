"""Source-bound preflight and exact Ops HTTP / Run Explorer verification."""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode

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
        dashboard = self.request(_DASHBOARD, grafana=True)["dashboard"]
        panels = [panel for panel in dashboard["panels"] if panel["id"] == 3010]
        if len(panels) != 1 or len(panels[0].get("targets", [])) != 1:
            raise ValueError("Grafana Run Explorer panel 3010 is unavailable")
        panel = panels[0]
        query = panel["targets"][0]
        if (
            not query.get("url", "").startswith(f"{_PIPELINE_INDEX}?")
            or "${lookup_run_id:percentencode}" not in query["url"]
            or query.get("datasource", panel.get("datasource", {})).get("uid")
            != _DATASOURCE
            or query.get("hide") is True
        ):
            raise ValueError(
                "Grafana Run Explorer does not have an active Ops HTTP lookup target"
            )
        return source_id, {
            **query,
            "datasource": query.get("datasource") or panel["datasource"],
        }

    def visible(self, run: RunReport, *, source_id: str, query: dict) -> bool:
        try:
            return self._visible(run, source_id=source_id, query=query)
        except HTTPError as exc:
            if exc.code == 404:
                return False
            raise

    def _visible(self, run: RunReport, *, source_id: str, query: dict) -> bool:
        if run.kind == "workflow":
            params = urlencode({"workflow": run.owner, "workflow_run_id": run.run_id})
            payload = self.request(f"/ops/observability/workflow-run-report?{params}")
            identity = payload.get("identity", {})
            return (identity.get("workflow_name"), identity.get("workflow_run_id")) == (
                run.owner,
                run.run_id,
            )

        url = query["url"]
        for key, value in {
            "pipeline": run.owner,
            "workflow": ".*",
            "run_type:csv": ".*",
            "run_id": "-",
            "lookup_run_id:percentencode": run.run_id,
        }.items():
            url = url.replace("${" + key + "}", value)
        if "${" in url or "$__" in url:
            raise ValueError(
                "Run Explorer lookup contains unresolved Grafana variables"
            )
        index = self.request(url)
        if (
            index.get("index_state") != "ok"
            or index.get("source_identity_actual") != source_id
            or not any(
                row.get("run_id") == run.run_id for row in index.get("items", [])
            )
        ):
            return False
        end = datetime.now(UTC)
        body = {
            "from": str(int((end - timedelta(hours=12)).timestamp() * 1000)),
            "to": str(int(end.timestamp() * 1000)),
            "queries": [{**query, "url": url}],
        }
        result = self.request("/api/ds/query", grafana=True, body=body)["results"][
            query["refId"]
        ]
        if result.get("error") or result.get("status", 200) != 200:
            return False
        return any(
            field.get("name") == "run_id" and run.run_id in column
            for frame in result.get("frames", [])
            for field, column in zip(
                frame["schema"]["fields"], frame["data"]["values"], strict=True
            )
        )
