#!/usr/bin/env python3
"""
Comprehensive live observability validation for BioETL.
Addresses OBS-003: Live Grafana/Prometheus Validation Gap
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import base64

# Configuration
DEFAULT_PROMETHEUS_URL = "http://localhost:9090"
DEFAULT_GRAFANA_URL = "http://localhost:3000"
DEFAULT_GRAFANA_USERNAME = "admin"
DEFAULT_GRAFANA_PASSWORD = "changeme"
DEFAULT_OUTPUT_DIR = Path("reports/observability/live-validation")
DEFAULT_TIMEOUT = 5.0

@dataclass
class ValidationResult:
    """Result of a single validation check."""
    check_name: str
    status: Literal["pass", "fail", "skip"]
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

def _fetch_json(url: str, timeout: float, headers: dict[str, str] | None = None) -> dict[str, Any]:
    """Fetch JSON from URL with optional headers."""
    request = Request(url, headers=headers or {})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))

def check_prometheus_health(prometheus_url: str, timeout: float) -> ValidationResult:
    """Check Prometheus health endpoint."""
    try:
        health_url = f"{prometheus_url}/-/healthy"
        response = urlopen(health_url, timeout=timeout)
        content = response.read().decode("utf-8").strip()

        if "Healthy" in content:
            return ValidationResult(
                check_name="prometheus_health",
                status="pass",
                message=f"Prometheus is healthy: {content}",
                details={"url": health_url, "response": content}
            )
        else:
            return ValidationResult(
                check_name="prometheus_health",
                status="fail",
                message=f"Prometheus health check returned unexpected: {content}",
                details={"url": health_url, "response": content}
            )
    except Exception as e:
        return ValidationResult(
            check_name="prometheus_health",
            status="fail",
            message=f"Prometheus health check failed: {e}",
            details={"url": f"{prometheus_url}/-/healthy", "error": str(e)}
        )

def check_prometheus_targets(prometheus_url: str, timeout: float) -> ValidationResult:
    """Check Prometheus targets status."""
    try:
        targets_url = f"{prometheus_url}/api/v1/targets"
        data = _fetch_json(targets_url, timeout)

        if data.get("status") != "success":
            return ValidationResult(
                check_name="prometheus_targets",
                status="fail",
                message="Prometheus targets API returned non-success status",
                details={"api_response": data}
            )

        active_targets = data.get("data", {}).get("activeTargets", [])
        up_count = sum(1 for t in active_targets if t.get("health") == "up")
        down_count = sum(1 for t in active_targets if t.get("health") == "down")

        down_targets = [
            {
                "job": t.get("labels", {}).get("job", "unknown"),
                "instance": t.get("labels", {}).get("instance", "unknown"),
                "last_error": t.get("lastError", "no error")
            }
            for t in active_targets if t.get("health") == "down"
        ]

        return ValidationResult(
            check_name="prometheus_targets",
            status="pass" if down_count == 0 else "partial",
            message=f"Prometheus targets: {up_count} up, {down_count} down",
            details={
                "total_targets": len(active_targets),
                "up_targets": up_count,
                "down_targets": down_count,
                "down_targets_details": down_targets
            }
        )
    except Exception as e:
        return ValidationResult(
            check_name="prometheus_targets",
            status="fail",
            message=f"Prometheus targets check failed: {e}",
            details={"error": str(e)}
        )

def check_prometheus_metrics(prometheus_url: str, timeout: float) -> ValidationResult:
    """Check if Prometheus has any metrics."""
    try:
        label_url = f"{prometheus_url}/api/v1/label/__name__/values"
        data = _fetch_json(label_url, timeout)

        if data.get("status") != "success":
            return ValidationResult(
                check_name="prometheus_metrics",
                status="fail",
                message="Prometheus label API returned non-success status",
                details={"api_response": data}
            )

        metric_names = data.get("data", [])
        bioetl_metrics = [m for m in metric_names if "bioetl" in m.lower()]

        return ValidationResult(
            check_name="prometheus_metrics",
            status="pass" if len(metric_names) > 0 else "fail",
            message=f"Prometheus has {len(metric_names)} total metrics, {len(bioetl_metrics)} BioETL metrics",
            details={
                "total_metrics": len(metric_names),
                "bioetl_metrics": len(bioetl_metrics),
                "sample_metrics": metric_names[:10] if metric_names else []
            }
        )
    except Exception as e:
        return ValidationResult(
            check_name="prometheus_metrics",
            status="fail",
            message=f"Prometheus metrics check failed: {e}",
            details={"error": str(e)}
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
                details={"version": version, "database": database}
            )
        else:
            return ValidationResult(
                check_name="grafana_health",
                status="fail",
                message=f"Grafana database status: {database}",
                details={"version": version, "database": database}
            )
    except Exception as e:
        return ValidationResult(
            check_name="grafana_health",
            status="fail",
            message=f"Grafana health check failed: {e}",
            details={"error": str(e)}
        )

def check_grafana_datasources(grafana_url: str, username: str, password: str, timeout: float) -> ValidationResult:
    """Check Grafana datasources."""
    try:
        datasources_url = f"{grafana_url}/api/datasources"
        headers = {"Authorization": _auth_header(username, password)}
        data = _fetch_json(datasources_url, timeout, headers)

        if not isinstance(data, list):
            return ValidationResult(
                check_name="grafana_datasources",
                status="fail",
                message="Grafana datasources API did not return a list",
                details={"response_type": type(data).__name__}
            )

        datasource_names = [ds.get("name", "unknown") for ds in data]
        prometheus_ds = any("prometheus" in name.lower() for name in datasource_names)

        return ValidationResult(
            check_name="grafana_datasources",
            status="pass" if prometheus_ds else "fail",
            message=f"Grafana has {len(datasource_names)} datasources, Prometheus: {prometheus_ds}",
            details={
                "total_datasources": len(datasource_names),
                "datasource_names": datasource_names,
                "has_prometheus": prometheus_ds
            }
        )
    except HTTPError as e:
        if e.code in (401, 403):
            return ValidationResult(
                check_name="grafana_datasources",
                status="fail",
                message=f"Grafana authentication failed (HTTP {e.code})",
                details={"error": str(e), "code": e.code}
            )
        return ValidationResult(
            check_name="grafana_datasources",
            status="fail",
            message=f"Grafana datasources check failed with HTTP {e.code}",
            details={"error": str(e), "code": e.code}
        )
    except Exception as e:
        return ValidationResult(
            check_name="grafana_datasources",
            status="fail",
            message=f"Grafana datasources check failed: {e}",
            details={"error": str(e)}
        )

def check_grafana_dashboards(grafana_url: str, username: str, password: str, timeout: float) -> ValidationResult:
    """Check Grafana dashboards."""
    try:
        dashboards_url = f"{grafana_url}/api/search?query=&type=dash-db"
        headers = {"Authorization": _auth_header(username, password)}
        data = _fetch_json(dashboards_url, timeout, headers)

        if not isinstance(data, list):
            return ValidationResult(
                check_name="grafana_dashboards",
                status="fail",
                message="Grafana search API did not return a list",
                details={"response_type": type(data).__name__}
            )

        dashboard_uids = [ds.get("uid", "unknown") for ds in data]
        bioetl_dashboards = [uid for uid in dashboard_uids if "bioetl" in uid.lower()]

        return ValidationResult(
            check_name="grafana_dashboards",
            status="pass" if len(bioetl_dashboards) >= 8 else "partial",
            message=f"Grafana has {len(dashboard_uids)} dashboards, {len(bioetl_dashboards)} BioETL dashboards (expected 8)",
            details={
                "total_dashboards": len(dashboard_uids),
                "bioetl_dashboards": len(bioetl_dashboards),
                "dashboard_uids": dashboard_uids,
                "bioetl_dashboard_uids": bioetl_dashboards
            }
        )
    except HTTPError as e:
        if e.code in (401, 403):
            return ValidationResult(
                check_name="grafana_dashboards",
                status="fail",
                message=f"Grafana authentication failed (HTTP {e.code})",
                details={"error": str(e), "code": e.code}
            )
        return ValidationResult(
            check_name="grafana_dashboards",
            status="fail",
            message=f"Grafana dashboards check failed with HTTP {e.code}",
            details={"error": str(e), "code": e.code}
        )
    except Exception as e:
        return ValidationResult(
            check_name="grafana_dashboards",
            status="fail",
            message=f"Grafana dashboards check failed: {e}",
            details={"error": str(e)}
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
                details={"api_response": data}
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
                "sample_results": results[:3]
            }
        )
    except Exception as e:
        return ValidationResult(
            check_name="prometheus_query",
            status="fail",
            message=f"Prometheus query test failed: {e}",
            details={"error": str(e)}
        )

def run_validation(
    prometheus_url: str,
    grafana_url: str,
    grafana_username: str,
    grafana_password: str,
    timeout: float
) -> ValidationReport:
    """Run complete observability validation."""
    results = []

    # Prometheus checks
    results.append(check_prometheus_health(prometheus_url, timeout))
    results.append(check_prometheus_targets(prometheus_url, timeout))
    results.append(check_prometheus_metrics(prometheus_url, timeout))
    results.append(check_prometheus_query(prometheus_url, timeout))

    # Grafana checks
    results.append(check_grafana_health(grafana_url, timeout))
    results.append(check_grafana_datasources(grafana_url, grafana_username, grafana_password, timeout))
    results.append(check_grafana_dashboards(grafana_url, grafana_username, grafana_password, timeout))

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
        "success_rate": f"{(passed / total * 100):.1f}%" if total > 0 else "0%"
    }

    return ValidationReport(
        prometheus_url=prometheus_url,
        grafana_url=grafana_url,
        timestamp=datetime.now(tz=UTC).isoformat(),
        results=results,
        summary=summary
    )

def main():
    parser = argparse.ArgumentParser(
        description="Validate live BioETL observability stack (OBS-003)"
    )
    parser.add_argument(
        "--prometheus-url",
        default=DEFAULT_PROMETHEUS_URL,
        help="Prometheus base URL"
    )
    parser.add_argument(
        "--grafana-url",
        default=DEFAULT_GRAFANA_URL,
        help="Grafana base URL"
    )
    parser.add_argument(
        "--grafana-username",
        default=DEFAULT_GRAFANA_USERNAME,
        help="Grafana username"
    )
    parser.add_argument(
        "--grafana-password",
        default=DEFAULT_GRAFANA_PASSWORD,
        help="Grafana password"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="Request timeout in seconds"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory for validation report"
    )

    args = parser.parse_args()

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Run validation
    print(f"Starting observability validation...")
    print(f"Prometheus: {args.prometheus_url}")
    print(f"Grafana: {args.grafana_url}")
    print()

    report = run_validation(
        prometheus_url=args.prometheus_url,
        grafana_url=args.grafana_url,
        grafana_username=args.grafana_username,
        grafana_password=args.grafana_password,
        timeout=args.timeout
    )

    # Print results
    print("Validation Results:")
    print("=" * 60)
    for result in report.results:
        status_symbol = "[PASS]" if result.status == "pass" else ("[PARTIAL]" if result.status == "partial" else "[FAIL]")
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
    report_path = args.output_dir / f"validation-report-{datetime.now(tz=UTC).strftime('%Y%m%d-%H%M%S')}.json"
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
