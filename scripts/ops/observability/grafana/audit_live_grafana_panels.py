"""Run a reviewed live datasource/frame audit for semantically sensitive Grafana panels."""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import monotonic, sleep
from typing import Any, Literal, cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from bioetl.infrastructure.storage.support.atomic_ops import atomic_write_text

DEFAULT_PROMETHEUS_BASE_URL = "http://localhost:9090"
DEFAULT_APP_BASE_URL = "http://localhost:8081"
DEFAULT_GRAFANA_BASE_URL = "http://localhost:3000"
DEFAULT_LOKI_BASE_URL = "http://localhost:3100"
DEFAULT_TEMPO_BASE_URL = "http://localhost:3200"
DEFAULT_GRAFANA_USERNAME = "admin"
DEFAULT_GRAFANA_PASSWORD = ""
DEFAULT_HTTP_DATASOURCE_NAME = "Quarantine Explorer"
DEFAULT_OUTPUT_PATH = Path("reports/observability/grafana/live-panel-audit.json")
DEFAULT_WORKFLOW = "All"
DEFAULT_PIPELINE = "chembl_target"
DEFAULT_RUN_TYPE = "incremental"
DEFAULT_RUN_ID = "-"
DEFAULT_RANGE_HOURS = 24
DEFAULT_REQUEST_TIMEOUT_SECONDS = 15.0
MAX_LOKI_RANGE_HOURS = 1
LOKI_READINESS_POLL_INTERVAL_SECONDS = 0.25
LOKI_READINESS_PROBE_TIMEOUT_SECONDS = 2.0
_HEALTH_PROBE_PATHS: tuple[str, ...] = ("/health/live", "/health")
_DASHBOARD_DIR = Path("grafana/dashboards")
PROCESSED_RECORDS_PANEL_TITLE = "Processed Records"
_PROCESSED_RECORDS_CONTRACT = "processed_records_table_v1"
_UNRESOLVED_IDENTITY_MODES = frozenset(
    {
        "aggregate_scope_requires_exact_run_id",
        "no_manifest_for_scope",
    }
)
_IDENTITY_ANCHOR_PARAMETERS = frozenset(
    {"Run ID [Pipeline]", "Manifest ID [Control Plane]"}
)
_PLACEHOLDER_PREFIXES = (
    "not available",
    "select one concrete pipeline",
)


@dataclass(frozen=True)
class PanelAuditSpec:
    dashboard_uid: str
    panel_id: int
    title: str
    source_kind: Literal["prometheus", "http", "loki", "tempo"]
    semantic_kind: Literal[
        "derived_status",
        "freshness",
        "http_endpoint",
        "http_records",
        "http_summary",
        "http_table",
        "loki_query",
        "prometheus_query",
        "tempo_handoff",
    ]
    target_ref_id: str | None = None
    required: bool = True


@dataclass(frozen=True)
class AuditConfig:
    prometheus_base_url: str
    app_base_url: str
    loki_base_url: str
    tempo_base_url: str
    grafana_base_url: str
    grafana_username: str
    grafana_password: str
    workflow: str
    pipeline: str
    run_type: str
    run_id: str
    range_hours: int
    output_path: Path
    request_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS
    occurrence_id: str = ""


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
    target_ref_id: str | None = None


SEMANTIC_CLASSIFICATION_POLICY: dict[str, str] = {
    "query_invalid": "block",
    "timeout_budget_exceeded": "block_when_required",
    "datasource_unavailable": "block_when_required",
    "blocked_backend_unavailable": "block_when_required",
    "empty_result": "review_required",
    "zero_result": "pass",
    "nonzero_result": "pass",
    "nonempty_result": "pass",
    "nonempty_table": "pass",
    "resolved_identity": "pass",
    "resolved_numeric": "pass",
    "resolved_zero": "pass",
    "expected_empty": "pass",
    "unknown_result": "review_required",
    "telemetry_missing": "review_required_unless_explicitly_reviewed",
}
_SEMANTIC_CLASSIFICATION_ALIASES = {
    "invalid_shape": "query_invalid",
    "missing_query": "query_invalid",
    "missing_url": "query_invalid",
    "query_error": "query_invalid",
    "blocked_unavailable": "datasource_unavailable",
    "no_data": "empty_result",
    "partial_data": "unknown_result",
    "unresolved_identity": "unknown_result",
    "zero_state_unknown_denominator": "unknown_result",
}
_UNREGISTERED_CLASSIFICATION_POLICY = "review_required"
_REVIEWED_SEMANTIC_OUTCOMES = frozenset(
    {
        ("bioetl-dq-v2", 8, "telemetry_missing"),
        ("bioetl-dq-v2", 101, "telemetry_missing"),
    }
)


def _semantic_decision(
    *,
    status: str,
    policy: str,
    required: bool,
    reviewed: bool,
) -> str:
    """Map status/policy/required/reviewed into a gate decision token."""
    if status != "ok":
        return "block"
    if policy == "block":
        return "block"
    if policy == "block_when_required":
        return "block" if required else "pass_optional"
    if policy in {
        "review_required",
        "review_required_unless_explicitly_reviewed",
    }:
        return "pass_reviewed" if reviewed else "review"
    return "pass"


def _semantic_outcome_for_result(
    result: AuditResult,
    *,
    required_by_panel: dict[tuple[str, int, str], bool],
) -> dict[str, Any]:
    """Build one panel-attributable semantic outcome row."""
    key = (result.dashboard_uid, result.panel_id, result.target_ref_id)
    required = required_by_panel.get(key, True)
    canonical = _SEMANTIC_CLASSIFICATION_ALIASES.get(
        result.classification,
        result.classification,
    )
    reviewed = (
        result.dashboard_uid,
        result.panel_id,
        canonical,
    ) in _REVIEWED_SEMANTIC_OUTCOMES
    policy = SEMANTIC_CLASSIFICATION_POLICY.get(
        canonical,
        _UNREGISTERED_CLASSIFICATION_POLICY,
    )
    decision = _semantic_decision(
        status=result.status,
        policy=policy,
        required=required,
        reviewed=reviewed,
    )
    return {
        "dashboard_uid": result.dashboard_uid,
        "panel_id": result.panel_id,
        "target_ref_id": result.target_ref_id,
        "source_kind": result.source_kind,
        "required": required,
        "classification": result.classification,
        "canonical_classification": canonical,
        "policy": policy,
        "decision": decision,
    }


def semantic_gate_evidence(results: list[AuditResult]) -> dict[str, Any]:
    """Build panel-attributable semantic gate evidence from live results."""
    required_by_panel = {
        (spec.dashboard_uid, spec.panel_id, spec.target_ref_id): spec.required
        for spec in effective_panel_specs()
    }
    outcomes = [
        _semantic_outcome_for_result(result, required_by_panel=required_by_panel)
        for result in results
    ]

    blocking_count = sum(item["decision"] == "block" for item in outcomes)
    review_count = sum(item["decision"] == "review" for item in outcomes)
    if blocking_count:
        status = "fail"
    elif review_count:
        status = "review_required"
    else:
        status = "pass"
    return {
        "status": status,
        "blocking_count": blocking_count,
        "review_count": review_count,
        "classification_policy": SEMANTIC_CLASSIFICATION_POLICY,
        "unregistered_classification_policy": _UNREGISTERED_CLASSIFICATION_POLICY,
        "panel_outcomes": outcomes,
    }


