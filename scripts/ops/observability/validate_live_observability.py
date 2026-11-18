#!/usr/bin/env python3
"""
Comprehensive live observability validation for BioETL.
Addresses OBS-003: Live Grafana/Prometheus Validation Gap
"""

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import base64

from dotenv import load_dotenv
import yaml

from scripts.engineering.qa.report_dashboard_inventory import (
    _normalize_dashboard_payload,
)

# Configuration
DEFAULT_PROMETHEUS_URL = "http://localhost:9090"
DEFAULT_GRAFANA_URL = "http://localhost:3000"
DEFAULT_GRAFANA_USERNAME = "admin"
# No committed Grafana password. Resolve from process env at parse time.
DEFAULT_GRAFANA_PASSWORD = ""
DEFAULT_OUTPUT_DIR = Path("reports/observability/live-validation")
DEFAULT_TIMEOUT = 5.0
EXPECTED_OPS_HTTP_DATASOURCE_UID = "bioetl-ops-http"
EXPECTED_OPS_HTTP_DATASOURCE_NAME = "BioETL Ops HTTP"
REPO_ROOT = Path(__file__).resolve().parents[3]
REPO_ENV_PATH = REPO_ROOT / ".env"
DASHBOARD_PROFILES = {
    "native": REPO_ROOT / "grafana/dashboards",
    "adaptive": REPO_ROOT / "grafana/dashboards-adaptive",
}


def _load_repo_environment() -> None:
    """Load the machine-local repository environment without overriding process env."""
    load_dotenv(dotenv_path=REPO_ENV_PATH, override=False)


def _env_first(*names: str, default: str = "") -> str:
    """Return the first non-empty process env value from *names*."""
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return default


def resolve_grafana_username() -> str:
    """Resolve Grafana username from runtime env, then the Grafana default user."""
    return _env_first(
        "GRAFANA_USERNAME",
        "GF_SECURITY_ADMIN_USER",
        default=DEFAULT_GRAFANA_USERNAME,
    )


def resolve_grafana_password() -> str:
    """Resolve Grafana password from runtime env only (no committed default)."""
    return _env_first(
        "GRAFANA_PASSWORD",
        "GF_SECURITY_ADMIN_PASSWORD",
        "GRAFANA_ADMIN_PASSWORD",
    )


EXPECTED_BIOETL_DASHBOARD_UIDS = frozenset(
    {
        "bioetl-control-plane-v1",
        "bioetl-dq-v2",
        "bioetl-incident-v1",
        "bioetl-overview-v2",
        "bioetl-run-explorer-v1",
    }
)


@dataclass
class ValidationResult:
    """Result of a single validation check."""

    check_name: str
    status: Literal["pass", "fail", "skip", "partial"]
    message: str
    details: dict[str, Any] | None = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(tz=UTC).isoformat()


@dataclass
class ValidationReport:
    """Complete validation report."""

    prometheus_url: str
    grafana_url: str
    timestamp: str
    results: list[ValidationResult]
    summary: dict[str, Any]


def _auth_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
    return f"Basic {token}"


def _fetch_json(url: str, timeout: float, headers: dict[str, str] | None = None) -> Any:
    """Fetch JSON from URL with optional headers."""
    from scripts.engineering.common.repo_paths import ensure_local_http_url

    safe_url = ensure_local_http_url(url)
    request = Request(safe_url, headers=headers or {})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def check_prometheus_health(prometheus_url: str, timeout: float) -> ValidationResult:
    """Check Prometheus health endpoint."""
    try:
        from scripts.engineering.common.repo_paths import ensure_local_http_url

        safe_base_url = ensure_local_http_url(prometheus_url)
        health_url = f"{safe_base_url}/-/healthy"
        response = urlopen(health_url, timeout=timeout)
        content = response.read().decode("utf-8").strip()

        if "Healthy" in content:
            return ValidationResult(
                check_name="prometheus_health",
                status="pass",
                message=f"Prometheus is healthy: {content}",
                details={"url": health_url, "response": content},
            )
        else:
            return ValidationResult(
                check_name="prometheus_health",
                status="fail",
                message=f"Prometheus health check returned unexpected: {content}",
                details={"url": health_url, "response": content},
            )
    except Exception as e:
        return ValidationResult(
            check_name="prometheus_health",
            status="fail",
            message=f"Prometheus health check failed: {e}",
            details={"url": f"{prometheus_url}/-/healthy", "error": str(e)},
        )


