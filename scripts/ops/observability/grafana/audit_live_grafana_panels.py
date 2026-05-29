"""Run a reviewed live datasource/frame audit for semantically sensitive Grafana panels."""

from __future__ import annotations

import argparse
import base64
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

DEFAULT_PROMETHEUS_BASE_URL = "http://localhost:9090"
DEFAULT_APP_BASE_URL = "http://localhost:8081"
DEFAULT_GRAFANA_BASE_URL = "http://localhost:3000"
DEFAULT_GRAFANA_USERNAME = "admin"
DEFAULT_GRAFANA_PASSWORD = "admin"
DEFAULT_HTTP_DATASOURCE_NAME = "Quarantine Explorer"
DEFAULT_OUTPUT_PATH = Path("reports/observability/grafana/live-panel-audit.json")
DEFAULT_WORKFLOW = "All"
DEFAULT_PIPELINE = "chembl_target"
DEFAULT_RUN_TYPE = "incremental"
DEFAULT_RUN_ID = "-"
DEFAULT_RANGE_HOURS = 24
_HEALTH_PROBE_PATHS: tuple[str, ...] = ("/health/live", "/health")
_DASHBOARD_DIR = Path("grafana/dashboards")


@dataclass(frozen=True)
class PanelAuditSpec:
    dashboard_uid: str
    panel_id: int
    title: str
    source_kind: Literal["prometheus", "http"]
    semantic_kind: Literal["derived_status", "freshness", "http_summary", "http_table"]


@dataclass(frozen=True)
class AuditConfig:
    prometheus_base_url: str
    app_base_url: str
    grafana_base_url: str
    grafana_username: str
    grafana_password: str
    workflow: str
    pipeline: str
    run_type: str
    run_id: str
    range_hours: int
    output_path: Path


@dataclass(frozen=True)
class AuditResult:
    dashboard_uid: str
    panel_id: int
    title: str
    source_kind: str
    semantic_kind: str
    status: str
    classification: str
    detail: str
    query_preview: str


REVIEWED_PANEL_SPECS: tuple[PanelAuditSpec, ...] = (
    PanelAuditSpec(
        dashboard_uid="bioetl-control-plane-v1",
        panel_id=9402,
        title="ID",
        source_kind="http",
        semantic_kind="http_table",
    ),
    PanelAuditSpec(
        dashboard_uid="bioetl-control-plane-v1",
        panel_id=9403,
        title="Processed Records",
        source_kind="http",
        semantic_kind="http_table",
    ),
    PanelAuditSpec(
        dashboard_uid="bioetl-overview-v2",
        panel_id=9301,
        title="Processed Records",
        source_kind="http",
        semantic_kind="http_table",
    ),
    PanelAuditSpec(
        dashboard_uid="bioetl-control-plane-v1",
        panel_id=132,
        title="Monitor: Manifest Write Failure Ratio",
        source_kind="prometheus",
        semantic_kind="derived_status",
    ),
    PanelAuditSpec(
        dashboard_uid="bioetl-control-plane-v1",
        panel_id=133,
        title="Monitor: Ledger Append Failure Ratio",
        source_kind="prometheus",
        semantic_kind="derived_status",
    ),
    PanelAuditSpec(
        dashboard_uid="bioetl-dq-v2",
        panel_id=101,
        title="Review: Latest Successful Data Timestamp",
        source_kind="prometheus",
        semantic_kind="freshness",
    ),
    PanelAuditSpec(
        dashboard_uid="bioetl-dq-v2",
        panel_id=8,
        title="Monitor: Worst Data Freshness Lag (seconds)",
        source_kind="prometheus",
        semantic_kind="freshness",
    ),
    PanelAuditSpec(
        dashboard_uid="bioetl-dq-v2",
        panel_id=9402,
        title="ID",
        source_kind="http",
        semantic_kind="http_table",
    ),
    PanelAuditSpec(
        dashboard_uid="bioetl-dq-v2",
        panel_id=9403,
        title="Processed Records",
        source_kind="http",
        semantic_kind="http_table",
    ),
    PanelAuditSpec(
        dashboard_uid="bioetl-control-plane-v1",
        panel_id=892,
        title="Monitor: Checkpoint Freshness Lag (seconds)",
        source_kind="http",
        semantic_kind="freshness",
    ),
    PanelAuditSpec(
        dashboard_uid="bioetl-silver-reject-explorer",
        panel_id=3,
        title="Track Reject Rate vs Bronze",
        source_kind="http",
        semantic_kind="http_summary",
    ),
    PanelAuditSpec(
        dashboard_uid="bioetl-runtime",
        panel_id=9403,
        title="Processed Records",
        source_kind="http",
        semantic_kind="http_table",
    ),
    PanelAuditSpec(
        dashboard_uid="bioetl-provider-health-v2",
        panel_id=9403,
        title="Processed Records",
        source_kind="http",
        semantic_kind="http_table",
    ),
    PanelAuditSpec(
        dashboard_uid="bioetl-workflow-overview",
        panel_id=9403,
        title="Processed Records",
        source_kind="http",
        semantic_kind="http_table",
    ),
)