REVIEWED_PANEL_SPECS: tuple[PanelAuditSpec, ...] = (
    # Runtime Loki log-hygiene panels (250/251/257) were removed from the
    # shipped bioetl-runtime surface (2026-07). Keep HTTP/Prometheus reviewed
    # panels only; Loki coverage is optional via discovered specs when present.
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
        title=PROCESSED_RECORDS_PANEL_TITLE,
        source_kind="http",
        semantic_kind="http_table",
    ),
    PanelAuditSpec(
        dashboard_uid="bioetl-overview-v2",
        panel_id=9301,
        title=PROCESSED_RECORDS_PANEL_TITLE,
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
        title="Time Range · Worst Freshness Age (hours; SLA 24/72)",
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
        title=PROCESSED_RECORDS_PANEL_TITLE,
        source_kind="http",
        semantic_kind="http_table",
    ),
    PanelAuditSpec(
        dashboard_uid="bioetl-control-plane-v1",
        panel_id=892,
        title="Monitor: Checkpoint Freshness Lag (seconds)",
        source_kind="prometheus",
        semantic_kind="freshness",
        target_ref_id="A",
    ),
    PanelAuditSpec(
        dashboard_uid="bioetl-runtime",
        panel_id=9403,
        title=PROCESSED_RECORDS_PANEL_TITLE,
        source_kind="http",
        semantic_kind="http_table",
    ),
    PanelAuditSpec(
        dashboard_uid="bioetl-provider-health-v2",
        panel_id=9403,
        title=PROCESSED_RECORDS_PANEL_TITLE,
        source_kind="http",
        semantic_kind="http_table",
    ),
    # bioetl-workflow-overview removed from shipping surface (epic #6647).
)