def check_prometheus_targets(prometheus_url: str, timeout: float) -> ValidationResult:
    """Require every configured scrape job and healthy active targets."""
    try:
        targets_url = f"{prometheus_url}/api/v1/targets"
        data = _fetch_json(targets_url, timeout)

        if data.get("status") != "success":
            return ValidationResult(
                check_name="prometheus_targets",
                status="fail",
                message="Prometheus targets API returned non-success status",
                details={"api_response": data},
            )

        active_targets = data.get("data", {}).get("activeTargets", [])
        if not isinstance(active_targets, list):
            raise ValueError("Prometheus activeTargets must be a list")
        config = yaml.safe_load(
            (REPO_ROOT / "grafana/prometheus.yml").read_text(encoding="utf-8")
        )
        expected_jobs = {item["job_name"] for item in config["scrape_configs"]}
        if not expected_jobs:
            raise ValueError("No expected Prometheus scrape jobs configured")
        active_jobs = {
            target.get("scrapePool") or target.get("labels", {}).get("job")
            for target in active_targets
        }
        missing_jobs = sorted(expected_jobs - active_jobs)
        up_count = sum(1 for t in active_targets if t.get("health") == "up")
        down_count = len(active_targets) - up_count

        down_targets = [
            {
                "job": t.get("labels", {}).get("job", "unknown"),
                "instance": t.get("labels", {}).get("instance", "unknown"),
                "last_error": t.get("lastError", "no error"),
                "health": t.get("health", "unknown"),
            }
            for t in active_targets
            if t.get("health") != "up"
        ]

        status: Literal["pass", "partial", "fail"] = "pass"
        if missing_jobs:
            status = "fail"
        elif down_count:
            status = "partial"
        return ValidationResult(
            check_name="prometheus_targets",
            status=status,
            message=(
                f"Prometheus targets: {up_count} up, {down_count} unhealthy, "
                f"{len(missing_jobs)} configured jobs missing"
            ),
            details={
                "total_targets": len(active_targets),
                "up_targets": up_count,
                "down_targets": down_count,
                "down_targets_details": down_targets,
                "expected_jobs": sorted(expected_jobs),
                "missing_jobs": missing_jobs,
            },
        )
    except Exception as e:
        return ValidationResult(
            check_name="prometheus_targets",
            status="fail",
            message=f"Prometheus targets check failed: {e}",
            details={"error": str(e)},
        )


def check_prometheus_rules_health(
    prometheus_url: str, timeout: float
) -> ValidationResult:
    """Fail when BioETL rules have lastError / evaluation failures (silent gaps)."""
    try:
        from scripts.ops.observability.check_prometheus_rules_health import (
            check_rules_health,
        )

        report = check_rules_health(
            prometheus_url=prometheus_url,
            timeout=timeout,
            fail_on_metric_signals=True,
            expr_parity=True,
            skip_if_unreachable=False,
        )
        details = {
            "bioetl_groups": report.bioetl_groups,
            "bioetl_rules": report.bioetl_rules,
            "evaluation_failures_10m": report.evaluation_failures_10m,
            "iterations_missed_10m": report.iterations_missed_10m,
            "issues": [
                {
                    "group": i.group,
                    "rule": i.rule,
                    "health": i.health,
                    "last_error": i.last_error,
                }
                for i in report.issues
            ],
            "query_errors": report.query_errors,
            "expr_parity_checked": report.expr_parity_checked,
            "expr_parity_skipped": report.expr_parity_skipped,
            "expr_parity_issues": report.expr_parity_issues,
            "tracked_rules_sha256": report.tracked_rules_sha256,
        }
        if (
            report.ok
            and report.bioetl_groups > 0
            and report.bioetl_rules > 0
            and report.expr_parity_checked
            and not report.expr_parity_skipped
            and not report.expr_parity_issues
            and not report.skipped_unreachable
        ):
            return ValidationResult(
                check_name="prometheus_rules_health",
                status="pass",
                message=(
                    f"BioETL rules healthy "
                    f"({report.bioetl_groups} groups, {report.bioetl_rules} rules; "
                    "six sentinel recording expressions match source)"
                ),
                details=details,
            )
        return ValidationResult(
            check_name="prometheus_rules_health",
            status="fail",
            message=(
                "BioETL rule coverage, health or sentinel expression parity failed"
            ),
            details=details,
        )
    except Exception as e:
        return ValidationResult(
            check_name="prometheus_rules_health",
            status="fail",
            message=f"Prometheus rules health check failed: {e}",
            details={"error": str(e)},
        )


