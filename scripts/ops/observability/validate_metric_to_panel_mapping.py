#!/usr/bin/env python3
"""
Metric-to-Panel Mapping Runtime Validation for BioETL.
Addresses OBS-002: Metric-to-Panel Mapping Runtime Proof Gap
"""

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

# Configuration
DEFAULT_PROMETHEUS_URL = "http://localhost:9090"
DEFAULT_DASHBOARD_DIR = Path("grafana/dashboards")
DEFAULT_OUTPUT_DIR = Path("reports/observability/metric-panel-validation")
DEFAULT_TIMEOUT = 5.0


@dataclass
class MetricPanelValidationResult:
    """Result of metric-to-panel validation."""

    dashboard_uid: str
    panel_id: int
    panel_title: str
    metric_name: str
    status: Literal["pass", "fail", "skip"]
    message: str
    details: dict[str, Any] | None = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(tz=UTC).isoformat()


@dataclass
class MetricPanelValidationReport:
    """Complete metric-to-panel validation report."""

    prometheus_url: str
    timestamp: str
    results: list[MetricPanelValidationResult]
    summary: dict[str, Any]


def _fetch_json(url: str, timeout: float) -> dict[str, Any]:
    """Fetch JSON from URL."""
    from scripts.engineering.common.repo_paths import ensure_local_http_url

    safe_url = ensure_local_http_url(url)
    with urlopen(safe_url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def get_prometheus_metrics(prometheus_url: str, timeout: float) -> set[str]:
    """Get all metric names from Prometheus."""
    try:
        url = f"{prometheus_url}/api/v1/label/__name__/values"
        data = _fetch_json(url, timeout)
        if data.get("status") == "success":
            return set(data.get("data", []))
        return set()
    except Exception:
        return set()


def extract_metrics_from_promql(expr: str) -> list[str]:
    """Extract metric names from PromQL expression."""
    import re

    # Simple extraction - match metric name patterns
    # This is a basic implementation; full PromQL parsing would be more complex
    metric_pattern = r"\b[a-zA-Z_]\w*\b"
    potential_metrics = re.findall(metric_pattern, expr)

    # Filter out PromQL keywords and functions
    keywords = {
        "sum",
        "avg",
        "min",
        "max",
        "count",
        "rate",
        "irate",
        "increase",
        "by",
        "without",
        "group_left",
        "group_right",
        "offset",
        "at",
        "and",
        "or",
        "unless",
        "label_replace",
        "label_join",
        "vector",
        "matrix",
        "scalar",
        "string",
        "on",
        "ignoring",
        "group",
        "clamp_max",
        "clamp_min",
        "abs",
        "sqrt",
        "exp",
        "ln",
        "log2",
        "log10",
        "hour",
        "minute",
        "month",
        "year",
        "day",
        "day_of_month",
        "day_of_week",
        "days_in_month",
        "delta",
        "idelta",
        "predict_linear",
        "holt_winters",
        "quantile",
        "topk",
        "bottomk",
        "resets",
        "changes",
        "deriv",
        "bool",
        "float",
        "int",  # Type conversion functions
    }

    # Also filter out common label names and values
    label_names = {
        "job",
        "instance",
        "__name__",
        "alertstate",
        "alertname",
        "severity",
        "pipeline",
        "run_type",
        "stage",
        "status",
        "step_kind",
        "step_status",
        "provider",
        "adapter",
        "workflow",
        "error_type",
        "reason_code",
    }

    metrics = [
        m
        for m in potential_metrics
        if m not in keywords and m not in label_names and not m.isdigit()
    ]
    return sorted(set(metrics))


def load_dashboard(dashboard_path: Path) -> dict[str, Any]:
    """Load dashboard JSON."""
    with open(dashboard_path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_panel_metrics(panel: dict[str, Any]) -> list[str]:
    """Extract metrics from a panel's targets."""
    metrics = []
    for target in panel.get("targets", []):
        expr = target.get("expr", "")
        if expr:
            panel_metrics = extract_metrics_from_promql(expr)
            metrics.extend(panel_metrics)
    return sorted(set(metrics))


def validate_metric_exists(
    metric_name: str, prometheus_metrics: set[str], prometheus_url: str, timeout: float
) -> tuple[bool, str]:
    """Validate if a metric exists in Prometheus."""
    if metric_name in prometheus_metrics:
        return True, f"Metric {metric_name} found in Prometheus"

    # Try to query the metric directly
    try:
        encoded_metric = quote(metric_name)
        query_url = f"{prometheus_url}/api/v1/query?query={encoded_metric}"
        data = _fetch_json(query_url, timeout)
        if data.get("status") == "success":
            result_type = data.get("data", {}).get("resultType")
            results = data.get("data", {}).get("result", [])
            # Empty successful vector/matrix is "not found", not "queryable".
            if results:
                return (
                    True,
                    f"Metric {metric_name} queryable (resultType: {result_type})",
                )
        return False, f"Metric {metric_name} not found in Prometheus"
    except Exception as e:
        return False, f"Metric {metric_name} query failed: {e}"


def _evaluate_promql_query(
    expr: str, prometheus_url: str, timeout: float
) -> tuple[bool, str]:
    """Execute one PromQL expression and classify the response."""
    try:
        encoded_expr = quote(expr)
        query_url = f"{prometheus_url}/api/v1/query?query={encoded_expr}"
        data = _fetch_json(query_url, timeout)
        if data.get("status") != "success":
            return False, f"Query failed: {data.get('error', 'Unknown error')}"
        result_data = data.get("data", {})
        result_type = result_data.get("resultType", "unknown")
        results = result_data.get("result", [])
        if results:
            return (
                True,
                f"Query returned {len(results)} results (resultType: {result_type})",
            )
        return False, f"Query returned no results (resultType: {result_type})"
    except KeyError as e:
        return False, f"Query execution failed: missing key in response ({e})"
    except Exception as e:
        return False, f"Query execution failed: {e}"


def validate_panel_query(
    panel: dict[str, Any], prometheus_url: str, timeout: float
) -> tuple[bool, str]:
    """Validate if a panel's query returns data."""
    for target in panel.get("targets", []):
        expr = target.get("expr", "")
        if not expr:
            continue
        return _evaluate_promql_query(expr, prometheus_url, timeout)
    return False, "No valid queries found in panel"


def _panel_query_execution_result(
    panel: dict[str, Any],
    *,
    dashboard_uid: str,
    panel_id: int,
    panel_title: str,
    prometheus_url: str,
    timeout: float,
) -> MetricPanelValidationResult:
    has_template_vars = any(
        "$" in target.get("expr", "") for target in panel.get("targets", [])
    )
    datasource = panel.get("datasource", {})
    datasource_type = datasource.get("type", "") if isinstance(datasource, dict) else ""
    is_loki_query = datasource_type.lower() == "loki"
    if is_loki_query:
        return MetricPanelValidationResult(
            dashboard_uid=dashboard_uid,
            panel_id=panel_id,
            panel_title=panel_title,
            metric_name="query_execution",
            status="skip",
            message="Panel uses Loki datasource, skipping Prometheus query validation",
            details={"datasource_type": "loki"},
        )
    if has_template_vars:
        return MetricPanelValidationResult(
            dashboard_uid=dashboard_uid,
            panel_id=panel_id,
            panel_title=panel_title,
            metric_name="query_execution",
            status="skip",
            message="Panel contains template variables, skipping query validation",
            details={"has_template_vars": True},
        )
    query_valid, query_message = validate_panel_query(panel, prometheus_url, timeout)
    return MetricPanelValidationResult(
        dashboard_uid=dashboard_uid,
        panel_id=panel_id,
        panel_title=panel_title,
        metric_name="query_execution",
        status="pass" if query_valid else "fail",
        message=query_message,
        details={"query_valid": query_valid},
    )


def _validate_panel_metrics(
    panel: dict[str, Any],
    *,
    dashboard_uid: str,
    prometheus_metrics: set[str],
    prometheus_url: str,
    timeout: float,
) -> list[MetricPanelValidationResult]:
    panel_id_value = panel.get("id")
    panel_id = panel_id_value if isinstance(panel_id_value, int) else 0
    panel_title = str(panel.get("title", f"panel-{panel_id}"))
    panel_metrics = extract_panel_metrics(panel)
    if not panel_metrics:
        return [
            MetricPanelValidationResult(
                dashboard_uid=dashboard_uid,
                panel_id=panel_id,
                panel_title=panel_title,
                metric_name="N/A",
                status="skip",
                message="Panel has no PromQL metrics (text/row panel)",
            )
        ]
    results: list[MetricPanelValidationResult] = []
    for metric_name in panel_metrics:
        exists, message = validate_metric_exists(
            metric_name, prometheus_metrics, prometheus_url, timeout
        )
        results.append(
            MetricPanelValidationResult(
                dashboard_uid=dashboard_uid,
                panel_id=panel_id,
                panel_title=panel_title,
                metric_name=metric_name,
                status="pass" if exists else "fail",
                message=message,
                details={"metric_exists": exists},
            )
        )
    results.append(
        _panel_query_execution_result(
            panel,
            dashboard_uid=dashboard_uid,
            panel_id=panel_id,
            panel_title=panel_title,
            prometheus_url=prometheus_url,
            timeout=timeout,
        )
    )
    return results


def _collect_panel_mapping_results(
    panels: list[dict[str, Any]],
    *,
    dashboard_uid: str,
    prometheus_metrics: set[str],
    prometheus_url: str,
    timeout: float,
) -> list[MetricPanelValidationResult]:
    results: list[MetricPanelValidationResult] = []
    for panel in panels:
        if panel.get("type") == "row":
            results.extend(
                _collect_panel_mapping_results(
                    panel.get("panels", []),
                    dashboard_uid=dashboard_uid,
                    prometheus_metrics=prometheus_metrics,
                    prometheus_url=prometheus_url,
                    timeout=timeout,
                )
            )
            continue
        results.extend(
            _validate_panel_metrics(
                panel,
                dashboard_uid=dashboard_uid,
                prometheus_metrics=prometheus_metrics,
                prometheus_url=prometheus_url,
                timeout=timeout,
            )
        )
        nested = panel.get("panels", [])
        if nested:
            results.extend(
                _collect_panel_mapping_results(
                    nested,
                    dashboard_uid=dashboard_uid,
                    prometheus_metrics=prometheus_metrics,
                    prometheus_url=prometheus_url,
                    timeout=timeout,
                )
            )
    return results


def validate_dashboard_metric_mapping(
    dashboard_path: Path,
    prometheus_metrics: set[str],
    prometheus_url: str,
    timeout: float,
) -> list[MetricPanelValidationResult]:
    """Validate metric-to-panel mapping for a single dashboard."""
    try:
        dashboard = load_dashboard(dashboard_path)
        dashboard_uid = dashboard.get("uid", dashboard_path.stem)
        return _collect_panel_mapping_results(
            dashboard.get("panels", []),
            dashboard_uid=dashboard_uid,
            prometheus_metrics=prometheus_metrics,
            prometheus_url=prometheus_url,
            timeout=timeout,
        )
    except Exception as e:
        return [
            MetricPanelValidationResult(
                dashboard_uid=dashboard_path.stem,
                panel_id=0,
                panel_title="dashboard_load_error",
                metric_name="N/A",
                status="fail",
                message=f"Failed to load dashboard: {e}",
                details={"error": str(e)},
            )
        ]


def run_metric_panel_validation(
    prometheus_url: str, dashboard_dir: Path, timeout: float
) -> MetricPanelValidationReport:
    """Run complete metric-to-panel validation."""

    # Get all Prometheus metrics
    prometheus_metrics = get_prometheus_metrics(prometheus_url, timeout)

    # Validate all dashboards
    all_results = []
    for dashboard_path in sorted(dashboard_dir.glob("*.json")):
        dashboard_results = validate_dashboard_metric_mapping(
            dashboard_path, prometheus_metrics, prometheus_url, timeout
        )
        all_results.extend(dashboard_results)

    # Calculate summary
    passed = sum(1 for r in all_results if r.status == "pass")
    failed = sum(1 for r in all_results if r.status == "fail")
    skipped = sum(1 for r in all_results if r.status == "skip")
    total = len(all_results)

    # Group by dashboard
    dashboard_stats = {}
    for result in all_results:
        uid = result.dashboard_uid
        if uid not in dashboard_stats:
            dashboard_stats[uid] = {"pass": 0, "fail": 0, "skip": 0}
        dashboard_stats[uid][result.status] += 1

    summary = {
        "total_checks": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "success_rate": f"{(passed / total * 100):.1f}%" if total > 0 else "0%",
        "total_dashboards": len(dashboard_stats),
        "dashboard_stats": dashboard_stats,
        "total_prometheus_metrics": len(prometheus_metrics),
    }

    return MetricPanelValidationReport(
        prometheus_url=prometheus_url,
        timestamp=datetime.now(tz=UTC).isoformat(),
        results=all_results,
        summary=summary,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Validate metric-to-panel mapping for BioETL dashboards (OBS-002)"
    )
    parser.add_argument(
        "--prometheus-url", default=DEFAULT_PROMETHEUS_URL, help="Prometheus base URL"
    )
    parser.add_argument(
        "--dashboard-dir",
        type=Path,
        default=DEFAULT_DASHBOARD_DIR,
        help="Dashboard directory",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="Request timeout in seconds",
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
    print("Starting metric-to-panel validation...")
    print(f"Prometheus: {args.prometheus_url}")
    print(f"Dashboard directory: {args.dashboard_dir}")
    print()

    report = run_metric_panel_validation(
        prometheus_url=args.prometheus_url,
        dashboard_dir=args.dashboard_dir,
        timeout=args.timeout,
    )

    # Print results
    print("Validation Results:")
    print("=" * 60)
    print(f"Total Prometheus metrics: {report.summary['total_prometheus_metrics']}")
    print(f"Total dashboards validated: {report.summary['total_dashboards']}")
    print()

    for dashboard_uid, stats in report.summary["dashboard_stats"].items():
        print(f"Dashboard {dashboard_uid}:")
        print(
            f"  Passed: {stats['pass']}, Failed: {stats['fail']}, Skipped: {stats['skip']}"
        )

    print()
    print("Summary:")
    print("=" * 60)
    for key, value in report.summary.items():
        if key != "dashboard_stats":
            print(f"  {key}: {value}")

    # Print failed checks
    failed_results = [r for r in report.results if r.status == "fail"]
    if failed_results:
        print()
        print("Failed Checks:")
        print("=" * 60)
        for result in failed_results[:10]:  # Show first 10 failures
            print(f"  {result.dashboard_uid}#{result.panel_id} ({result.panel_title})")
            print(f"    Metric: {result.metric_name}")
            print(f"    Message: {result.message}")
        if len(failed_results) > 10:
            print(f"  ... and {len(failed_results) - 10} more failures")

    # Save report
    report_path = (
        args.output_dir
        / f"metric-panel-report-{datetime.now(tz=UTC).strftime('%Y%m%d-%H%M%S')}.json"
    )
    with open(report_path, "w") as f:
        json.dump(asdict(report), f, indent=2, default=str)

    print(f"\nReport saved to: {report_path}")

    # Exit with appropriate code
    if report.summary["failed"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