def _read_env(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value or default


def _auth_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
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
        "--loki-base-url",
        default=DEFAULT_LOKI_BASE_URL,
        help="Loki HTTP API base URL used for LogQL panel smoke validation.",
    )
    parser.add_argument(
        "--tempo-base-url",
        default=DEFAULT_TEMPO_BASE_URL,
        help="Tempo HTTP API base URL used for trace handoff smoke validation.",
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
    parser.add_argument(
        "--request-timeout-seconds",
        type=float,
        default=DEFAULT_REQUEST_TIMEOUT_SECONDS,
        help=(
            "Per-request timeout for Prometheus, Grafana datasource discovery, "
            "Quarantine Explorer, Loki, and Tempo probes."
        ),
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument(
        "--occurrence-id",
        default="",
        help="Bind this semantic artifact to one dashboard release occurrence.",
    )
    args = parser.parse_args(argv)
    return AuditConfig(
        prometheus_base_url=args.prometheus_base_url.rstrip("/"),
        app_base_url=args.app_base_url.rstrip("/"),
        loki_base_url=args.loki_base_url.rstrip("/"),
        tempo_base_url=args.tempo_base_url.rstrip("/"),
        grafana_base_url=args.grafana_base_url.rstrip("/"),
        grafana_username=args.grafana_username,
        grafana_password=args.grafana_password,
        workflow=args.workflow,
        pipeline=args.pipeline,
        run_type=args.run_type,
        run_id=args.run_id,
        range_hours=args.range_hours,
        output_path=args.output,
        request_timeout_seconds=max(float(args.request_timeout_seconds), 0.1),
        occurrence_id=str(args.occurrence_id).strip(),
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


def _datasource_name(panel: dict[str, Any], target: dict[str, Any]) -> str:
    datasource = target.get("datasource") or panel.get("datasource") or ""
    if isinstance(datasource, dict):
        return str(
            datasource.get("type")
            or datasource.get("uid")
            or datasource.get("name")
            or ""
        )
    return str(datasource)


def _target_ref_id(target: dict[str, Any]) -> str | None:
    ref_id = target.get("refId")
    if isinstance(ref_id, str) and ref_id:
        return ref_id
    return None


def _infer_http_semantic_kind(url: str) -> str:
    if "checkpoint-freshness" in url:
        return "freshness"
    if "identity-table" in url or "processed-records" in url:
        return "http_table"
    if "filtered-records" in url:
        return "http_records"
    if "filtered-stats" in url:
        return "http_summary"
    return "http_endpoint"


def _panel_specs_from_targets(
    *,
    dashboard_uid: str,
    panel_id: int,
    title: str,
    panel: dict[str, Any],
) -> list[PanelAuditSpec]:
    specs: list[PanelAuditSpec] = []
    for target in cast(list[dict[str, Any]], panel.get("targets", [])):
        ref_id = _target_ref_id(target)
        url = target.get("url")
        if isinstance(url, str) and url:
            specs.append(
                PanelAuditSpec(
                    dashboard_uid=dashboard_uid,
                    panel_id=panel_id,
                    title=title,
                    source_kind="http",
                    semantic_kind=cast(
                        Literal[
                            "freshness",
                            "http_endpoint",
                            "http_records",
                            "http_summary",
                            "http_table",
                        ],
                        _infer_http_semantic_kind(url),
                    ),
                    target_ref_id=ref_id,
                    required=False,
                )
            )
            continue
        expr = target.get("expr")
        if not isinstance(expr, str) or not expr.strip():
            continue
        datasource_name = _datasource_name(panel, target).lower()
        kind = "loki" if "loki" in datasource_name else "prometheus"
        semantic = "loki_query" if kind == "loki" else "prometheus_query"
        specs.append(
            PanelAuditSpec(
                dashboard_uid=dashboard_uid,
                panel_id=panel_id,
                title=title,
                source_kind=kind,  # type: ignore[arg-type]
                semantic_kind=semantic,  # type: ignore[arg-type]
                target_ref_id=ref_id,
                required=False,
            )
        )
    return specs


def _panel_specs_from_links(
    *,
    dashboard_uid: str,
    panel_id: int,
    title: str,
    panel: dict[str, Any],
) -> list[PanelAuditSpec]:
    specs: list[PanelAuditSpec] = []
    for link in cast(list[dict[str, Any]], panel.get("links", [])):
        link_url = str(link.get("url") or "")
        if "exploretraces-app" not in link_url and "var-ds=tempo" not in link_url:
            continue
        specs.append(
            PanelAuditSpec(
                dashboard_uid=dashboard_uid,
                panel_id=panel_id,
                title=f"{title} :: {link.get('title') or 'Tempo handoff'}",
                source_kind="tempo",
                semantic_kind="tempo_handoff",
                target_ref_id=str(link.get("title") or "tempo"),
                required=False,
            )
        )
    return specs


def _classify_prometheus_vector(result: object) -> tuple[str, str]:
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
    if all(abs(value) <= 1e-12 for value in values):
        return ("zero_result", "Prometheus vector returned only zero values")
    return ("nonzero_result", "Prometheus vector returned non-zero values")


def _classify_prometheus_scalar(result: object) -> tuple[str, str]:
    if not isinstance(result, list) or len(result) != 2:
        return ("invalid_shape", "Prometheus scalar result missing value pair")
    try:
        value = float(result[1])
    except (TypeError, ValueError):
        return ("invalid_shape", "Prometheus scalar value is not numeric")
    if abs(value) <= 1e-12:
        return ("zero_result", "Prometheus scalar returned zero")
    return ("nonzero_result", "Prometheus scalar returned non-zero value")


def _discover_dashboard_panel_specs() -> tuple[PanelAuditSpec, ...]:
    specs: list[PanelAuditSpec] = []
    for path in sorted(_DASHBOARD_DIR.glob("*.json")):
        dashboard = json.loads(path.read_text(encoding="utf-8"))
        dashboard_uid = str(dashboard.get("uid") or path.stem)
        for panel in _iter_panels(
            cast(list[dict[str, Any]], dashboard.get("panels", []))
        ):
            panel_id = panel.get("id")
            if not isinstance(panel_id, int):
                continue
            title = str(panel.get("title") or f"panel-{panel_id}")
            specs.extend(
                _panel_specs_from_targets(
                    dashboard_uid=dashboard_uid,
                    panel_id=panel_id,
                    title=title,
                    panel=panel,
                )
            )
            specs.extend(
                _panel_specs_from_links(
                    dashboard_uid=dashboard_uid,
                    panel_id=panel_id,
                    title=title,
                    panel=panel,
                )
            )
    return tuple(specs)


def _bind_reviewed_panel_spec(
    reviewed_spec: PanelAuditSpec,
    discovered_specs: tuple[PanelAuditSpec, ...] | list[PanelAuditSpec],
) -> PanelAuditSpec:
    """Attach a unique discovered target_ref_id when the reviewed spec omits one."""
    if reviewed_spec.target_ref_id is not None:
        return reviewed_spec
    matching_targets = [
        spec
        for spec in discovered_specs
        if spec.dashboard_uid == reviewed_spec.dashboard_uid
        and spec.panel_id == reviewed_spec.panel_id
        and spec.source_kind == reviewed_spec.source_kind
    ]
    if len(matching_targets) != 1 or not matching_targets[0].target_ref_id:
        return reviewed_spec
    return PanelAuditSpec(
        dashboard_uid=reviewed_spec.dashboard_uid,
        panel_id=reviewed_spec.panel_id,
        title=reviewed_spec.title,
        source_kind=reviewed_spec.source_kind,
        semantic_kind=reviewed_spec.semantic_kind,
        target_ref_id=matching_targets[0].target_ref_id,
        required=reviewed_spec.required,
    )


def effective_panel_specs() -> tuple[PanelAuditSpec, ...]:
    """Return curated required specs plus generated coverage for all executable panels."""
    discovered_specs = _discover_dashboard_panel_specs()
    specs: list[PanelAuditSpec] = [
        _bind_reviewed_panel_spec(reviewed_spec, discovered_specs)
        for reviewed_spec in REVIEWED_PANEL_SPECS
    ]

    covered = {
        (spec.dashboard_uid, spec.panel_id, spec.source_kind, spec.target_ref_id)
        for spec in specs
    }
    wildcard_covered = {
        (spec.dashboard_uid, spec.panel_id, spec.source_kind)
        for spec in specs
        if spec.target_ref_id is None
    }
    for spec in discovered_specs:
        key = (spec.dashboard_uid, spec.panel_id, spec.source_kind, spec.target_ref_id)
        wildcard_key = (spec.dashboard_uid, spec.panel_id, spec.source_kind)
        if key in covered or wildcard_key in wildcard_covered:
            continue
        specs.append(spec)
        covered.add(key)
    return tuple(specs)


def _time_window(
    config: AuditConfig,
    *,
    range_hours: int | None = None,
) -> tuple[str, str]:
    effective_range_hours = config.range_hours if range_hours is None else range_hours
    end = datetime.now(tz=UTC)
    start = end - timedelta(hours=effective_range_hours)
    return start.isoformat(), end.isoformat()


def _substitute_dashboard_tokens(
    template: str,
    config: AuditConfig,
    *,
    range_hours: int | None = None,
) -> str:
    effective_range_hours = config.range_hours if range_hours is None else range_hours
    start_iso, end_iso = _time_window(config, range_hours=effective_range_hours)
    quarantine_run_id = "" if config.run_id in {"", "-"} else config.run_id
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
        "${workflow:regex}": config.workflow,
        "${pipeline:regex}": config.pipeline,
        "${run_type:regex}": config.run_type,
        "${run_id:regex}": config.run_id,
        "${pipeline:csv}": config.pipeline,
        "${run_type:csv}": config.run_type,
        "$pipeline_context": config.pipeline,
        "${pipeline_context}": config.pipeline,
        "${pipeline_context:queryparam}": quote(config.pipeline, safe=""),
        "${pipeline_context:regex}": config.pipeline,
        "${pipeline_context:csv}": config.pipeline,
        "$run_type_context": config.run_type,
        "${run_type_context}": config.run_type,
        "${run_type_context:queryparam}": quote(config.run_type, safe=""),
        "${run_type_context:regex}": config.run_type,
        "${run_type_context:csv}": config.run_type,
        "$provider_context": "chembl",
        "${provider_context}": "chembl",
        "${provider_context:queryparam}": "chembl",
        "${provider_context:regex}": "chembl",
        "$provider": "chembl",
        "${provider}": "chembl",
        "${provider:regex}": "chembl",
        "$adapter": "chembl",
        "${adapter}": "chembl",
        "${adapter:regex}": "chembl",
        "$stage": ".*",
        "${stage}": ".*",
        "${stage:regex}": ".*",
        "$status": ".*",
        "${status}": ".*",
        "${status:regex}": ".*",
        "$step_kind": ".*",
        "${step_kind}": ".*",
        "${step_kind:regex}": ".*",
        "${step_kind:csv}": ".*",
        "$step_status": ".*",
        "${step_status}": ".*",
        "${step_status:regex}": ".*",
        "${step_status:csv}": ".*",
        "$provider_hint": "chembl",
        "${provider_hint}": "chembl",
        "${provider_hint:regex}": "chembl",
        "$__range": f"{effective_range_hours}h",
        "${__range}": f"{effective_range_hours}h",
        "${__range_s}": str(effective_range_hours * 3600),
        "$__interval": "5m",
        "${__interval}": "5m",
        "$__rate_interval": "5m",
        "${__rate_interval}": "5m",
        "${reason_code:csv}": "",
        "${field:csv}": "",
        "${quarantine_run_id}": quarantine_run_id,
        "${quarantine_run_id:queryparam}": quote(quarantine_run_id, safe=""),
        "${payload_hash}": "",
        "${__from:date:iso}": quote(start_iso, safe=""),
        "${__to:date:iso}": quote(end_iso, safe=""),
    }
    rendered = template
    for token, value in sorted(
        replacements.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        rendered = rendered.replace(token, value)
    return rendered


def _bounded_loki_range_hours(config: AuditConfig) -> int:
    return max(1, min(config.range_hours, MAX_LOKI_RANGE_HOURS))


def _loki_query_range_bounds(config: AuditConfig) -> tuple[str, str]:
    start_iso, end_iso = _time_window(
        config,
        range_hours=_bounded_loki_range_hours(config),
    )
    start = datetime.fromisoformat(start_iso).timestamp()
    end = datetime.fromisoformat(end_iso).timestamp()
    return (str(int(start * 1_000_000_000)), str(int(end * 1_000_000_000)))


def _fetch_json(url: str, *, timeout_seconds: float) -> object:
    with urlopen(url, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_text(url: str, *, timeout_seconds: float) -> str:
    with urlopen(url, timeout=timeout_seconds) as response:
        return response.read().decode("utf-8")


def _request_json(url: str, *, auth_header: str, timeout_seconds: float) -> object:
    request = Request(url, headers={"Authorization": auth_header})
    with urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def _auth_header_for_url(url: str, config: AuditConfig) -> str | None:
    parts = urlsplit(url)
    if parts.username or parts.password:
        return _auth_header(parts.username or "", parts.password or "")
    grafana_base = config.grafana_base_url.rstrip("/")
    if url.startswith(f"{grafana_base}/api/datasources/proxy/"):
        return _auth_header(config.grafana_username, config.grafana_password)
    return None


def _strip_url_userinfo(url: str) -> str:
    parts = urlsplit(url)
    if not parts.username and not parts.password:
        return url
    hostname = parts.hostname or ""
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    port = f":{parts.port}" if parts.port is not None else ""
    return urlunsplit(
        (parts.scheme, f"{hostname}{port}", parts.path, parts.query, parts.fragment)
    )


def _fetch_json_with_optional_auth(
    url: str,
    *,
    config: AuditConfig,
    timeout_seconds: float,
) -> object:
    request_url = _strip_url_userinfo(url)
    auth_header = _auth_header_for_url(url, config)
    if auth_header:
        return _request_json(
            request_url,
            auth_header=auth_header,
            timeout_seconds=timeout_seconds,
        )
    return _fetch_json(request_url, timeout_seconds=timeout_seconds)


def _normalize_host_access_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.hostname != "host.docker.internal":
        return url.rstrip("/")
    port = f":{parts.port}" if parts.port is not None else ""
    host = f"localhost{port}"
    return urlunsplit(
        (parts.scheme, host, parts.path, parts.query, parts.fragment)
    ).rstrip("/")


def _zero_bind_access_url(url: str) -> str | None:
    parts = urlsplit(url)
    if parts.hostname not in {"localhost", "127.0.0.1"}:
        return None
    port = f":{parts.port}" if parts.port is not None else ""
    host = f"0.0.0.0{port}"
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
        timeout_seconds=config.request_timeout_seconds,
    )
    if not isinstance(payload, dict):
        return None
    datasource_url = payload.get("url")
    if not isinstance(datasource_url, str) or not datasource_url.strip():
        return None
    return datasource_url.rstrip("/")


def _grafana_http_datasource_proxy_url(config: AuditConfig) -> str:
    return f"{config.grafana_base_url}/api/datasources/proxy/uid/quarantine-explorer"


def _candidate_app_base_urls(config: AuditConfig) -> tuple[str, ...]:
    candidates: list[str] = [config.app_base_url.rstrip("/")]
    if config.app_base_url.rstrip("/") != DEFAULT_APP_BASE_URL:
        if "/api/datasources/proxy/uid/" not in config.app_base_url:
            candidates.append(_grafana_http_datasource_proxy_url(config))
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
    candidates.append(_grafana_http_datasource_proxy_url(config))

    for candidate in tuple(candidates):
        zero_bind_url = _zero_bind_access_url(candidate)
        if zero_bind_url:
            candidates.append(zero_bind_url)

    deduped: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in deduped:
            deduped.append(candidate)
    return tuple(deduped)


def _probe_app_health(
    candidate_base_url: str, *, config: AuditConfig, timeout_seconds: float
) -> tuple[str, object] | None:
    for path in _HEALTH_PROBE_PATHS:
        try:
            payload = _fetch_json_with_optional_auth(
                f"{candidate_base_url}{path}",
                config=config,
                timeout_seconds=timeout_seconds,
            )
        except (HTTPError, URLError, OSError, json.JSONDecodeError):
            continue
        return (path, payload)
    return None


def _resolve_app_base_url(config: AuditConfig) -> str:
    attempted: list[str] = []
    for candidate in _candidate_app_base_urls(config):
        probe = _probe_app_health(
            candidate,
            config=config,
            timeout_seconds=config.request_timeout_seconds,
        )
        if probe is None:
            attempted.extend(f"{candidate}{path}" for path in _HEALTH_PROBE_PATHS)
            continue
        path, payload = probe
        attempted.append(f"{candidate}{path}")
        if isinstance(payload, dict):
            return candidate
    attempted_urls = ", ".join(_redact_url(url) for url in attempted)
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
        return _classify_prometheus_vector(result)
    if result_type == "scalar":
        return _classify_prometheus_scalar(result)
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


def _prefixed_cell_value(
    row: dict[str, object],
    *,
    parameter: str,
    field: str,
) -> tuple[str | None, str | None]:
    cell = row.get(field)
    if not isinstance(cell, str):
        return (None, f"{field} must be a prefixed string")
    prefix, separator, display = cell.partition("|")
    if separator != "|" or prefix != parameter:
        return (None, f"{field} prefix does not match parameter")
    display = display.strip()
    if not display:
        return (None, f"{field} display value is empty")
    return (display, None)


def _is_nonnegative_number(raw: str) -> bool:
    normalized = raw.replace(" ", "")
    try:
        value = float(normalized)
    except ValueError:
        return False
    return math.isfinite(value) and value >= 0


def _validate_processed_records_percentage(
    parameter: str, percentage: str
) -> str | None:
    if percentage == "No data":
        return None
    if percentage.endswith("%") and _is_nonnegative_number(percentage[:-1]):
        return None
    return f"Processed Records row {parameter!r} has malformed percentage"


def _processed_records_parameter(
    raw_row: dict[str, object], *, index: int, parameters: set[str]
) -> tuple[str | None, str | None]:
    parameter = raw_row.get("parameter")
    if not isinstance(parameter, str) or not parameter.strip():
        return None, f"Processed Records row {index} has no parameter"
    if parameter in parameters:
        return None, f"Processed Records parameter is duplicated: {parameter}"
    parameters.add(parameter)
    return parameter, None


def _processed_records_numeric_value(
    parameter: str, value: str
) -> tuple[float | None, bool, str | None]:
    if value == "No data":
        return (None, True, None)
    if not _is_nonnegative_number(value):
        return (
            None,
            False,
            f"Processed Records row {parameter!r} has a non-numeric value",
        )
    return (float(value.replace(" ", "")), False, None)


def _parse_processed_records_row(
    raw_row: object,
    *,
    index: int,
    parameters: set[str],
) -> tuple[float | None, bool, str | None]:
    """Return (numeric_value|None, is_missing, error_detail|None)."""
    if not isinstance(raw_row, dict):
        return (None, False, f"Processed Records row {index} is not an object")
    parameter, parameter_error = _processed_records_parameter(
        raw_row, index=index, parameters=parameters
    )
    if parameter_error is not None:
        return (None, False, parameter_error)
    assert parameter is not None

    value, value_error = _prefixed_cell_value(
        raw_row, parameter=parameter, field="value"
    )
    percentage, percentage_error = _prefixed_cell_value(
        raw_row, parameter=parameter, field="percintage"
    )
    if value_error or percentage_error:
        return (
            None,
            False,
            f"Processed Records row {parameter!r} is malformed: "
            f"{value_error or percentage_error}",
        )
    assert value is not None
    assert percentage is not None
    percentage_error_detail = _validate_processed_records_percentage(
        parameter, percentage
    )
    if percentage_error_detail is not None:
        return (None, False, percentage_error_detail)
    row_status = raw_row.get("row_status", "")
    if not isinstance(row_status, str):
        return (
            None,
            False,
            f"Processed Records row {parameter!r} has malformed row_status",
        )
    return _processed_records_numeric_value(parameter, value)


def _summarize_processed_records_values(
    *,
    row_count: int,
    missing_values: int,
    numeric_values: list[float],
) -> tuple[str, str]:
    if missing_values == row_count:
        return ("no_data", "Processed Records returned only No data values")
    if missing_values:
        return ("partial_data", "Processed Records mixed numeric and No data values")
    if all(value == 0 for value in numeric_values):
        return ("resolved_zero", "Processed Records returned resolved numeric zero")
    return ("resolved_numeric", "Processed Records returned resolved numeric values")


def _classify_processed_records_payload(payload: dict[str, object]) -> tuple[str, str]:
    if payload.get("contract") != _PROCESSED_RECORDS_CONTRACT:
        return (
            "invalid_shape",
            "Processed Records payload has an unknown or missing contract",
        )
    rows = payload.get("rows")
    if not isinstance(rows, list):
        return ("invalid_shape", "Processed Records payload missing rows list")
    if not rows:
        return ("empty_result", "Processed Records payload returned no rows")

    numeric_values: list[float] = []
    missing_values = 0
    parameters: set[str] = set()
    for index, raw_row in enumerate(rows):
        numeric_value, is_missing, error_detail = _parse_processed_records_row(
            raw_row, index=index, parameters=parameters
        )
        if error_detail is not None:
            return ("invalid_shape", error_detail)
        if is_missing:
            missing_values += 1
            continue
        assert numeric_value is not None
        numeric_values.append(numeric_value)

    return _summarize_processed_records_values(
        row_count=len(rows),
        missing_values=missing_values,
        numeric_values=numeric_values,
    )


def _is_identity_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized in {"", "-", "no data", "none", "null", "unknown"} or any(
        normalized.startswith(prefix) for prefix in _PLACEHOLDER_PREFIXES
    )


def _collect_identity_anchors(
    rows: list[object],
) -> tuple[dict[str, str] | None, tuple[str, str] | None]:
    anchors: dict[str, str] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            return None, ("invalid_shape", f"Identity row {index} is not an object")
        parameter = row.get("parameter")
        value = row.get("value")
        if not isinstance(parameter, str) or not isinstance(value, str):
            return None, ("invalid_shape", f"Identity row {index} is malformed")
        if parameter in _IDENTITY_ANCHOR_PARAMETERS:
            anchors[parameter] = value
    return anchors, None


def _classify_identity_anchors(anchors: dict[str, str]) -> tuple[str, str]:
    missing_anchors = _IDENTITY_ANCHOR_PARAMETERS - anchors.keys()
    if missing_anchors:
        return (
            "unresolved_identity",
            f"Identity payload missing anchors: {sorted(missing_anchors)}",
        )
    placeholder_anchors = sorted(
        parameter
        for parameter, value in anchors.items()
        if _is_identity_placeholder(value)
    )
    if placeholder_anchors:
        return (
            "unresolved_identity",
            f"Identity payload has placeholder anchors: {placeholder_anchors}",
        )
    return ("resolved_identity", "Identity payload returned concrete run anchors")


def _classify_identity_payload(payload: dict[str, object]) -> tuple[str, str]:
    resolved_via = payload.get("resolved_via")
    if not isinstance(resolved_via, str) or not resolved_via:
        return ("invalid_shape", "Identity payload missing resolved_via")
    if resolved_via in _UNRESOLVED_IDENTITY_MODES:
        return ("unresolved_identity", f"Identity scope resolved via {resolved_via}")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        return ("invalid_shape", "Identity payload missing rows list")
    if not rows:
        return ("empty_result", "Identity payload returned no rows")

    anchors, error = _collect_identity_anchors(rows)
    if error is not None:
        return error
    assert anchors is not None
    return _classify_identity_anchors(anchors)


def _classify_http_table_payload(
    payload: object,
    *,
    title: str | None = None,
) -> tuple[str, str]:
    if not isinstance(payload, dict):
        return ("invalid_shape", "HTTP table payload is not a JSON object")
    if title == PROCESSED_RECORDS_PANEL_TITLE or "contract" in payload:
        return _classify_processed_records_payload(payload)
    if title == "ID" or "resolved_via" in payload:
        return _classify_identity_payload(payload)
    rows = payload.get("rows")
    if not isinstance(rows, list):
        return ("invalid_shape", "HTTP table payload missing rows list")
    if not rows:
        return ("empty_result", "HTTP table payload returned no rows")
    return ("nonempty_table", "HTTP table payload returned rows")


def _classify_http_endpoint_payload(payload: object) -> tuple[str, str]:
    if isinstance(payload, dict):
        if not payload:
            return ("expected_empty", "HTTP endpoint returned an empty object")
        return ("nonempty_result", "HTTP endpoint returned a JSON object")
    if isinstance(payload, list):
        if not payload:
            return ("expected_empty", "HTTP endpoint returned an empty list")
        return ("nonempty_result", "HTTP endpoint returned JSON rows")
    return ("invalid_shape", "HTTP endpoint did not return a JSON object or list")


def _classify_http_records_payload(payload: object) -> tuple[str, str]:
    if not isinstance(payload, dict):
        return ("invalid_shape", "HTTP records payload is not a JSON object")
    items = payload.get("items")
    total = payload.get("total")
    if not isinstance(items, list):
        return ("invalid_shape", "HTTP records payload missing items list")
    if not isinstance(total, int):
        return ("invalid_shape", "HTTP records payload missing integer total")
    if total == 0 and not items:
        return ("zero_result", "HTTP records payload returned zero rows")
    if total > 0 and items:
        return ("nonempty_result", "HTTP records payload returned rows")
    return (
        "invalid_shape",
        "HTTP records payload total/items disagree",
    )


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


def _classify_loki_payload(payload: object) -> tuple[str, str]:
    if not isinstance(payload, dict):
        return ("invalid_shape", "Loki payload is not a JSON object")
    if payload.get("status") != "success":
        return ("query_error", f"Loki status={payload.get('status')!r}")
    data = payload.get("data")
    if not isinstance(data, dict):
        return ("invalid_shape", "Loki payload missing data object")
    result = data.get("result")
    if not isinstance(result, list):
        return ("invalid_shape", "Loki result must be a list")
    if not result:
        return (
            "expected_empty",
            "Loki returned no streams for the scoped query; this is valid for sparse local runs",
        )
    return ("nonempty_result", "Loki returned scoped log evidence")


def _classify_tempo_search_payload(payload: object) -> tuple[str, str]:
    if not isinstance(payload, dict):
        return ("invalid_shape", "Tempo search payload is not a JSON object")
    traces = payload.get("traces")
    if not isinstance(traces, list):
        return ("invalid_shape", "Tempo search payload missing traces list")
    if not traces:
        return (
            "expected_empty",
            "Tempo returned no traces; NoOpTracing or sparse local trace ingestion is valid",
        )
    return ("nonempty_result", "Tempo returned trace search evidence")


def _select_target(
    panel: dict[str, Any],
    spec: PanelAuditSpec,
    *,
    field: str,
) -> dict[str, Any] | None:
    targets = cast(list[dict[str, Any]], panel.get("targets", []))
    for target in targets:
        if (
            spec.target_ref_id is not None
            and _target_ref_id(target) != spec.target_ref_id
        ):
            continue
        value = target.get(field)
        if isinstance(value, str) and value:
            return target
    return None


def _audit_prometheus_panel(
    spec: PanelAuditSpec,
    panel: dict[str, Any],
    config: AuditConfig,
) -> AuditResult:
    target = _select_target(panel, spec, field="expr")
    expr = str(target.get("expr") or "") if target is not None else ""
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
            target_ref_id=spec.target_ref_id,
        )
    rendered_expr = _substitute_dashboard_tokens(expr, config)
    query_url = f"{config.prometheus_base_url}/api/v1/query?" + urlencode(
        {"query": rendered_expr}
    )
    payload = _fetch_json(query_url, timeout_seconds=config.request_timeout_seconds)
    classification, detail = _classify_prometheus_payload(payload)
    if classification == "empty_result" and spec.semantic_kind == "freshness":
        classification = "telemetry_missing"
        detail = (
            "Freshness metric returned no samples for the selected scope/range; "
            "the dashboard must render UNKNOWN rather than a false healthy zero"
        )
    status = "ok"
    if classification in {"invalid_shape", "query_error"}:
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
        target_ref_id=spec.target_ref_id,
    )


_HTTP_TABLE_ERROR_CLASSIFICATIONS = frozenset(
    {
        "empty_result",
        "invalid_shape",
        "no_data",
        "partial_data",
        "unresolved_identity",
    }
)


def _classify_http_panel_payload(
    spec: PanelAuditSpec, payload: object
) -> tuple[str, str, str]:
    """Return (status, classification, detail) for an HTTP panel payload."""
    if spec.semantic_kind == "freshness":
        classification, detail = _classify_http_freshness_payload(payload)
        status = (
            "error" if classification in {"invalid_shape", "empty_result"} else "ok"
        )
        return status, classification, detail
    if spec.semantic_kind == "http_table":
        classification, detail = _classify_http_table_payload(payload, title=spec.title)
        status = (
            "error" if classification in _HTTP_TABLE_ERROR_CLASSIFICATIONS else "ok"
        )
        return status, classification, detail
    if spec.semantic_kind == "http_summary":
        classification, detail = _classify_http_payload(payload)
    elif spec.semantic_kind == "http_records":
        classification, detail = _classify_http_records_payload(payload)
    else:
        classification, detail = _classify_http_endpoint_payload(payload)
    status = "error" if classification == "invalid_shape" and spec.required else "ok"
    return status, classification, detail


def _audit_http_panel(
    spec: PanelAuditSpec,
    panel: dict[str, Any],
    config: AuditConfig,
    *,
    app_base_url: str,
) -> AuditResult:
    target = _select_target(panel, spec, field="url")
    url_template = str(target.get("url") or "") if target is not None else ""
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
            target_ref_id=spec.target_ref_id,
        )
    rendered_url = _substitute_dashboard_tokens(url_template, config)
    payload = _fetch_json_with_optional_auth(
        f"{app_base_url}{rendered_url}",
        config=config,
        timeout_seconds=config.request_timeout_seconds,
    )
    status, classification, detail = _classify_http_panel_payload(spec, payload)
    return AuditResult(
        dashboard_uid=spec.dashboard_uid,
        panel_id=spec.panel_id,
        title=spec.title,
        source_kind=spec.source_kind,
        semantic_kind=spec.semantic_kind,
        status=status,
        classification=classification,
        detail=f"{detail}; app_base_url={_redact_url(app_base_url)}",
        query_preview=rendered_url,
        target_ref_id=spec.target_ref_id,
    )