def check_prometheus_metrics(prometheus_url: str, timeout: float) -> ValidationResult:
    """Require current BioETL samples, independently of retained metric names."""
    try:
        label_url = f"{prometheus_url}/api/v1/label/__name__/values"
        data = _fetch_json(label_url, timeout)

        if data.get("status") != "success":
            return ValidationResult(
                check_name="prometheus_metrics",
                status="fail",
                message="Prometheus label API returned non-success status",
                details={"api_response": data},
            )

        metric_names = data.get("data", [])
        if not isinstance(metric_names, list) or not all(
            isinstance(name, str) for name in metric_names
        ):
            raise ValueError("Prometheus metric names must be a list of strings")
        bioetl_metrics = [m for m in metric_names if m.startswith("bioetl_")]
        query = urlencode({"query": 'count({__name__=~"bioetl_.+"})'})
        current = _fetch_json(f"{prometheus_url}/api/v1/query?{query}", timeout)
        if current.get("status") != "success":
            raise ValueError("Prometheus current BioETL samples query failed")
        result = current.get("data", {})
        if result.get("resultType") != "vector":
            raise ValueError("Prometheus current BioETL samples must be a vector")
        samples = result.get("result", [])
        if not isinstance(samples, list) or len(samples) > 1:
            raise ValueError(
                "Prometheus BioETL count query must return at most one sample"
            )
        sample_count = float(samples[0]["value"][1]) if samples else 0.0
        if not math.isfinite(sample_count) or sample_count < 0:
            raise ValueError("Invalid current BioETL sample count")

        return ValidationResult(
            check_name="prometheus_metrics",
            status="pass" if sample_count > 0 else "fail",
            message=(
                f"Prometheus has {sample_count:g} current BioETL samples "
                f"({len(bioetl_metrics)} retained BioETL metric names)"
            ),
            details={
                "total_metrics": len(metric_names),
                "bioetl_metrics": len(bioetl_metrics),
                "current_bioetl_samples": sample_count,
                "sample_metrics": metric_names[:10] if metric_names else [],
            },
        )
    except Exception as e:
        return ValidationResult(
            check_name="prometheus_metrics",
            status="fail",
            message=f"Prometheus metrics check failed: {e}",
            details={"error": str(e)},
        )


def check_grafana_health(grafana_url: str, timeout: float) -> ValidationResult:
    """Check Grafana health endpoint."""
    try:
        health_url = f"{grafana_url}/api/health"
        data = _fetch_json(health_url, timeout)

        database = data.get("database", "unknown")
        version = data.get("version", "unknown")

        if database == "ok":
            return ValidationResult(
                check_name="grafana_health",
                status="pass",
                message=f"Grafana is healthy (version {version})",
                details={"version": version, "database": database},
            )
        else:
            return ValidationResult(
                check_name="grafana_health",
                status="fail",
                message=f"Grafana database status: {database}",
                details={"version": version, "database": database},
            )
    except Exception as e:
        return ValidationResult(
            check_name="grafana_health",
            status="fail",
            message=f"Grafana health check failed: {e}",
            details={"error": str(e)},
        )


