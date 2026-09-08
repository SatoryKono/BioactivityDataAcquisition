"""Compute separate, fail-closed layout and accessibility capture verdicts."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path


def contrast_summary(pairs: list[dict]) -> dict:
    """Recompute thresholds; an absent denominator is unknown, never passing."""
    counts: Counter = Counter()
    for pair in pairs:
        if pair.get("status") == "EXEMPT_DISABLED" and pair.get("disabled") is True:
            counts["EXEMPT_DISABLED"] += 1
            continue
        ratio, threshold = pair.get("ratio"), pair.get("threshold")
        if (
            not isinstance(ratio, (float, int))
            or not math.isfinite(ratio)
            or threshold not in (3, 4.5)
        ):
            counts["NOT_VERIFIABLE"] += 1
        else:
            counts["PASS" if ratio >= threshold else "FAIL"] += 1
    measured = counts["PASS"] + counts["FAIL"]
    return {
        "numerator": counts["PASS"],
        "denominator": measured,
        "value": counts["PASS"] / measured if measured else None,
        "failed": counts["FAIL"],
        "unmeasured": counts["NOT_VERIFIABLE"],
        "exempt_disabled": counts["EXEMPT_DISABLED"],
        "status": "PASS"
        if measured and not counts["FAIL"] and not counts["NOT_VERIFIABLE"]
        else "NOT_PROVEN",
    }


def model_panels(dashboard: dict) -> dict[int, dict]:
    """Derive required IDs from the provisioned model, not a reported count."""
    result = {}
    stack = list(
        dashboard.get("provisionedModel", {}).get("before", {}).get("panels", [])
    )
    while stack:
        panel = stack.pop()
        stack.extend(panel.get("panels", []))
        if panel.get("type") != "row":
            result[panel["id"]] = panel
    return result


def measurement_pairs(dashboard: dict, kind: str) -> list[dict]:
    """Include virtualized/scroll-tile evidence and deduplicate repeated pairs."""
    key = "accessibilityMeasurements" if kind == "text" else "graphicsMeasurements"
    pairs = list(dashboard.get(key, {}).get("pairs", []))
    for tile in dashboard.get("scrollCapture", {}).get("tiles", []):
        pairs.extend(tile.get("evidence", {}).get(kind, {}).get("pairs", []))
    unique = {}
    for pair in pairs:
        identity = {
            k: v
            for k, v in pair.items()
            if k
            not in {
                "bbox",
                "clientHeight",
                "clientWidth",
                "scrollHeight",
                "scrollWidth",
            }
        }
        unique[json.dumps(identity, sort_keys=True)] = pair
    return list(unique.values())


def _panel_number(value: object) -> int | None:
    try:
        return int(str(value).removeprefix("panel-"))
    except ValueError:
        return None


def _layout_reasons(dashboard: dict, requested: dict, first: set[int]) -> list[str]:
    reasons = []
    containment = dashboard.get("panelContainment", {})
    measured = {p.get("id") for p in containment.get("panels", [])}
    screenshots = {
        p.get("panelId") for p in dashboard.get("criticalPanelScreenshots", [])
    }
    if not first or measured != first or screenshots != first:
        reasons.append("missing first-window DOM or critical-panel capture coverage")
    if containment.get("status") != "ok" or any(
        p.get("status") != "ok" for p in containment.get("panels", [])
    ):
        reasons.append("first-window containment failed or unavailable")
    if dashboard.get("browserState", {}).get("actualKiosk") != requested.get(
        "kiosk_mode"
    ):
        reasons.append("actual kiosk does not match requested profile")
    if dashboard.get("layoutGeometry", {}).get("horizontalOverflow") is not False:
        reasons.append("page horizontal overflow or missing measurement")
    for key in ("typographyValidation", "navigationValidation"):
        if dashboard.get(key, {}).get("status") != "ok":
            reasons.append(f"{key} failed or unavailable")
    for table in dashboard.get("tablePagination", []):
        if table.get("status") not in {"COMPLETE", "NOT_PAGINATED"}:
            reasons.append(f"incomplete table pagination: {table.get('panelId')}")
        for page in table.get("pages", []):
            for scroller in page.get("scrollers", []):
                if any(
                    scroller.get(f"scroll{axis}", 0)
                    > scroller.get(f"client{axis}", 0) + 2
                    for axis in ("Width", "Height")
                ):
                    reasons.append(
                        f"table page overflow: {table.get('panelId')}/{page.get('page')}"
                    )
    return reasons


def assess_dashboard(dashboard: dict, requested: dict) -> dict:
    """Keep critical measurement coverage distinct from the full inventory."""
    panels = model_panels(dashboard)
    first = {
        id_ for id_, p in panels.items() if p.get("gridPos", {}).get("y", 1000) < 18
    }
    reasons = _layout_reasons(dashboard, requested, first)
    observed = {
        _panel_number(p.get("panel"))
        for tile in dashboard.get("scrollCapture", {}).get("tiles", [])
        for p in tile.get("panels", [])
    }
    if requested.get("capture_surface") == "full" and not set(panels).issubset(
        observed
    ):
        reasons.append("expanded panel-level scroll evidence incomplete")
    text, graphics = (
        measurement_pairs(dashboard, "text"),
        measurement_pairs(dashboard, "graphics"),
    )
    canvas_panels = {
        _panel_number(c.get("panel"))
        for c in dashboard.get("graphicsMeasurements", {}).get("canvases", [])
    }
    terminal = {
        p.get("id"): p
        for p in dashboard.get("terminalStateValidation", {}).get("panelStates", [])
    }
    statuses = []
    for id_, panel in sorted(panels.items()):
        pairs = [p for p in text + graphics if _panel_number(p.get("panel")) == id_]
        summary = contrast_summary(pairs)
        state = terminal.get(id_, {}).get("classification")
        reasons_panel = []
        if summary["failed"]:
            status = "DEFECT"
            reasons_panel.append("measured contrast below required threshold")
        elif (
            summary["unmeasured"] or not summary["denominator"] or id_ in canvas_panels
        ):
            status = "NOT_VERIFIABLE"
            reasons_panel.append(
                "missing/unsupported text, graphic or canvas measurements"
            )
        elif state in {
            "valid-empty",
            "telemetry-absent",
            "not-applicable",
            "incomplete",
        }:
            status = "EXPECTED_EMPTY"
        else:
            status = "OK"
        statuses.append(
            {
                "id": id_,
                "title": panel.get("title"),
                "critical": id_ in first,
                "status": status,
                "reasons": reasons_panel,
                "terminal_state": state,
                "contrast": summary,
                "scroll_observed": id_ in observed,
            }
        )
    critical = [p for p in text + graphics if _panel_number(p.get("panel")) in first]
    critical_measured = {
        _panel_number(p.get("panel")) for p in critical if p.get("ratio") is not None
    }
    return {
        "uid": dashboard.get("uid"),
        "layout": {
            "status": "FAIL" if reasons else "PASS",
            "reasons": reasons,
            "required_first_window_panels": sorted(first),
            "measured_first_window_panels": sorted(
                p.get("id")
                for p in dashboard.get("panelContainment", {}).get("panels", [])
            ),
        },
        "accessibility": {
            "status": "NOT_PROVEN",
            "text": contrast_summary(text),
            "graphics": contrast_summary(graphics),
            "critical_contrast": contrast_summary(critical),
            "critical_coverage_complete": bool(first) and first <= critical_measured,
            "unmeasured_canvas_panels": sorted(canvas_panels),
            "color_only_encoding_count": None,
            "color_only_reason": "state/series cue coverage requires an explicit source-bound scenario review",
        },
        "panels": statuses,
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


def matrix_coverage(manifests: list[dict]) -> dict:
    """Require fixed, matching source/context and every mandatory actual profile."""
    profiles = set()
    identities = set()
    errors = []
    for m in manifests:
        r = m.get("requested", {})
        viewport = r.get("viewport", {})
        profile = (
            viewport.get("width"),
            viewport.get("height"),
            r.get("theme"),
            r.get("browser_zoom"),
            r.get("capture_surface"),
        )
        profiles.add(profile)
        identities.add(
            json.dumps(
                {
                    "source": m.get("source", {}).get("commit_sha"),
                    "context": m.get("capture_context"),
                    "base": m.get("base_url"),
                },
                sort_keys=True,
            )
        )
        for d in m.get("dashboards", []):
            state = d.get("browserState", {})
            zoom = r.get("browser_zoom", 100)
            expected = {
                "width": int(viewport.get("width", 0) / (zoom / 100)),
                "height": int(viewport.get("height", 0) / (zoom / 100)),
            }
            if (
                d.get("actualTheme") != r.get("theme")
                or state.get("layoutViewport") != expected
                or state.get("devicePixelRatio") != zoom / 100
            ):
                errors.append(
                    f"actual theme/zoom mismatch: {m.get('capture_id')}/{d.get('uid')}"
                )
    # Row expansion belongs to the profile and does not change selected inputs.
    contexts = set()
    for m in manifests:
        context = dict(m.get("capture_context", {}))
        context.pop("row_state", None)
        contexts.add(
            json.dumps(
                {
                    "source": m.get("source", {}).get("commit_sha"),
                    "context": context,
                    "base": m.get("base_url"),
                },
                sort_keys=True,
            )
        )
    if len(contexts) != 1:
        errors.append("source/runtime/time/variable context differs across profiles")
    required = {
        (w, h, theme, 100, "full")
        for w, h in ((1366, 768), (1440, 900), (1920, 1080))
        for theme in ("dark", "light")
    }
    required |= {
        (1366, 768, theme, zoom, "viewport")
        for theme in ("dark", "light")
        for zoom in (100, 200)
    }
    missing = sorted(required - profiles)
    return {
        "status": "PASS" if not missing and not errors else "NOT_PROVEN",
        "missing_profiles": missing,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    """Write an immutable assessment directory for explicit immutable manifests."""
    from scripts.ops.observability.grafana.capture_provenance import verify_capture

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifests", nargs="+", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    manifests = [json.loads(p.read_text(encoding="utf-8")) for p in args.manifests]
    assessments = [assess_manifest(m) for m in manifests]
    provenance = [verify_capture(p, repo_root=args.repo_root) for p in args.manifests]
    references = [
        {"file": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in args.manifests
    ]
    common = {
        "manifests": references,
        "provenance": provenance,
        "matrix": matrix_coverage(manifests),
    }
    outputs = {
        "reflow-results.json": {**common, "profiles": assessments},
        "contrast-measurements.json": {
            "manifests": references,
            "profiles": [
                {
                    "capture_id": m.get("capture_id"),
                    "dashboards": [
                        {
                            "uid": d.get("uid"),
                            "text": measurement_pairs(d, "text"),
                            "graphics": measurement_pairs(d, "graphics"),
                        }
                        for d in m.get("dashboards", [])
                    ],
                }
                for m in manifests
            ],
        },
        "accessibility-status.json": {
            **common,
            "status": "NOT_PROVEN",
            "profiles": assessments,
            "reason": "explicit state/series-cue review and unsupported graphics evidence remain required",
        },
    }
    for name, payload in outputs.items():
        (args.output_dir / name).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return 1 if any(p["status"] != "PASS" for p in provenance) else 0


if __name__ == "__main__":
    raise SystemExit(main())
