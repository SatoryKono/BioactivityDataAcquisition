"""Integration tests for Grafana dashboard configurations.

Ensures that dashboards are synchronized with the application metrics
and follow the project's observability standards.
"""

import json
from pathlib import Path
import re
import pytest

# Import metrics module to get all defined metric names
from bioetl.infrastructure.observability import metrics


def get_all_valid_metric_names() -> set[str]:
    """Extract all valid Prometheus metric names including suffixes for Histograms."""
    base_names = set()
    all_valid_names = set()

    for item_name in dir(metrics):
        item = getattr(metrics, item_name)
        if hasattr(item, "_name"):
            base_name = item._name
            base_names.add(base_name)
            all_valid_names.add(base_name)

            # Histograms and Summaries have auto-generated suffixes
            # We check the type by looking at the class name or internal structure
            class_name = type(item).__name__
            if "Histogram" in class_name or "Summary" in class_name:
                all_valid_names.add(f"{base_name}_bucket")
                all_valid_names.add(f"{base_name}_sum")
                all_valid_names.add(f"{base_name}_count")
            elif "Counter" in class_name:
                all_valid_names.add(
                    f"{base_name}_total"
                )  # Prometheus client often adds _total

    return all_valid_names


def get_dashboard_files() -> list[Path]:
    """Get all Grafana dashboard JSON files."""
    dashboard_dir = Path("grafana/dashboards")
    return list(dashboard_dir.glob("*.json"))


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_dashboard_is_valid_json(dashboard_path):
    """L1: Verify that the dashboard file is a valid JSON."""
    with open(dashboard_path, encoding="utf-8-sig") as f:
        data = json.load(f)
    assert isinstance(data, dict)
    assert "title" in data


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_dashboard_metrics_contract(dashboard_path):
    """L3: Verify that all metrics used in PromQL exist in the codebase."""
    valid_metrics = get_all_valid_metric_names()

    with open(dashboard_path, encoding="utf-8-sig") as f:
        dashboard = json.load(f)

    panels = dashboard.get("panels", [])
    for row in dashboard.get("rows", []):
        panels.extend(row.get("panels", []))

    errors = []
    for panel in panels:
        targets = panel.get("targets", [])
        for target in targets:
            query = target.get("expr", "")
            if not query:
                continue

            # Regex to find potential bioetl metric names
            # Matches strings starting with bioetl_ and containing letters, numbers, underscores
            found_metrics = re.findall(r"(bioetl_[a-z0-9_]+)", query)
            for m in found_metrics:
                # Basic check: is this exact name or base name valid?
                if m not in valid_metrics:
                    # Also check without common suffixes
                    base = re.sub(r"(_total|_bucket|_sum|_count)$", "", m)
                    if base not in valid_metrics:
                        errors.append(
                            f"Panel '{panel.get('title')}' uses unknown metric: {m}"
                        )

    assert not errors, f"Metric mismatch in {dashboard_path.name}:\n" + "\n".join(
        errors
    )


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_dashboard_has_required_variables(dashboard_path):
    """Check if mandatory dashboard variables are present."""
    required_vars = {"pipeline", "run_id"}

    with open(dashboard_path, encoding="utf-8-sig") as f:
        dashboard = json.load(f)

    variables = {v.get("name") for v in dashboard.get("templating", {}).get("list", [])}

    missing = required_vars - variables
    assert not missing, f"Dashboard {dashboard_path.name} missing variables: {missing}"