def _wait_for_loki_ready(
    config: AuditConfig,
    *,
    started_at: float,
) -> tuple[float, str | None]:
    """Poll Loki readiness while preserving the shared readiness/query budget."""
    remaining_timeout = config.request_timeout_seconds
    last_detail: str | None = None
    while remaining_timeout > 0:
        try:
            readiness = _fetch_text(
                f"{config.loki_base_url}/ready",
                timeout_seconds=min(
                    remaining_timeout,
                    LOKI_READINESS_PROBE_TIMEOUT_SECONDS,
                ),
            )
            if readiness.strip().lower() == "ready":
                elapsed = monotonic() - started_at
                return (config.request_timeout_seconds - elapsed, None)
            last_detail = f"unexpected /ready response: {readiness[:80]!r}"
        except (HTTPError, URLError, OSError, UnicodeError) as exc:
            last_detail = f"{type(exc).__name__}: {exc}"

        elapsed = monotonic() - started_at
        remaining_timeout = config.request_timeout_seconds - elapsed
        if remaining_timeout <= 0:
            break
        sleep(min(LOKI_READINESS_POLL_INTERVAL_SECONDS, remaining_timeout))
        elapsed = monotonic() - started_at
        remaining_timeout = config.request_timeout_seconds - elapsed
    return (remaining_timeout, last_detail)


