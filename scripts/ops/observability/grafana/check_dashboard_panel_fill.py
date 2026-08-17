#!/usr/bin/env python3
"""Fail closed when a shipped Grafana panel fill returns a transport/query error.

Empty / No data / UNKNOWN is not an error. HTTP 502/503/504/505, Gateway
Timeout, query error, and datasource/plugin failures are.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bioetl.infrastructure.storage.support.atomic_ops import atomic_write_text
from scripts.ops.observability.grafana import audit_live_grafana_panels as live_audit

DEFAULT_OUTPUT_PATH = Path("reports/observability/grafana/panel-fill-errors.json")
DEFAULT_REQUEST_TIMEOUT_SECONDS = 15.0
_DASHBOARD_DIR = Path("grafana/dashboards")
_SKIP_PANEL_TYPES = frozenset({"row", "text"})
_GATEWAY_STATUS_CODES = frozenset({502, 503, 504, 505})
_PROMETHEUS_DATASOURCE = {"type": "prometheus", "uid": "prometheus"}
_HTTP_DATASOURCE = {
    "type": "yesoreyeram-infinity-datasource",
    "uid": "bioetl-ops-http",
}
_ERROR_NEEDLES = (
    "gateway timeout",
    "bad gateway",
    "service unavailable",
    "http version not supported",
    "query error",
    "plugin error",
    "datasource not found",
    "context deadline exceeded",
    "i/o timeout",
    "client.timeout",
    "connection refused",
    "connection reset",
    "no such host",
    "network is unreachable",
    "temporarily unavailable",
    "upstream request timeout",
    "failed to get data from url",
    "error querying",
)


@dataclass(frozen=True)
class FillConfig:
    grafana_base_url: str
    grafana_username: str
    grafana_password: str
    pipeline: str
    run_type: str
    run_id: str
    workflow: str
    range_hours: int
    request_timeout_seconds: float
    output_path: Path | None


@dataclass(frozen=True)
class FillVerdict:
    kind: Literal["ok", "fill_error", "skipped"]
    reason: str
    http_status: int | None = None


@dataclass(frozen=True)
class PanelFillResult:
    dashboard_uid: str
    dashboard_file: str
    panel_id: int
    title: str
    panel_type: str
    verdict: FillVerdict


def classify_fill_error(
    *,
    http_status: int | None,
    body: object = None,
    transport_error: str | None = None,
) -> FillVerdict:
    """Classify one panel-fill attempt. Valid empty is ``ok``."""
    if transport_error:
        return FillVerdict(
            kind="fill_error",
            reason=f"transport: {transport_error}",
            http_status=http_status,
        )
    if http_status in _GATEWAY_STATUS_CODES:
        return FillVerdict(
            kind="fill_error",
            reason=_status_reason(http_status, body),
            http_status=http_status,
        )
    if http_status is not None and http_status >= 500:
        return FillVerdict(
            kind="fill_error",
            reason=_status_reason(http_status, body),
            http_status=http_status,
        )
    texts = _collect_error_texts(body)
    for text in texts:
        lowered = text.lower()
        for needle in _ERROR_NEEDLES:
            if needle in lowered:
                return FillVerdict(
                    kind="fill_error",
                    reason=text.strip()[:400],
                    http_status=http_status,
                )
        if _looks_like_http_gateway_status(lowered):
            return FillVerdict(
                kind="fill_error",
                reason=text.strip()[:400],
                http_status=http_status,
            )
    return FillVerdict(kind="ok", reason="panel fill returned no transport/query error")


def iter_queryable_panels(
    dashboard_dir: Path = _DASHBOARD_DIR,
) -> tuple[dict[str, Any], ...]:
    """Yield shipped data-bearing panels that Grafana will query on fill."""
    items: list[dict[str, Any]] = []
    for path in sorted(dashboard_dir.glob("*.json")):
        dashboard = json.loads(path.read_text(encoding="utf-8"))
        uid = str(dashboard.get("uid") or path.stem)
        for panel in live_audit._iter_panels(list(dashboard.get("panels") or [])):
            if not _is_queryable_panel(panel):
                continue
            items.append(
                {
                    "dashboard_uid": uid,
                    "dashboard_file": path.name,
                    "panel": panel,
                }
            )
    return tuple(items)


def build_ds_query_payload(
    panel: dict[str, Any],
    *,
    config: FillConfig,
) -> dict[str, Any]:
    """Build a Grafana ``POST /api/ds/query`` body for one panel."""
    audit_config = _to_audit_config(config)
    end = datetime.now(UTC)
    start = end - timedelta(hours=max(config.range_hours, 1))
    queries: list[dict[str, Any]] = []
    for index, target in enumerate(panel.get("targets") or []):
        if not isinstance(target, dict) or target.get("hide") is True:
            continue
        query = _render_target(target, audit_config=audit_config)
        if not _target_has_live_query(query):
            continue
        query["datasource"] = _normalize_datasource(panel, target)
        query.setdefault("refId", chr(ord("A") + index))
        queries.append(query)
    return {
        "from": str(int(start.timestamp() * 1000)),
        "to": str(int(end.timestamp() * 1000)),
        "queries": queries,
    }


def query_panel_fill(
    panel: dict[str, Any],
    *,
    config: FillConfig,
) -> FillVerdict:
    payload = build_ds_query_payload(panel, config=config)
    if not payload["queries"]:
        return FillVerdict(kind="skipped", reason="no live query targets")
    url = f"{config.grafana_base_url.rstrip('/')}/api/ds/query"
    try:
        status, body = _post_json(
            url,
            payload,
            auth_header=live_audit._auth_header(
                config.grafana_username, config.grafana_password
            ),
            timeout_seconds=config.request_timeout_seconds,
        )
    except TimeoutError as exc:
        return classify_fill_error(
            http_status=None,
            transport_error=f"client timeout: {exc}",
        )
    except URLError as exc:
        return classify_fill_error(
            http_status=None,
            transport_error=str(exc.reason if getattr(exc, "reason", None) else exc),
        )
    except OSError as exc:
        return classify_fill_error(http_status=None, transport_error=str(exc))
    return classify_fill_error(http_status=status, body=body)


def run_panel_fill_check(config: FillConfig) -> list[PanelFillResult]:
    results: list[PanelFillResult] = []
    for item in iter_queryable_panels():
        panel = item["panel"]
        verdict = query_panel_fill(panel, config=config)
        results.append(
            PanelFillResult(
                dashboard_uid=str(item["dashboard_uid"]),
                dashboard_file=str(item["dashboard_file"]),
                panel_id=int(panel.get("id") or 0),
                title=str(panel.get("title") or f"panel-{panel.get('id')}"),
                panel_type=str(panel.get("type") or ""),
                verdict=verdict,
            )
        )
    return results


def grafana_is_reachable(config: FillConfig) -> bool:
    url = f"{config.grafana_base_url.rstrip('/')}/api/health"
    try:
        with urlopen(url, timeout=min(config.request_timeout_seconds, 3.0)) as response:
            return int(response.status) == 200
    except (HTTPError, URLError, OSError, TimeoutError):
        return False


def _is_queryable_panel(panel: dict[str, Any]) -> bool:
    if not isinstance(panel, dict):
        return False
    if panel.get("type") in _SKIP_PANEL_TYPES:
        return False
    if not isinstance(panel.get("id"), int):
        return False
    return any(
        isinstance(target, dict)
        and target.get("hide") is not True
        and _target_has_live_query(target)
        for target in panel.get("targets") or []
    )


def _target_has_live_query(target: dict[str, Any]) -> bool:
    expr = target.get("expr")
    if isinstance(expr, str) and expr.strip():
        return True
    url = target.get("url")
    return isinstance(url, str) and bool(url.strip())


def _normalize_datasource(
    panel: dict[str, Any], target: dict[str, Any]
) -> dict[str, str]:
    raw = target.get("datasource")
    if raw in (None, "", {}):
        raw = panel.get("datasource")
    if isinstance(raw, dict):
        uid = str(raw.get("uid") or "").strip()
        typ = str(raw.get("type") or "").strip()
        if uid == "bioetl-ops-http" or "infinity" in typ.lower():
            return dict(_HTTP_DATASOURCE)
        if uid == "prometheus" or typ == "prometheus":
            return dict(_PROMETHEUS_DATASOURCE)
        if uid:
            return {"type": typ or "prometheus", "uid": uid}
        raw = typ
    text = str(raw or "").strip().lower()
    if "ops" in text or "http" in text or "infinity" in text:
        return dict(_HTTP_DATASOURCE)
    return dict(_PROMETHEUS_DATASOURCE)


def _render_target(
    target: dict[str, Any], *, audit_config: live_audit.AuditConfig
) -> dict[str, Any]:
    rendered = dict(target)
    for field in ("expr", "url"):
        value = rendered.get(field)
        if isinstance(value, str) and value:
            rendered[field] = live_audit._substitute_dashboard_tokens(
                value, audit_config
            )
    return rendered


def _to_audit_config(config: FillConfig) -> live_audit.AuditConfig:
    return live_audit.AuditConfig(
        prometheus_base_url=live_audit.DEFAULT_PROMETHEUS_BASE_URL,
        app_base_url=live_audit.DEFAULT_APP_BASE_URL,
        loki_base_url=live_audit.DEFAULT_LOKI_BASE_URL,
        tempo_base_url=live_audit.DEFAULT_TEMPO_BASE_URL,
        grafana_base_url=config.grafana_base_url,
        grafana_username=config.grafana_username,
        grafana_password=config.grafana_password,
        workflow=config.workflow,
        pipeline=config.pipeline,
        run_type=config.run_type,
        run_id=config.run_id,
        range_hours=config.range_hours,
        output_path=config.output_path or DEFAULT_OUTPUT_PATH,
        request_timeout_seconds=config.request_timeout_seconds,
    )


def _status_reason(http_status: int | None, body: object) -> str:
    texts = _collect_error_texts(body)
    suffix = f": {texts[0][:300]}" if texts else ""
    return f"HTTP {http_status}{suffix}"


def _looks_like_http_gateway_status(text: str) -> bool:
    for code in _GATEWAY_STATUS_CODES:
        token = str(code)
        if text == token or text.startswith(f"{token} ") or f" {token} " in f" {text} ":
            return True
    return False


def _collect_error_texts(body: object) -> list[str]:
    texts: list[str] = []
    if isinstance(body, str):
        stripped = body.strip()
        if stripped:
            texts.append(stripped[:2000])
        return texts
    if not isinstance(body, dict):
        return texts
    for key in ("message", "error", "errorSource"):
        value = body.get(key)
        if isinstance(value, str) and value.strip():
            texts.append(value.strip())
    results = body.get("results")
    if isinstance(results, dict):
        for result in results.values():
            texts.extend(_collect_result_error_texts(result))
    return texts


def _collect_result_error_texts(result: object) -> list[str]:
    if not isinstance(result, dict):
        return []
    texts: list[str] = []
    for key in ("error", "message", "errorSource"):
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            texts.append(value.strip())
    status = result.get("status")
    if isinstance(status, int) and status >= 400:
        texts.append(f"status {status}")
    frames = result.get("frames")
    if not isinstance(frames, list):
        return texts
    for frame in frames:
        if not isinstance(frame, dict):
            continue
        meta = frame.get("meta")
        if not isinstance(meta, dict):
            continue
        notices = meta.get("notices")
        if not isinstance(notices, list):
            continue
        for notice in notices:
            if not isinstance(notice, dict):
                continue
            severity = str(notice.get("severity") or "").lower()
            text = notice.get("text")
            if severity == "error" and isinstance(text, str) and text.strip():
                texts.append(text.strip())
    return texts


def _post_json(
    url: str,
    payload: dict[str, Any],
    *,
    auth_header: str,
    timeout_seconds: float,
) -> tuple[int, object]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Accept": "application/json",
            "Authorization": auth_header,
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
            status = int(response.status)
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        status = int(exc.code)
    if not raw.strip():
        return status, None
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, raw


def _parse_args(argv: list[str] | None) -> FillConfig:
    parser = argparse.ArgumentParser(
        description=(
            "Query every shipped Grafana data panel through /api/ds/query and "
            "fail if any fill returns a gateway/query error."
        )
    )
    parser.add_argument(
        "--grafana-base-url",
        default=live_audit._read_env(
            "GRAFANA_BASE_URL",
            live_audit._read_env("GRAFANA_URL", live_audit.DEFAULT_GRAFANA_BASE_URL),
        ),
    )
    parser.add_argument(
        "--grafana-username",
        default=live_audit._read_env(
            "GRAFANA_USERNAME", live_audit.DEFAULT_GRAFANA_USERNAME
        ),
    )
    parser.add_argument(
        "--grafana-password",
        default=live_audit._read_env(
            "GRAFANA_PASSWORD", live_audit.DEFAULT_GRAFANA_PASSWORD
        ),
    )
    parser.add_argument("--workflow", default=live_audit.DEFAULT_WORKFLOW)
    parser.add_argument("--pipeline", default=live_audit.DEFAULT_PIPELINE)
    parser.add_argument("--run-type", default=live_audit.DEFAULT_RUN_TYPE)
    parser.add_argument("--run-id", default=live_audit.DEFAULT_RUN_ID)
    parser.add_argument("--range-hours", type=int, default=live_audit.DEFAULT_RANGE_HOURS)
    parser.add_argument(
        "--request-timeout-seconds",
        type=float,
        default=DEFAULT_REQUEST_TIMEOUT_SECONDS,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument(
        "--no-output",
        action="store_true",
        help="Do not write the JSON report.",
    )
    args = parser.parse_args(argv)
    return FillConfig(
        grafana_base_url=str(args.grafana_base_url).rstrip("/"),
        grafana_username=str(args.grafana_username),
        grafana_password=str(args.grafana_password),
        pipeline=str(args.pipeline),
        run_type=str(args.run_type),
        run_id=str(args.run_id),
        workflow=str(args.workflow),
        range_hours=max(int(args.range_hours), 1),
        request_timeout_seconds=max(float(args.request_timeout_seconds), 0.1),
        output_path=None if args.no_output else args.output,
    )


def _report_payload(results: list[PanelFillResult]) -> dict[str, Any]:
    errors = [result for result in results if result.verdict.kind == "fill_error"]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "panel_count": len(results),
        "error_count": len(errors),
        "ok_count": sum(1 for result in results if result.verdict.kind == "ok"),
        "skipped_count": sum(
            1 for result in results if result.verdict.kind == "skipped"
        ),
        "errors": [
            {
                "dashboard_uid": result.dashboard_uid,
                "dashboard_file": result.dashboard_file,
                "panel_id": result.panel_id,
                "title": result.title,
                "http_status": result.verdict.http_status,
                "reason": result.verdict.reason,
            }
            for result in errors
        ],
        "results": [
            {
                "dashboard_uid": result.dashboard_uid,
                "dashboard_file": result.dashboard_file,
                "panel_id": result.panel_id,
                "title": result.title,
                "panel_type": result.panel_type,
                "verdict": asdict(result.verdict),
            }
            for result in results
        ],
    }


def main(argv: list[str] | None = None) -> int:
    config = _parse_args(argv)
    if not grafana_is_reachable(config):
        print(
            f"Grafana is not reachable at {config.grafana_base_url}/api/health",
            file=sys.stderr,
        )
        return 2
    results = run_panel_fill_check(config)
    payload = _report_payload(results)
    if config.output_path is not None:
        config.output_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(
            config.output_path,
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        )
    errors = payload["errors"]
    print(
        f"panel fill: {payload['ok_count']} ok, "
        f"{payload['skipped_count']} skipped, "
        f"{payload['error_count']} errors "
        f"(of {payload['panel_count']} queryable panels)"
    )
    for error in errors:
        print(
            f"FILL_ERROR {error['dashboard_uid']}#{error['panel_id']} "
            f"{error['title']}: {error['reason']}",
            file=sys.stderr,
        )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