def check_grafana_datasources(
    grafana_url: str, username: str, password: str, timeout: float
) -> ValidationResult:
    """Check Grafana datasources."""
    if not password.strip():
        return ValidationResult(
            check_name="grafana_datasources",
            status="fail",
            message=(
                "Grafana password is missing; set GRAFANA_PASSWORD "
                "(or GF_SECURITY_ADMIN_PASSWORD / GRAFANA_ADMIN_PASSWORD). "
                "No committed default password is used."
            ),
            details={"error": "missing_grafana_password"},
        )
    try:
        datasources_url = f"{grafana_url}/api/datasources"
        headers = {"Authorization": _auth_header(username, password)}
        data = _fetch_json(datasources_url, timeout, headers)

        if not isinstance(data, list):
            return ValidationResult(
                check_name="grafana_datasources",
                status="fail",
                message="Grafana datasources API did not return a list",
                details={"response_type": type(data).__name__},
            )

        datasource_names = [ds.get("name", "unknown") for ds in data]
        prometheus_ds = any("prometheus" in name.lower() for name in datasource_names)
        ops_http_ds = any(
            ds.get("uid") == EXPECTED_OPS_HTTP_DATASOURCE_UID
            and ds.get("name") == EXPECTED_OPS_HTTP_DATASOURCE_NAME
            and ds.get("type") == "yesoreyeram-infinity-datasource"
            for ds in data
        )
        ops_http_ready = False
        if ops_http_ds:
            ready = _fetch_json(
                f"{grafana_url}/api/datasources/proxy/uid/"
                f"{EXPECTED_OPS_HTTP_DATASOURCE_UID}/ops/control-plane/ready",
                timeout,
                headers,
            )
            source_id = ready.get("runtime_source_id", "")
            ops_http_ready = (
                isinstance(source_id, str)
                and len(source_id) == 64
                and all(character in "0123456789abcdef" for character in source_id)
                and all(
                    ready.get(port) is True
                    for port in (
                        "run_manifest_port",
                        "run_ledger_port",
                        "workflow_manifest_port",
                        "checkpoint_port",
                        "validation_evidence_service",
                    )
                )
            )
        if prometheus_ds and ops_http_ds:
            status: Literal["pass", "fail", "partial"] = (
                "pass" if ops_http_ready else "fail"
            )
        elif prometheus_ds:
            status = "partial"
        else:
            status = "fail"

        return ValidationResult(
            check_name="grafana_datasources",
            status=status,
            message=(
                f"Grafana has {len(datasource_names)} datasources, "
                f"Prometheus: {prometheus_ds}, Ops HTTP: {ops_http_ds}, "
                f"Ops backend ready: {ops_http_ready}"
            ),
            details={
                "total_datasources": len(datasource_names),
                "datasource_names": datasource_names,
                "has_prometheus": prometheus_ds,
                "has_ops_http": ops_http_ds,
                "ops_http_ready": ops_http_ready,
            },
        )
    except HTTPError as e:
        if e.code in (401, 403):
            return ValidationResult(
                check_name="grafana_datasources",
                status="fail",
                message=f"Grafana authentication failed (HTTP {e.code})",
                details={"error": str(e), "code": e.code},
            )
        return ValidationResult(
            check_name="grafana_datasources",
            status="fail",
            message=f"Grafana datasources check failed with HTTP {e.code}",
            details={"error": str(e), "code": e.code},
        )
    except Exception as e:
        return ValidationResult(
            check_name="grafana_datasources",
            status="fail",
            message=f"Grafana datasources check failed: {e}",
            details={"error": str(e)},
        )


def _grafana_dashboard_model_matches(
    dashboard_root: Path,
    uid: str,
    grafana_url: str,
    headers: dict[str, str],
    timeout: float,
) -> bool:
    """Compare one validated shipped model with its live Grafana payload."""
    source = json.loads((dashboard_root / f"{uid}.json").read_text(encoding="utf-8"))
    live = _fetch_json(f"{grafana_url}/api/dashboards/uid/{uid}", timeout, headers)
    if (
        not isinstance(source, dict)
        or source.get("uid") != uid
        or not isinstance(source.get("panels"), list)
        or not isinstance(live, dict)
        or not isinstance(live.get("dashboard"), dict)
        or live["dashboard"].get("uid") != uid
        or not isinstance(live["dashboard"].get("panels"), list)
    ):
        raise ValueError(f"Malformed dashboard model for {uid}")
    return _normalize_dashboard_payload(source) == _normalize_dashboard_payload(live)