def _loki_timeout_result(
    spec: PanelAuditSpec,
    config: AuditConfig,
    *,
    rendered_expr: str,
    phase: str,
    latency_seconds: float,
    last_detail: str | None = None,
) -> AuditResult:
    detail = (
        f"Loki {phase} exhausted the governed request budget; "
        f"latency_seconds={latency_seconds:.3f}; "
        f"budget_seconds={config.request_timeout_seconds:.3f}"
    )
    if last_detail:
        detail += f"; last_readiness={last_detail}"
    return AuditResult(
        dashboard_uid=spec.dashboard_uid,
        panel_id=spec.panel_id,
        title=spec.title,
        source_kind=spec.source_kind,
        semantic_kind=spec.semantic_kind,
        status="error" if spec.required else "ok",
        classification="timeout_budget_exceeded",
        detail=detail,
        query_preview=rendered_expr[:400],
        target_ref_id=spec.target_ref_id,
    )


def _missing_loki_query_result(spec: PanelAuditSpec) -> AuditResult:
    return AuditResult(
        dashboard_uid=spec.dashboard_uid,
        panel_id=spec.panel_id,
        title=spec.title,
        source_kind=spec.source_kind,
        semantic_kind=spec.semantic_kind,
        status="error" if spec.required else "ok",
        classification="missing_query",
        detail="Panel has no Loki expr target",
        query_preview="",
        target_ref_id=spec.target_ref_id,
    )


