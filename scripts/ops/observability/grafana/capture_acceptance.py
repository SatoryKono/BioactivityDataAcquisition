"""Separate layout and accessibility verdicts from capture provenance."""

from __future__ import annotations

from collections import Counter


def contrast_summary(pairs: list[dict]) -> dict:
    """An absent or unmeasured denominator cannot become a passing rate."""
    counts = Counter(pair.get("status", "NOT_VERIFIABLE") for pair in pairs)
    measured = counts["PASS"] + counts["FAIL"]
    return {
        "numerator": counts["PASS"],
        "denominator": measured,
        "value": counts["PASS"] / measured if measured else None,
        "unmeasured": counts["NOT_VERIFIABLE"],
        "exempt_disabled": counts["EXEMPT_DISABLED"],
        "status": "PASS"
        if measured and not counts["FAIL"] and not counts["NOT_VERIFIABLE"]
        else "NOT_PROVEN",
    }


def assess_dashboard(dashboard: dict, requested: dict) -> dict:
    """Require positive panel coverage and actual measurements for every claim."""
    first = {p["id"] for p in dashboard.get("firstWindowPanels", [])}
    containment = dashboard.get("panelContainment", {})
    measured = {p.get("id") for p in containment.get("panels", [])}
    screenshots = {
        p.get("panelId") for p in dashboard.get("criticalPanelScreenshots", [])
    }
    reasons = []
    if not first or measured != first or screenshots != first:
        reasons.append("missing first-window DOM or critical-panel capture coverage")
    if containment.get("status") != "ok":
        reasons.append("first-window containment failed or unavailable")
    if dashboard.get("browserState", {}).get("actualKiosk") != requested.get(
        "kiosk_mode"
    ):
        reasons.append("actual kiosk does not match requested profile")
    if dashboard.get("layoutGeometry", {}).get("horizontalOverflow") is not False:
        reasons.append("page horizontal overflow or missing measurement")
    if dashboard.get("typographyValidation", {}).get("status") != "ok":
        reasons.append("computed typography failed or unavailable")
    text = contrast_summary(
        dashboard.get("accessibilityMeasurements", {}).get("pairs", [])
    )
    graphics = dashboard.get("graphicsMeasurements", {})
    graphical = contrast_summary(graphics.get("pairs", []))
    canvas_count = len(graphics.get("canvases", []))
    return {
        "uid": dashboard.get("uid"),
        "layout": {
            "status": "FAIL" if reasons else "PASS",
            "reasons": reasons,
            "required_first_window_panels": sorted(first),
            "measured_first_window_panels": sorted(measured),
        },
        "accessibility": {
            "status": "NOT_PROVEN",
            "text": text,
            "graphics": graphical,
            "unmeasured_canvases": canvas_count,
            "color_only_encoding_count": None,
            "color_only_reason": "state/series cue coverage requires an explicit scenario review",
        },
    }


def assess_manifest(manifest: dict) -> dict:
    """Return scoped results; missing state/canvas evidence remains visible."""
    dashboards = [
        assess_dashboard(d, manifest.get("requested", {}))
        for d in manifest.get("dashboards", [])
    ]
    return {
        "capture_id": manifest.get("capture_id"),
        "requested": manifest.get("requested"),
        "dashboards": dashboards,
        "layout_status": "PASS"
        if dashboards and all(d["layout"]["status"] == "PASS" for d in dashboards)
        else "FAIL",
        "accessibility_status": "NOT_PROVEN",
    }
