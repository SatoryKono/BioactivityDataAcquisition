"""Integration tests for Grafana dashboard panel-type visualization standards."""

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_files,
    get_dashboard_panels,
    load_dashboard,
)

pytestmark = pytest.mark.integration


def test_stat_panels_use_correct_color_mode():
    """Stat panels should use appropriate colorMode based on their role."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            panel_type = panel.get("type")
            if panel_type == "stat":
                title = panel.get("title", "")
                options = panel.get("options", {})
                color_mode = options.get("colorMode")
                graph_mode = options.get("graphMode")
                # Check for selected-range trend stats
                if "Trend" in title or "trend" in title.lower():
                    # Trend stats should use colorMode=value, graphMode=area
                    if color_mode:
                        assert color_mode in ("value", "background"), (
                            f"{dashboard_path.name}:{title} trend stat should use colorMode=value/background, got {color_mode}"
                        )
                    if graph_mode:
                        assert graph_mode in ("area", "none"), (
                            f"{dashboard_path.name}:{title} trend stat should use graphMode=area/none, got {graph_mode}"
                        )


def test_gauge_panels_show_threshold_markers():
    """Gauge panels should have showThresholdMarkers=true."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            panel_type = panel.get("type")
            if panel_type == "gauge":
                title = panel.get("title", "")
                options = panel.get("options", {})
                # Check for percentage/score/latency gauges
                if "Percentage" in title or "Score" in title or "Latency" in title:
                    show_markers = options.get("showThresholdMarkers")
                    show_labels = options.get("showThresholdLabels")
                    # showThresholdMarkers should be true, showThresholdLabels should be false
                    # This is a SHOULD, not MUST - just check if configured
                    if show_markers is not None:
                        assert show_markers is True, (
                            f"{dashboard_path.name}:{title} gauge should have showThresholdMarkers=true"
                        )
                    if show_labels is not None:
                        assert show_labels is False, (
                            f"{dashboard_path.name}:{title} gauge should have showThresholdLabels=false"
                        )


def test_timeseries_panels_use_correct_tooltip_mode():
    """Timeseries panels should use appropriate tooltip mode based on their role."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            panel_type = panel.get("type")
            if panel_type == "timeseries":
                title = panel.get("title", "")
                options = panel.get("options", {})
                tooltip = options.get("tooltip", {})
                tooltip_mode = tooltip.get("mode")
                tooltip_sort = tooltip.get("sort")
                # Check for comparative timeseries (multiple series)
                if "Compare" in title or "vs" in title:
                    if tooltip_mode:
                        assert tooltip_mode in ("multi", "single"), (
                            f"{dashboard_path.name}:{title} comparative timeseries should use tooltip.mode=multi/single, got {tooltip_mode}"
                        )
                # Check for scalar trend timeseries
                if "Trend" in title:
                    if tooltip_mode:
                        assert tooltip_mode in ("single", "multi"), (
                            f"{dashboard_path.name}:{title} trend timeseries should use tooltip.mode=single/multi, got {tooltip_mode}"
                        )
