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

            # Prometheus client auto-creates _created timestamp for all metric types
            all_valid_names.add(f"{base_name}_created")

            if "Histogram" in class_name or "Summary" in class_name:
                all_valid_names.add(f"{base_name}_bucket")
                all_valid_names.add(f"{base_name}_sum")
                all_valid_names.add(f"{base_name}_count")
            elif "Counter" in class_name:
                all_valid_names.add(
                    f"{base_name}_total"
                )  # Prometheus client often adds _total
                all_valid_names.add(
                    f"{base_name}_created"
                )  # Prometheus auto-creates _created timestamp

            # All metric types can have a _created suffix (OpenMetrics)
            all_valid_names.add(f"{base_name}_created")

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
                    base = re.sub(r"(_total|_bucket|_sum|_count|_created)$", "", m)
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


# =============================================================================
# Phase 1 regression tests — critical bug fixes
# =============================================================================


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_no_duplicate_variable_names(dashboard_path):
    """Ensure no duplicate variable names exist in templating."""
    with open(dashboard_path, encoding="utf-8-sig") as f:
        dashboard = json.load(f)

    var_names = [
        v.get("name") for v in dashboard.get("templating", {}).get("list", [])
    ]
    duplicates = [name for name in var_names if var_names.count(name) > 1]
    assert not duplicates, (
        f"Dashboard {dashboard_path.name} has duplicate variables: {set(duplicates)}"
    )


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_run_id_variable_uses_valid_metric(dashboard_path):
    """Ensure run_id variable queries a metric that actually has run_id label."""
    # Metrics that actually have run_id label
    metrics_with_run_id = {
        "bioetl_infrastructure_validated",
        "bioetl_preflight_medallion_policy_valid",
        "bioetl_preflight_config_errors_total",
    }

    with open(dashboard_path, encoding="utf-8-sig") as f:
        dashboard = json.load(f)

    for var in dashboard.get("templating", {}).get("list", []):
        if var.get("name") != "run_id":
            continue
        query = var.get("definition", "") or ""
        if not query:
            query_obj = var.get("query", {})
            if isinstance(query_obj, dict):
                query = query_obj.get("query", "")
            else:
                query = str(query_obj)

        # Extract metric name from label_values(metric{...}, run_id)
        m = re.search(r"label_values\((\w+)", query)
        if m:
            metric_name = m.group(1)
            assert metric_name in metrics_with_run_id, (
                f"Dashboard {dashboard_path.name}: run_id variable queries "
                f"'{metric_name}' which does not have run_id label. "
                f"Use one of: {metrics_with_run_id}"
            )


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_quality_ratio_has_clamp_min(dashboard_path):
    """Ensure quality ratio formulas use clamp_min to prevent division by zero."""
    with open(dashboard_path, encoding="utf-8-sig") as f:
        dashboard = json.load(f)

    panels = dashboard.get("panels", [])
    for panel in panels:
        for target in panel.get("targets", []):
            expr = target.get("expr", "")
            # Detect quality ratio pattern: gold / bronze
            if 'stage="gold"' in expr and 'stage="bronze"' in expr and "/" in expr:
                assert "clamp_min(" in expr, (
                    f"Panel '{panel.get('title')}' in {dashboard_path.name} "
                    f"has quality ratio without clamp_min() — division by zero risk"
                )


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_no_corrupted_unicode(dashboard_path):
    """Ensure no mojibake / corrupted Unicode sequences in dashboard text."""
    with open(dashboard_path, encoding="utf-8-sig") as f:
        content = f.read()

    # Common mojibake patterns: \u0432\u2020 is "в†" which is broken UTF-8
    mojibake_patterns = [
        r"\u0432\u2020",  # в† — common UTF-8 mojibake
        r"\u00c3\u00a2",  # Ã¢ — double-encoded UTF-8
        r"\u00c2\u00b",   # Â — double-encoded UTF-8
    ]
    for pattern in mojibake_patterns:
        assert pattern not in content, (
            f"Dashboard {dashboard_path.name} contains corrupted Unicode: {pattern}"
        )


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_all_variables_used_in_panels_or_cascade(dashboard_path):
    """Ensure every template variable is referenced by panels or other variable definitions.

    Variables marked as 'infrastructure' (run_id) are allowed without direct panel
    references — they serve as user-facing filters and cascade dependencies.
    """
    # Variables that exist as infrastructure filters, not necessarily in PromQL
    infrastructure_vars = {"run_id"}

    with open(dashboard_path, encoding="utf-8-sig") as f:
        dashboard = json.load(f)

    variables = dashboard.get("templating", {}).get("list", [])
    var_names = {v.get("name") for v in variables}

    # Serialize entire dashboard to find $var references
    full_json = json.dumps(dashboard)

    unused = []
    for name in var_names:
        if name in infrastructure_vars:
            continue
        ref_patterns = [f"${name}", f"${{{name}}}"]
        ref_count = sum(full_json.count(p) for p in ref_patterns)
        if ref_count == 0:
            unused.append(name)

    assert not unused, (
        f"Dashboard {dashboard_path.name} has unused variables: {unused}"
    )


# =============================================================================
# Phase 2 regression tests — modernization
# =============================================================================


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_datasource_uses_uid_format(dashboard_path):
    """Ensure datasource references use UID object format, not plain strings."""
    with open(dashboard_path, encoding="utf-8-sig") as f:
        dashboard = json.load(f)

    string_datasources = []
    for panel in dashboard.get("panels", []):
        ds = panel.get("datasource")
        if isinstance(ds, str) and ds not in ("-- Mixed --",):
            string_datasources.append(
                f"Panel '{panel.get('title', 'unknown')}' uses string datasource: {ds}"
            )

    assert not string_datasources, (
        f"Dashboard {dashboard_path.name} has legacy string datasources:\n"
        + "\n".join(string_datasources)
    )


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_dashboard_has_inter_dashboard_links(dashboard_path):
    """Ensure dashboards have navigation links to other dashboards."""
    with open(dashboard_path, encoding="utf-8-sig") as f:
        dashboard = json.load(f)

    links = dashboard.get("links", [])
    assert len(links) >= 1, (
        f"Dashboard {dashboard_path.name} has no inter-dashboard links"
    )
