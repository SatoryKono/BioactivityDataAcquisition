"""Negative coverage controls for RF-002/RF-003 report assembly."""

import copy
import pytest
from scripts.ops.observability.grafana.capture_acceptance import (
    contrast_summary,
    assess_dashboard,
    matrix_coverage,
)

pytestmark = pytest.mark.unit


def test_absent_or_unmeasured_contrast_denominator_is_null():
    for pairs in ([], [{"status": "PASS"}], [{"ratio": None, "threshold": 4.5}]):
        result = contrast_summary(pairs)
        assert result["value"] is None
        assert result["status"] == "NOT_PROVEN"


def test_claimed_pass_does_not_override_the_measured_ratio():
    result = contrast_summary([{"ratio": 4.4999, "threshold": 4.5, "status": "PASS"}])
    assert result["failed"] == 1
    assert result["value"] == 0
    assert result["status"] == "NOT_PROVEN"


def test_disabled_exemption_requires_an_observed_disabled_control():
    assert (
        contrast_summary([{"status": "EXEMPT_DISABLED", "disabled": False}])[
            "unmeasured"
        ]
        == 1
    )
    assert (
        contrast_summary([{"status": "EXEMPT_DISABLED", "disabled": True}])[
            "exempt_disabled"
        ]
        == 1
    )


def test_reported_first_panel_list_cannot_hide_missing_model_coverage():
    dashboard = {
        "uid": "test",
        "provisionedModel": {
            "before": {"panels": [{"id": 1, "type": "text", "gridPos": {"y": 0}}]}
        },
        "firstWindowPanels": [],
        "panelContainment": {"status": "ok", "panels": []},
    }
    result = assess_dashboard(dashboard, {})
    assert result["layout"]["status"] == "FAIL"
    assert result["layout"]["required_first_window_panels"] == [1]
    assert not result["accessibility"]["critical_coverage_complete"]
    assert result["accessibility"]["color_only_encoding_count"] is None


def _matrix():
    profiles = {
        (w, h, theme, 100, "full")
        for w, h in ((1366, 768), (1440, 900), (1920, 1080))
        for theme in ("dark", "light")
    }
    profiles |= {
        (1366, 768, theme, zoom, "viewport")
        for theme in ("dark", "light")
        for zoom in (100, 200)
    }
    return [
        {
            "source": {"commit_sha": "a" * 40},
            "capture_context": {"time_range": {"from": "1", "to": "2"}},
            "requested": {
                "viewport": {"width": w, "height": h},
                "theme": theme,
                "browser_zoom": zoom,
                "capture_surface": surface,
            },
            "dashboards": [
                {
                    "uid": "test",
                    "actualTheme": theme,
                    "browserState": {
                        "layoutViewport": {
                            "width": int(w / (zoom / 100)),
                            "height": int(h / (zoom / 100)),
                        },
                        "devicePixelRatio": zoom / 100,
                    },
                }
            ],
        }
        for w, h, theme, zoom, surface in profiles
    ]


def test_matrix_requires_every_viewport_theme_zoom_profile_and_matching_context():
    manifests = _matrix()
    assert matrix_coverage(manifests)["status"] == "PASS"
    assert matrix_coverage(manifests[:-1])["status"] == "NOT_PROVEN"
    changed = copy.deepcopy(manifests)
    changed[0]["capture_context"]["time_range"]["from"] = "3"
    assert matrix_coverage(changed)["status"] == "NOT_PROVEN"
    changed = copy.deepcopy(manifests)
    changed[0]["dashboards"][0]["browserState"]["devicePixelRatio"] = 0.5
    assert matrix_coverage(changed)["status"] == "NOT_PROVEN"