def _loki_query_request(
    *,
    target: dict[str, Any] | None,
    rendered_expr: str,
    config: AuditConfig,
) -> tuple[str, bool, str, str, str]:
    """Return (endpoint, instant, start_ns, end_ns, query_url)."""
    start_ns, end_ns = _loki_query_range_bounds(config)
    instant = target.get("instant") is True if target is not None else False
    endpoint = "query" if instant else "query_range"
    query_params = (
        {"query": rendered_expr, "time": end_ns}
        if instant
        else {
            "query": rendered_expr,
            "start": start_ns,
            "end": end_ns,
            "limit": "100",
        }
    )
    query_url = f"{config.loki_base_url}/loki/api/v1/{endpoint}?" + urlencode(
        query_params
    )
    return endpoint, instant, start_ns, end_ns, query_url


def _loki_fetch_failure_result(
    spec: PanelAuditSpec,
    config: AuditConfig,
    *,
    rendered_expr: str,
    started_at: float,
    exc: Exception,
) -> AuditResult:
    latency_seconds = monotonic() - started_at
    if latency_seconds >= config.request_timeout_seconds:
        return _loki_timeout_result(
            spec,
            config,
            rendered_expr=rendered_expr,
            phase="readiness/query",
            latency_seconds=latency_seconds,
            last_detail=f"{type(exc).__name__}: {exc}",
        )
    return AuditResult(
        dashboard_uid=spec.dashboard_uid,
        panel_id=spec.panel_id,
        title=spec.title,
        source_kind=spec.source_kind,
        semantic_kind=spec.semantic_kind,
        status="error" if spec.required else "ok",
        classification="blocked_unavailable",
        detail=f"Loki query could not be executed after readiness: {exc}",
        query_preview=rendered_expr[:400],
        target_ref_id=spec.target_ref_id,
    )