def check_grafana_dashboards(
    grafana_url: str,
    username: str,
    password: str,
    timeout: float,
    *,
    dashboard_profile: str = "native",
) -> ValidationResult:
    """Compare deployed shipped models with an explicitly selected profile."""
    if not password.strip():
        return ValidationResult(
            check_name="grafana_dashboards",
            status="fail",
            message=(
                "Grafana password is missing; set GRAFANA_PASSWORD "
                "(or GF_SECURITY_ADMIN_PASSWORD / GRAFANA_ADMIN_PASSWORD). "
                "No committed default password is used."
            ),
            details={"error": "missing_grafana_password"},
        )
    try:
        dashboard_root = DASHBOARD_PROFILES[dashboard_profile]
        dashboards_url = f"{grafana_url}/api/search?query=&type=dash-db"
        headers = {"Authorization": _auth_header(username, password)}
        data = _fetch_json(dashboards_url, timeout, headers)

        if not isinstance(data, list):
            return ValidationResult(
                check_name="grafana_dashboards",
                status="fail",
                message="Grafana search API did not return a list",
                details={"response_type": type(data).__name__},
            )

        dashboard_uids = [str(ds.get("uid") or "unknown") for ds in data]
        bioetl_dashboards = [uid for uid in dashboard_uids if "bioetl" in uid.lower()]
        missing_bioetl_dashboard_uids = sorted(
            EXPECTED_BIOETL_DASHBOARD_UIDS.difference(dashboard_uids)
        )
        expected_count = len(EXPECTED_BIOETL_DASHBOARD_UIDS)
        mismatched_uids = []
        for uid in sorted(EXPECTED_BIOETL_DASHBOARD_UIDS):
            if uid in missing_bioetl_dashboard_uids:
                continue
            if not _grafana_dashboard_model_matches(
                dashboard_root, uid, grafana_url, headers, timeout
            ):
                mismatched_uids.append(uid)

        return ValidationResult(
            check_name="grafana_dashboards",
            status=(
                "fail" if missing_bioetl_dashboard_uids or mismatched_uids else "pass"
            ),
            message=(
                f"Grafana has {len(dashboard_uids)} dashboards, "
                f"{len(bioetl_dashboards)} BioETL dashboards "
                f"({expected_count} shipped UIDs expected; "
                f"{len(missing_bioetl_dashboard_uids)} missing; "
                f"{len(mismatched_uids)} models differ from {dashboard_profile})"
            ),
            details={
                "total_dashboards": len(dashboard_uids),
                "bioetl_dashboards": len(bioetl_dashboards),
                "dashboard_uids": dashboard_uids,
                "bioetl_dashboard_uids": bioetl_dashboards,
                "expected_bioetl_dashboards": expected_count,
                "expected_bioetl_dashboard_uids": sorted(
                    EXPECTED_BIOETL_DASHBOARD_UIDS
                ),
                "missing_bioetl_dashboard_uids": missing_bioetl_dashboard_uids,
                "dashboard_profile": dashboard_profile,
                "mismatched_dashboard_uids": mismatched_uids,
            },
        )
    except HTTPError as e:
        if e.code in (401, 403):
            return ValidationResult(
                check_name="grafana_dashboards",
                status="fail",
                message=f"Grafana authentication failed (HTTP {e.code})",
                details={"error": str(e), "code": e.code},
            )
        return ValidationResult(
            check_name="grafana_dashboards",
            status="fail",
            message=f"Grafana dashboards check failed with HTTP {e.code}",
            details={"error": str(e), "code": e.code},
        )
    except Exception as e:
        return ValidationResult(
            check_name="grafana_dashboards",
            status="fail",
            message=f"Grafana dashboards check failed: {e}",
            details={"error": str(e)},
        )


def check_prometheus_query(prometheus_url: str, timeout: float) -> ValidationResult:
    """Test basic Prometheus query."""
    try:
        query_url = f"{prometheus_url}/api/v1/query?query=up"
        data = _fetch_json(query_url, timeout)

        if data.get("status") != "success":
            return ValidationResult(
                check_name="prometheus_query",
                status="fail",
                message="Prometheus query API returned non-success status",
                details={"api_response": data},
            )

        result_type = data.get("data", {}).get("resultType", "unknown")
        results = data.get("data", {}).get("result", [])

        return ValidationResult(
            check_name="prometheus_query",
            status="pass",
            message=f"Prometheus query executed successfully (resultType: {result_type}, {len(results)} results)",
            details={
                "result_type": result_type,
                "result_count": len(results),
                "sample_results": results[:3],
            },
        )
    except Exception as e:
        return ValidationResult(
            check_name="prometheus_query",
            status="fail",
            message=f"Prometheus query test failed: {e}",
            details={"error": str(e)},
        )