def _read_env(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value or default


def _auth_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def _parse_args(argv: list[str] | None) -> AuditConfig:
    parser = argparse.ArgumentParser(
        description=(
            "Execute a reviewed live datasource/frame audit for semantically "
            "sensitive Grafana panels and write a JSON report under reports/."
        )
    )
    parser.add_argument(
        "--prometheus-base-url",
        default=DEFAULT_PROMETHEUS_BASE_URL,
        help="Prometheus HTTP API base URL.",
    )
    parser.add_argument(
        "--app-base-url",
        default=DEFAULT_APP_BASE_URL,
        help="Health/ops HTTP base URL used by dashboard backend datasources.",
    )
    parser.add_argument(
        "--grafana-base-url",
        default=_read_env("GRAFANA_BASE_URL", DEFAULT_GRAFANA_BASE_URL),
        help="Grafana base URL used to discover shipped HTTP datasource URLs.",
    )
    parser.add_argument(
        "--grafana-username",
        default=_read_env("GRAFANA_USERNAME", DEFAULT_GRAFANA_USERNAME),
        help="Grafana username used for datasource discovery.",
    )
    parser.add_argument(
        "--grafana-password",
        default=_read_env("GRAFANA_PASSWORD", DEFAULT_GRAFANA_PASSWORD),
        help="Grafana password used for datasource discovery.",
    )
    parser.add_argument("--workflow", default=DEFAULT_WORKFLOW)
    parser.add_argument("--pipeline", default=DEFAULT_PIPELINE)
    parser.add_argument("--run-type", default=DEFAULT_RUN_TYPE)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--range-hours", type=int, default=DEFAULT_RANGE_HOURS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)
    return AuditConfig(
        prometheus_base_url=args.prometheus_base_url.rstrip("/"),
        app_base_url=args.app_base_url.rstrip("/"),
        grafana_base_url=args.grafana_base_url.rstrip("/"),
        grafana_username=args.grafana_username,
        grafana_password=args.grafana_password,
        workflow=args.workflow,
        pipeline=args.pipeline,
        run_type=args.run_type,
        run_id=args.run_id,
        range_hours=args.range_hours,
        output_path=args.output,
    )


def _load_dashboard(uid: str) -> dict[str, Any]:
    for path in sorted(_DASHBOARD_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("uid") == uid:
            return cast(dict[str, Any], payload)
    raise FileNotFoundError(f"Dashboard UID not found in repo: {uid}")


def _iter_panels(panels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for panel in panels:
        items.append(panel)
        nested = panel.get("panels")
        if isinstance(nested, list):
            items.extend(_iter_panels(cast(list[dict[str, Any]], nested)))
    return items


def _find_panel(spec: PanelAuditSpec) -> dict[str, Any]:
    dashboard = _load_dashboard(spec.dashboard_uid)
    for panel in _iter_panels(cast(list[dict[str, Any]], dashboard.get("panels", []))):
        if panel.get("id") == spec.panel_id:
            return panel
    raise LookupError(f"Panel not found: {spec.dashboard_uid}#{spec.panel_id}")


def _time_window(config: AuditConfig) -> tuple[str, str]:
    end = datetime.now(tz=UTC)
    start = end - timedelta(hours=config.range_hours)
    return start.isoformat(), end.isoformat()


def _substitute_dashboard_tokens(template: str, config: AuditConfig) -> str:
    start_iso, end_iso = _time_window(config)
    replacements = {
        "$workflow": config.workflow,
        "$pipeline": config.pipeline,
        "$run_type": config.run_type,
        "$run_id": config.run_id,
        "${workflow}": config.workflow,
        "${pipeline}": config.pipeline,
        "${run_type}": config.run_type,
        "${run_id}": config.run_id,
        "${workflow:queryparam}": quote(config.workflow, safe=""),
        "${pipeline:queryparam}": quote(config.pipeline, safe=""),
        "${run_type:queryparam}": quote(config.run_type, safe=""),
        "${run_id:queryparam}": quote(config.run_id, safe=""),
        "${pipeline:csv}": config.pipeline,
        "${run_type:csv}": config.run_type,
        "${reason_code:csv}": "",
        "${field:csv}": "",
        "${quarantine_run_id}": "",
        "${payload_hash}": "",
        "${__from:date:iso}": quote(start_iso, safe=""),
        "${__to:date:iso}": quote(end_iso, safe=""),
    }
    rendered = template
    for token, value in replacements.items():
        rendered = rendered.replace(token, value)
    return rendered


def _fetch_json(url: str) -> object:
    with urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _request_json(url: str, *, auth_header: str, timeout_seconds: float) -> object:
    request = Request(url, headers={"Authorization": auth_header})
    with urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def _normalize_host_access_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.hostname != "host.docker.internal":
        return url.rstrip("/")
    port = f":{parts.port}" if parts.port is not None else ""
    host = f"localhost{port}"
    return urlunsplit(
        (parts.scheme, host, parts.path, parts.query, parts.fragment)
    ).rstrip("/")


def _discover_http_datasource_url(
    config: AuditConfig,
    *,
    datasource_name: str = DEFAULT_HTTP_DATASOURCE_NAME,
) -> str | None:
    url = (
        f"{config.grafana_base_url}/api/datasources/name/"
        f"{quote(datasource_name, safe='')}"
    )
    payload = _request_json(
        url,
        auth_header=_auth_header(config.grafana_username, config.grafana_password),
        timeout_seconds=30,
    )
    if not isinstance(payload, dict):
        return None
    datasource_url = payload.get("url")
    if not isinstance(datasource_url, str) or not datasource_url.strip():
        return None
    return datasource_url.rstrip("/")


def _candidate_app_base_urls(config: AuditConfig) -> tuple[str, ...]:
    candidates: list[str] = [config.app_base_url.rstrip("/")]
    if config.app_base_url.rstrip("/") != DEFAULT_APP_BASE_URL:
        return tuple(candidates)

    try:
        datasource_url = _discover_http_datasource_url(config)
    except (HTTPError, URLError, OSError, json.JSONDecodeError):
        datasource_url = None
    if datasource_url:
        candidates.append(datasource_url)
        normalized = _normalize_host_access_url(datasource_url)
        if normalized != datasource_url:
            candidates.append(normalized)

    deduped: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in deduped:
            deduped.append(candidate)
    return tuple(deduped)


def _probe_app_health(candidate_base_url: str) -> tuple[str, object] | None:
    for path in _HEALTH_PROBE_PATHS:
        try:
            payload = _fetch_json(f"{candidate_base_url}{path}")
        except (HTTPError, URLError, OSError, json.JSONDecodeError):
            continue
        return (path, payload)
    return None


def _resolve_app_base_url(config: AuditConfig) -> str:
    attempted: list[str] = []
    for candidate in _candidate_app_base_urls(config):
        probe = _probe_app_health(candidate)
        if probe is None:
            attempted.extend(f"{candidate}{path}" for path in _HEALTH_PROBE_PATHS)
            continue
        path, payload = probe
        attempted.append(f"{candidate}{path}")
        if isinstance(payload, dict):
            return candidate
    attempted_urls = ", ".join(attempted)
    raise OSError(
        "Could not reach Quarantine Explorer backend via canonical health probes using candidates: "
        f"{attempted_urls}"
    )


def _classify_prometheus_payload(payload: object) -> tuple[str, str]:
    if not isinstance(payload, dict):
        return ("invalid_shape", "Prometheus payload is not a JSON object")
    if payload.get("status") != "success":
        return ("query_error", f"Prometheus status={payload.get('status')!r}")
    data = payload.get("data")
    if not isinstance(data, dict):
        return ("invalid_shape", "Prometheus payload missing data object")
    result = data.get("result")
    result_type = data.get("resultType")
    if result_type == "vector":
        if not isinstance(result, list):
            return ("invalid_shape", "Prometheus vector result must be a list")
        if not result:
            return ("empty_result", "Prometheus vector returned no samples")
        values: list[float] = []
        for item in result:
            if not isinstance(item, dict):
                return ("invalid_shape", "Prometheus vector sample must be an object")
            sample = item.get("value")
            if not isinstance(sample, list) or len(sample) != 2:
                return ("invalid_shape", "Prometheus vector sample missing value pair")
            try:
                values.append(float(sample[1]))
            except (TypeError, ValueError):
                return (
                    "invalid_shape",
                    "Prometheus vector sample value is not numeric",
                )
        if all(value == 0.0 for value in values):
            return ("zero_result", "Prometheus vector returned only zero values")
        return ("nonzero_result", "Prometheus vector returned non-zero values")
    if result_type == "scalar":
        if not isinstance(result, list) or len(result) != 2:
            return ("invalid_shape", "Prometheus scalar result missing value pair")
        try:
            value = float(result[1])
        except (TypeError, ValueError):
            return ("invalid_shape", "Prometheus scalar value is not numeric")
        if value == 0.0:
            return ("zero_result", "Prometheus scalar returned zero")
        return ("nonzero_result", "Prometheus scalar returned non-zero value")
    return ("invalid_shape", f"Unsupported Prometheus resultType={result_type!r}")


def _classify_http_payload(payload: object) -> tuple[str, str]:
    if not isinstance(payload, dict):
        return ("invalid_shape", "HTTP payload is not a JSON object")
    required_keys = {"total", "bronze_records", "reject_ratio"}
    if not required_keys.issubset(payload):
        return (
            "invalid_shape",
            f"HTTP payload missing keys: {sorted(required_keys - set(payload))}",
        )
    total = payload.get("total")
    bronze_records = payload.get("bronze_records")
    reject_ratio = payload.get("reject_ratio")
    if not isinstance(total, int):
        return ("invalid_shape", "HTTP total must be an integer")
    if not isinstance(bronze_records, int):
        return ("invalid_shape", "HTTP bronze_records must be an integer")
    if not isinstance(reject_ratio, (int, float)):
        return ("invalid_shape", "HTTP reject_ratio must be numeric")
    if total == 0 and bronze_records == 0:
        return (
            "zero_state_unknown_denominator",
            "Explorer summary returned zero with missing denominator",
        )
    if total == 0:
        return ("zero_result", "Explorer summary returned zero rejects")
    return ("nonzero_result", "Explorer summary returned non-zero rejects")


def _classify_http_table_payload(payload: object) -> tuple[str, str]:
    if not isinstance(payload, dict):
        return ("invalid_shape", "HTTP table payload is not a JSON object")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        return ("invalid_shape", "HTTP table payload missing rows list")
    if not rows:
        return ("empty_result", "HTTP table payload returned no rows")
    return ("nonempty_table", "HTTP table payload returned rows")


def _classify_http_freshness_payload(payload: object) -> tuple[str, str]:
    if not isinstance(payload, dict):
        return ("invalid_shape", "HTTP payload is not a JSON object")
    if "age_seconds" not in payload:
        return ("invalid_shape", "HTTP freshness payload missing age_seconds")
    age_seconds = payload.get("age_seconds")
    if age_seconds is None:
        if str(payload.get("status", "")).upper() == "UNKNOWN":
            return (
                "unknown_result",
                "Checkpoint freshness payload returned UNKNOWN due to missing persisted checkpoint evidence",
            )
        return (
            "empty_result",
            "Checkpoint freshness payload returned null age_seconds",
        )
    if not isinstance(age_seconds, (int, float)):
        return ("invalid_shape", "HTTP age_seconds must be numeric or null")
    if age_seconds == 0:
        return ("zero_result", "Checkpoint freshness payload returned zero age")
    return ("nonzero_result", "Checkpoint freshness payload returned non-zero age")


def _audit_prometheus_panel(
    spec: PanelAuditSpec,
    panel: dict[str, Any],
    config: AuditConfig,
) -> AuditResult:
    targets = cast(list[dict[str, Any]], panel.get("targets", []))
    expr = next(
        (
            target.get("expr", "")
            for target in targets
            if isinstance(target.get("expr"), str) and target.get("expr")
        ),
        "",
    )
    if not expr:
        return AuditResult(
            dashboard_uid=spec.dashboard_uid,
            panel_id=spec.panel_id,
            title=spec.title,
            source_kind=spec.source_kind,
            semantic_kind=spec.semantic_kind,
            status="error",
            classification="missing_query",
            detail="Panel has no Prometheus expr target",
            query_preview="",
        )
    rendered_expr = _substitute_dashboard_tokens(expr, config)
    query_url = f"{config.prometheus_base_url}/api/v1/query?" + urlencode(
        {"query": rendered_expr}
    )
    payload = _fetch_json(query_url)
    classification, detail = _classify_prometheus_payload(payload)
    status = "ok"
    if classification in {"invalid_shape", "query_error"}:
        status = "error"
    elif classification == "empty_result" and spec.semantic_kind == "freshness":
        status = "error"
    return AuditResult(
        dashboard_uid=spec.dashboard_uid,
        panel_id=spec.panel_id,
        title=spec.title,
        source_kind=spec.source_kind,
        semantic_kind=spec.semantic_kind,
        status=status,
        classification=classification,
        detail=detail,
        query_preview=rendered_expr[:400],
    )


def _audit_http_panel(
    spec: PanelAuditSpec,
    panel: dict[str, Any],
    config: AuditConfig,
    *,
    app_base_url: str,
) -> AuditResult:
    targets = cast(list[dict[str, Any]], panel.get("targets", []))
    url_template = next(
        (
            target.get("url", "")
            for target in targets
            if isinstance(target.get("url"), str) and target.get("url")
        ),
        "",
    )
    if not url_template:
        return AuditResult(
            dashboard_uid=spec.dashboard_uid,
            panel_id=spec.panel_id,
            title=spec.title,
            source_kind=spec.source_kind,
            semantic_kind=spec.semantic_kind,
            status="error",
            classification="missing_url",
            detail="Panel has no backend URL target",
            query_preview="",
        )
    rendered_url = _substitute_dashboard_tokens(url_template, config)
    payload = _fetch_json(f"{app_base_url}{rendered_url}")
    if spec.semantic_kind == "freshness":
        classification, detail = _classify_http_freshness_payload(payload)
        status = (
            "error" if classification in {"invalid_shape", "empty_result"} else "ok"
        )
    elif spec.semantic_kind == "http_table":
        classification, detail = _classify_http_table_payload(payload)
        status = (
            "error" if classification in {"invalid_shape", "empty_result"} else "ok"
        )
    else:
        classification, detail = _classify_http_payload(payload)
        status = "ok" if classification != "invalid_shape" else "error"
    return AuditResult(
        dashboard_uid=spec.dashboard_uid,
        panel_id=spec.panel_id,
        title=spec.title,
        source_kind=spec.source_kind,
        semantic_kind=spec.semantic_kind,
        status=status,
        classification=classification,
        detail=f"{detail}; app_base_url={app_base_url}",
        query_preview=rendered_url,
    )


def run_audit(config: AuditConfig) -> list[AuditResult]:
    results: list[AuditResult] = []
    resolved_app_base_url: str | None = None
    for spec in REVIEWED_PANEL_SPECS:
        panel = _find_panel(spec)
        if spec.source_kind == "prometheus":
            results.append(_audit_prometheus_panel(spec, panel, config))
        else:
            if resolved_app_base_url is None:
                resolved_app_base_url = _resolve_app_base_url(config)
            results.append(
                _audit_http_panel(
                    spec,
                    panel,
                    config,
                    app_base_url=resolved_app_base_url,
                )
            )
    return results


def _write_report(config: AuditConfig, results: list[AuditResult]) -> None:
    config.output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "config": {
            "prometheus_base_url": config.prometheus_base_url,
            "app_base_url": config.app_base_url,
            "grafana_base_url": config.grafana_base_url,
            "workflow": config.workflow,
            "pipeline": config.pipeline,
            "run_type": config.run_type,
            "run_id": config.run_id,
            "range_hours": config.range_hours,
        },
        "panel_specs": [asdict(spec) for spec in REVIEWED_PANEL_SPECS],
        "results": [asdict(result) for result in results],
    }
    config.output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    config = _parse_args(argv)
    try:
        results = run_audit(config)
    except (FileNotFoundError, LookupError, OSError, json.JSONDecodeError) as exc:
        print(str(exc))
        return 1

    _write_report(config, results)
    for result in results:
        print(
            f"{result.dashboard_uid}#{result.panel_id} {result.title}: "
            f"{result.status}/{result.classification}"
        )
    return 1 if any(result.status != "ok" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