def _loki_success_result(
    spec: PanelAuditSpec,
    *,
    payload: object,
    rendered_expr: str,
    endpoint: str,
    bounded_range_hours: int,
    latency_seconds: float,
    instant: bool,
    start_ns: str,
    end_ns: str,
) -> AuditResult:
    classification, detail = _classify_loki_payload(payload)
    status = "error" if classification in {"invalid_shape", "query_error"} else "ok"
    time_detail = f"time={end_ns}" if instant else f"start={start_ns}; end={end_ns}"
    return AuditResult(
        dashboard_uid=spec.dashboard_uid,
        panel_id=spec.panel_id,
        title=spec.title,
        source_kind=spec.source_kind,
        semantic_kind=spec.semantic_kind,
        status=status,
        classification=classification,
        detail=(
            f"{detail}; endpoint={endpoint}; range_hours={bounded_range_hours}; "
            f"latency_seconds={latency_seconds:.3f}; {time_detail}"
        ),
        query_preview=rendered_expr[:400],
        target_ref_id=spec.target_ref_id,
    )


def _audit_loki_panel(
    spec: PanelAuditSpec,
    panel: dict[str, Any],
    config: AuditConfig,
) -> AuditResult:
    target = _select_target(panel, spec, field="expr")
    expr = str(target.get("expr") or "") if target is not None else ""
    if not expr:
        return _missing_loki_query_result(spec)
    bounded_range_hours = _bounded_loki_range_hours(config)
    rendered_expr = _substitute_dashboard_tokens(
        expr,
        config,
        range_hours=bounded_range_hours,
    )
    endpoint, instant, start_ns, end_ns, query_url = _loki_query_request(
        target=target,
        rendered_expr=rendered_expr,
        config=config,
    )
    started_at = monotonic()
    remaining_timeout, readiness_detail = _wait_for_loki_ready(
        config,
        started_at=started_at,
    )
    if remaining_timeout <= 0:
        return _loki_timeout_result(
            spec,
            config,
            rendered_expr=rendered_expr,
            phase="readiness polling",
            latency_seconds=monotonic() - started_at,
            last_detail=readiness_detail,
        )
    try:
        payload = _fetch_json(
            query_url,
            timeout_seconds=remaining_timeout,
        )
    except (HTTPError, URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        return _loki_fetch_failure_result(
            spec,
            config,
            rendered_expr=rendered_expr,
            started_at=started_at,
            exc=exc,
        )
    latency_seconds = monotonic() - started_at
    if latency_seconds > config.request_timeout_seconds:
        return _loki_timeout_result(
            spec,
            config,
            rendered_expr=rendered_expr,
            phase="readiness/query",
            latency_seconds=latency_seconds,
        )
    return _loki_success_result(
        spec,
        payload=payload,
        rendered_expr=rendered_expr,
        endpoint=endpoint,
        bounded_range_hours=bounded_range_hours,
        latency_seconds=latency_seconds,
        instant=instant,
        start_ns=start_ns,
        end_ns=end_ns,
    )


def _audit_tempo_handoff(spec: PanelAuditSpec, config: AuditConfig) -> AuditResult:
    search_url = f"{config.tempo_base_url}/api/search?" + urlencode({"limit": "1"})
    try:
        _fetch_text(
            f"{config.tempo_base_url}/ready",
            timeout_seconds=config.request_timeout_seconds,
        )
        payload = _fetch_json(
            search_url,
            timeout_seconds=config.request_timeout_seconds,
        )
    except (HTTPError, URLError, OSError, json.JSONDecodeError) as exc:
        return AuditResult(
            dashboard_uid=spec.dashboard_uid,
            panel_id=spec.panel_id,
            title=spec.title,
            source_kind=spec.source_kind,
            semantic_kind=spec.semantic_kind,
            status="error" if spec.required else "ok",
            classification="blocked_unavailable",
            detail=f"Tempo handoff could not be smoke-validated: {exc}",
            query_preview=search_url,
            target_ref_id=spec.target_ref_id,
        )
    classification, detail = _classify_tempo_search_payload(payload)
    status = "error" if classification in {"invalid_shape", "query_error"} else "ok"
    return AuditResult(
        dashboard_uid=spec.dashboard_uid,
        panel_id=spec.panel_id,
        title=spec.title,
        source_kind=spec.source_kind,
        semantic_kind=spec.semantic_kind,
        status=status,
        classification=classification,
        detail=detail,
        query_preview=search_url,
        target_ref_id=spec.target_ref_id,
    )


def _blocked_http_backend_result(
    spec: PanelAuditSpec,
    *,
    detail: str,
) -> AuditResult:
    return AuditResult(
        dashboard_uid=spec.dashboard_uid,
        panel_id=spec.panel_id,
        title=spec.title,
        source_kind=spec.source_kind,
        semantic_kind=spec.semantic_kind,
        status="error" if spec.required else "ok",
        classification="blocked_backend_unavailable",
        detail=detail,
        query_preview="",
        target_ref_id=spec.target_ref_id,
    )


def _resolve_or_block_app_base_url(
    config: AuditConfig,
    *,
    resolved_app_base_url: str | None,
    app_resolution_error: str | None,
) -> tuple[str | None, str | None]:
    """Resolve app base URL once; return (url, error) without retrying on failure."""
    if app_resolution_error is not None:
        return None, app_resolution_error
    if resolved_app_base_url is not None:
        return resolved_app_base_url, None
    try:
        return _resolve_app_base_url(config), None
    except (
        HTTPError,
        URLError,
        OSError,
        TimeoutError,
        json.JSONDecodeError,
    ) as exc:
        return None, (
            "Quarantine Explorer backend could not be resolved; "
            "all HTTP-backed panel checks are blocked instead of "
            f"being retried per panel: {exc}"
        )


def _audit_one_panel_spec(
    spec: PanelAuditSpec,
    panel: dict[str, Any],
    config: AuditConfig,
    *,
    resolved_app_base_url: str | None,
    app_resolution_error: str | None,
) -> tuple[AuditResult, str | None, str | None]:
    """Audit one panel; return (result, updated_url, updated_error)."""
    if spec.source_kind == "prometheus":
        return (
            _audit_prometheus_panel(spec, panel, config),
            resolved_app_base_url,
            app_resolution_error,
        )
    if spec.source_kind == "http":
        url, error = _resolve_or_block_app_base_url(
            config,
            resolved_app_base_url=resolved_app_base_url,
            app_resolution_error=app_resolution_error,
        )
        if error is not None:
            return (
                _blocked_http_backend_result(spec, detail=error),
                url,
                error,
            )
        assert url is not None
        return (
            _audit_http_panel(spec, panel, config, app_base_url=url),
            url,
            None,
        )
    if spec.source_kind == "loki":
        return (
            _audit_loki_panel(spec, panel, config),
            resolved_app_base_url,
            app_resolution_error,
        )
    return (
        _audit_tempo_handoff(spec, config),
        resolved_app_base_url,
        app_resolution_error,
    )


def _panel_audit_exception_result(
    spec: PanelAuditSpec,
    exc: Exception,
) -> AuditResult:
    return AuditResult(
        dashboard_uid=spec.dashboard_uid,
        panel_id=spec.panel_id,
        title=spec.title,
        source_kind=spec.source_kind,
        semantic_kind=spec.semantic_kind,
        status="error" if spec.required else "ok",
        classification="blocked_unavailable",
        detail=f"Panel audit target could not be executed: {exc}",
        query_preview="",
        target_ref_id=spec.target_ref_id,
    )


def _run_audit_with_provenance(
    config: AuditConfig,
) -> tuple[list[AuditResult], str | None]:
    results: list[AuditResult] = []
    resolved_app_base_url: str | None = None
    app_resolution_error: str | None = None
    for spec in effective_panel_specs():
        panel = _find_panel(spec)
        try:
            result, resolved_app_base_url, app_resolution_error = _audit_one_panel_spec(
                spec,
                panel,
                config,
                resolved_app_base_url=resolved_app_base_url,
                app_resolution_error=app_resolution_error,
            )
            results.append(result)
        except (
            HTTPError,
            URLError,
            OSError,
            TimeoutError,
            json.JSONDecodeError,
        ) as exc:
            results.append(_panel_audit_exception_result(spec, exc))
    return (results, resolved_app_base_url)


def run_audit(config: AuditConfig) -> list[AuditResult]:
    results, _ = _run_audit_with_provenance(config)
    return results


def _redact_url(url: str) -> str:
    parts = urlsplit(url)
    host = parts.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    netloc = host
    if parts.port is not None:
        netloc = f"{netloc}:{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def _read_prometheus_runtime_identity(config: AuditConfig) -> dict[str, object]:
    source_url = _redact_url(config.prometheus_base_url.rstrip("/"))
    try:
        payload = _fetch_json(
            f"{config.prometheus_base_url.rstrip('/')}/api/v1/status/runtimeinfo",
            timeout_seconds=config.request_timeout_seconds,
        )
    except (HTTPError, URLError, OSError, TimeoutError, json.JSONDecodeError) as exc:
        return {
            "source_url": source_url,
            "status": "unavailable",
            "error_type": type(exc).__name__,
        }
    if not isinstance(payload, dict) or payload.get("status") != "success":
        return {"source_url": source_url, "status": "invalid_shape"}
    data = payload.get("data")
    if not isinstance(data, dict):
        return {"source_url": source_url, "status": "invalid_shape"}
    return {
        "source_url": source_url,
        "status": "resolved",
        "start_time": data.get("startTime"),
        "reload_config_success": data.get("reloadConfigSuccess"),
        "last_config_time": data.get("lastConfigTime"),
    }


def _write_report(
    config: AuditConfig,
    results: list[AuditResult],
    *,
    resolved_backend_base_url: str | None = None,
    prometheus_runtime_identity: dict[str, object] | None = None,
) -> None:
    config.output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "occurrence_id": config.occurrence_id,
        "config": {
            "prometheus_base_url": _redact_url(config.prometheus_base_url),
            "app_base_url": _redact_url(config.app_base_url),
            "loki_base_url": _redact_url(config.loki_base_url),
            "tempo_base_url": _redact_url(config.tempo_base_url),
            "grafana_base_url": _redact_url(config.grafana_base_url),
            "workflow": config.workflow,
            "pipeline": config.pipeline,
            "run_type": config.run_type,
            "run_id": config.run_id,
            "range_hours": config.range_hours,
            "loki_range_hours": _bounded_loki_range_hours(config),
            "request_timeout_seconds": config.request_timeout_seconds,
        },
        "runtime_provenance": {
            "resolved_backend_base_url": (
                _redact_url(resolved_backend_base_url)
                if resolved_backend_base_url
                else None
            ),
            "prometheus": prometheus_runtime_identity
            or {
                "source_url": _redact_url(config.prometheus_base_url),
                "status": "not_collected",
            },
        },
        "panel_specs": [asdict(spec) for spec in effective_panel_specs()],
        "semantic_gate": semantic_gate_evidence(results),
        "results": [asdict(result) for result in results],
    }
    atomic_write_text(
        config.output_path,
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
    )


def main(argv: list[str] | None = None) -> int:
    config = _parse_args(argv)
    try:
        results, resolved_backend_base_url = _run_audit_with_provenance(config)
    except (FileNotFoundError, LookupError, OSError, json.JSONDecodeError) as exc:
        print(str(exc))
        return 1

    _write_report(
        config,
        results,
        resolved_backend_base_url=resolved_backend_base_url,
        prometheus_runtime_identity=_read_prometheus_runtime_identity(config),
    )
    for result in results:
        print(
            f"{result.dashboard_uid}#{result.panel_id} {result.title}: "
            f"{result.status}/{result.classification}"
        )
    return 0 if semantic_gate_evidence(results)["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