def run_validation(
    prometheus_url: str,
    grafana_url: str,
    grafana_username: str,
    grafana_password: str,
    timeout: float,
    *,
    dashboard_profile: str = "native",
) -> ValidationReport:
    """Run complete observability validation."""
    results = []

    # Prometheus checks
    results.append(check_prometheus_health(prometheus_url, timeout))
    results.append(check_prometheus_targets(prometheus_url, timeout))
    results.append(check_prometheus_metrics(prometheus_url, timeout))
    results.append(check_prometheus_query(prometheus_url, timeout))
    results.append(check_prometheus_rules_health(prometheus_url, timeout))

    # Grafana checks
    results.append(check_grafana_health(grafana_url, timeout))
    results.append(
        check_grafana_datasources(
            grafana_url, grafana_username, grafana_password, timeout
        )
    )
    results.append(
        check_grafana_dashboards(
            grafana_url,
            grafana_username,
            grafana_password,
            timeout,
            dashboard_profile=dashboard_profile,
        )
    )

    # Calculate summary
    passed = sum(1 for r in results if r.status == "pass")
    failed = sum(1 for r in results if r.status == "fail")
    partial = sum(1 for r in results if r.status == "partial")
    total = len(results)

    summary = {
        "total_checks": total,
        "passed": passed,
        "failed": failed,
        "partial": partial,
        "success_rate": f"{(passed / total * 100):.1f}%" if total > 0 else "0%",
    }

    return ValidationReport(
        prometheus_url=prometheus_url,
        grafana_url=grafana_url,
        timestamp=datetime.now(tz=UTC).isoformat(),
        results=results,
        summary=summary,
    )


def main():
    _load_repo_environment()
    parser = argparse.ArgumentParser(
        description="Validate live BioETL observability stack (OBS-003)"
    )
    parser.add_argument(
        "--prometheus-url", default=DEFAULT_PROMETHEUS_URL, help="Prometheus base URL"
    )
    parser.add_argument(
        "--grafana-url", default=DEFAULT_GRAFANA_URL, help="Grafana base URL"
    )
    parser.add_argument(
        "--grafana-username",
        default=resolve_grafana_username(),
        help="Grafana username (default: GRAFANA_USERNAME / GF_SECURITY_ADMIN_USER)",
    )
    parser.add_argument(
        "--grafana-password",
        default=resolve_grafana_password(),
        help=(
            "Grafana password (default: GRAFANA_PASSWORD / "
            "GF_SECURITY_ADMIN_PASSWORD / GRAFANA_ADMIN_PASSWORD). "
            "No committed default password is used."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="Request timeout in seconds",
    )
    parser.add_argument(
        "--dashboard-profile",
        choices=tuple(DASHBOARD_PROFILES),
        default="native",
        help="Explicit source profile for deployed dashboard model parity",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory for validation report",
    )

    args = parser.parse_args()

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Run validation
    print("Starting observability validation...")
    print(f"Prometheus: {args.prometheus_url}")
    print(f"Grafana: {args.grafana_url}")
    print()

    report = run_validation(
        prometheus_url=args.prometheus_url,
        grafana_url=args.grafana_url,
        grafana_username=args.grafana_username,
        grafana_password=args.grafana_password,
        timeout=args.timeout,
        dashboard_profile=args.dashboard_profile,
    )

    # Print results
    print("Validation Results:")
    print("=" * 60)
    for result in report.results:
        if result.status == "pass":
            status_symbol = "[PASS]"
        elif result.status == "partial":
            status_symbol = "[PARTIAL]"
        else:
            status_symbol = "[FAIL]"
        print(f"{status_symbol} {result.check_name}: {result.status}")
        print(f"  {result.message}")
        if result.details:
            print(f"  Details: {json.dumps(result.details, indent=2)[:200]}...")
        print()

    print("Summary:")
    print("=" * 60)
    for key, value in report.summary.items():
        print(f"  {key}: {value}")

    # Save report
    report_path = (
        args.output_dir
        / f"validation-report-{datetime.now(tz=UTC).strftime('%Y%m%d-%H%M%S')}.json"
    )
    with open(report_path, "w") as f:
        json.dump(asdict(report), f, indent=2, default=str)

    print(f"\nReport saved to: {report_path}")

    # Exit with appropriate code
    if report.summary["failed"] > 0:
        sys.exit(1)
    elif report.summary["partial"] > 0:
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
