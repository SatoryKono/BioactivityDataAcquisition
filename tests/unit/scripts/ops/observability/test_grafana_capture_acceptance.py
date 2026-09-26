"""Negative coverage controls for RF-002/RF-003 report assembly."""

import copy
import pytest
from scripts.ops.observability.grafana.capture_acceptance import (
    contrast_summary,
    assess_dashboard,
    matrix_coverage,
    native_zoom_matches,
)

pytestmark = pytest.mark.unit


def test_native_zoom_requires_browser_api_proof_not_only_emulated_dimensions():
    requested = {"browser_zoom": 200, "viewport": {"width": 1366, "height": 768}}
    dashboard = {
        "nativeBrowserZoom": {
            "actualFactor": 2,
            "physicalContentViewport": requested["viewport"],
            "method": "chrome.tabs.setZoom/getZoom; native content viewport",
            "browserVersion": "Chrome/131.0.6778.33",
            "actual": {
                "devicePixelRatio": 2,
                "innerWidth": 683,
                "innerHeight": 384,
                "cssZoom": "1",
            },
        }
    }
    assert native_zoom_matches(dashboard, requested)
    for changed in (
        {"actualFactor": 1},
        {"method": "layout-viewport-and-device-scale-factor"},
        {"actual": {**dashboard["nativeBrowserZoom"]["actual"], "cssZoom": "2"}},
        {"actual": {**dashboard["nativeBrowserZoom"]["actual"], "innerWidth": 1366}},
    ):
        invalid = {"nativeBrowserZoom": {**dashboard["nativeBrowserZoom"], **changed}}
        assert not native_zoom_matches(invalid, requested)
    assert not native_zoom_matches({}, requested)


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


def test_later_terminal_pass_cannot_validate_an_earlier_loading_png():
    dashboard = {
        "uid": "test",
        "provisionedModel": {
            "before": {"panels": [{"id": 1, "type": "text", "gridPos": {"y": 0}}]}
        },
        "terminalStateValidation": {
            "status": "ok",
            "panelStates": [{"id": 1, "classification": "healthy"}],
        },
    }
    reasons = assess_dashboard(dashboard, {})["layout"]["reasons"]
    assert "terminal readiness was not proved before PNG capture" in reasons


def test_manual_review_must_bind_exact_capture_hashes_and_all_scenarios():
    from scripts.ops.observability.grafana.capture_acceptance import (
        review_binding_errors,
    )

    manifests = [{"capture_id": "one", "source": {"commit_sha": "a" * 40}}]
    references = [{"sha256": "b" * 64}]
    review = {
        "reviewer": "reviewer",
        "source_sha": "a" * 40,
        "captures": {"one": "b" * 64},
        "scenarios": {
            key: {"status": "NOT_VERIFIABLE", "reason": "not available in this runtime"}
            for key in (
                "normal_populated",
                "valid_zero",
                "expected_empty_or_selection",
                "error_or_anomaly",
            )
        },
    }
    assert not review_binding_errors(review, manifests, references)
    review["captures"]["one"] = "c" * 64
    assert review_binding_errors(review, manifests, references)
    review["captures"]["one"] = "b" * 64
    del review["scenarios"]["valid_zero"]
    assert review_binding_errors(review, manifests, references)


def test_color_only_zero_requires_observed_critical_copy_and_complete_series_controls():
    from scripts.ops.observability.grafana.capture_acceptance import validate_panel_cues

    dashboard = {
        "terminalStateValidation": {
            "panelStates": [{"id": 1, "bodyText": "UNKNOWN: inspect source"}]
        }
    }
    reviews = [{"id": 1, "status": "PASS", "evidence_text": "UNKNOWN"}]
    assert validate_panel_cues(dashboard, reviews, {1}, {1})["status"] == "PASS"
    reviews[0]["evidence_text"] = "OK"
    assert validate_panel_cues(dashboard, reviews, {1}, {1})["status"] == "NOT_PROVEN"
    reviews[0]["evidence_text"] = "UNKNOWN"
    dashboard["seriesControls"] = [
        {
            "panel": "panel-2",
            "status": "PASS",
            "labels": ["a", "b"],
            "entries": [
                {"label": "a", "focused": True, "active": ["a"], "restored": ["a", "b"]}
            ],
        }
    ]
    assert validate_panel_cues(dashboard, reviews, {1}, {1})["status"] == "NOT_PROVEN"


def test_isolated_canvas_measurement_resolves_occlusion_but_preserves_failure():
    from scripts.ops.observability.grafana.capture_acceptance import canvas_pairs

    base = {
        "panel": "panel-1",
        "element": "canvas stroke",
        "text": None,
        "foreground": [240, 200, 0],
        "background": [255, 255, 255],
        "threshold": 3,
        "method": "native",
        "ratio": None,
        "status": "NOT_VERIFIABLE",
    }
    measured = {
        **base,
        "ratio": 1.6,
        "status": "FAIL",
        "pixelWitness": {"foreground": {"x": 1, "y": 1}},
    }
    dashboard = {
        "canvasEvidence": [{"measurements": {"pairs": {"graphics": [base]}}}],
        "seriesControls": [
            {
                "entries": [
                    {"canvas": [{"measurements": {"pairs": {"graphics": [measured]}}}]}
                ]
            }
        ],
    }
    result = canvas_pairs(dashboard, "graphics")
    assert len(result) == 1
    assert result[0]["status"] == "FAIL"
    assert result[0]["measured_frames"] == 1
    assert result[0]["observed_frames"] == 2
