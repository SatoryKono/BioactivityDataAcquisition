"""Verify an explicitly selected immutable capture, independently of layout."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import struct
import zlib
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse


def query_values_match(key: str, actual: list[str] | None, expected: list[str]) -> bool:
    """Grafana rewrites Unix milliseconds as equivalent ISO UTC timestamps."""
    if actual == expected:
        return True
    if (
        key not in {"from", "to"}
        or not actual
        or len(actual) != 1
        or len(expected) != 1
    ):
        return False
    try:
        parsed = datetime.fromisoformat(actual[0].replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return False
        delta = parsed - datetime(1970, 1, 1, tzinfo=UTC)
        microseconds = (
            delta.days * 86400 + delta.seconds
        ) * 1_000_000 + delta.microseconds
        return microseconds == int(expected[0]) * 1000
    except ValueError:
        return False


def png_structure_errors(raw: bytes) -> list[str]:
    """Check every chunk CRC and complete deflate stream, including IEND."""
    offset = 8
    kinds = []
    compressed = bytearray()
    while offset + 12 <= len(raw):
        length = int.from_bytes(raw[offset : offset + 4], "big")
        end = offset + length + 12
        if end > len(raw):
            return ["truncated PNG chunk"]
        kind = raw[offset + 4 : offset + 8]
        payload = raw[offset + 8 : end - 4]
        crc = int.from_bytes(raw[end - 4 : end], "big")
        if zlib.crc32(kind + payload) != crc:
            return ["PNG chunk CRC mismatch"]
        kinds.append(kind)
        if kind == b"IHDR" and length != 13:
            return ["invalid PNG IHDR length"]
        if kind == b"IDAT":
            compressed.extend(payload)
        offset = end
        if kind == b"IEND":
            break
    if not kinds or kinds[0] != b"IHDR" or kinds[-1] != b"IEND" or offset != len(raw):
        return ["incomplete PNG structure"]
    return png_pixel_errors(raw, bytes(compressed))


def png_pixel_errors(raw: bytes, compressed: bytes) -> list[str]:
    """Verify the complete decoded pixel stream matches its declared shape."""
    width, height, depth, color, compression, filtering, interlace = struct.unpack(
        ">IIBBBBB", raw[16:29]
    )
    # Chromium and the canonical stitcher emit non-interlaced 8-bit RGB/RGBA.
    # Other encodings remain unverified rather than receiving a header-only PASS.
    if depth != 8 or color not in {2, 6} or compression or filtering or interlace:
        return ["unsupported PNG pixel encoding"]
    stride = 1 + width * (3 if color == 2 else 4)
    try:
        decoder = zlib.decompressobj()
        decoded = decoder.decompress(compressed, stride * height + 1)
    except zlib.error:
        return ["corrupted PNG pixel stream"]
    if not width or not height or len(decoded) != stride * height:
        return ["PNG pixel dimensions mismatch"]
    if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        return ["incomplete PNG pixel stream"]
    if any(decoded[index] > 4 for index in range(0, len(decoded), stride)):
        return ["invalid PNG scanline filter"]
    return []


def browser_url_errors(manifest: dict, dashboard: dict) -> list[str]:
    """Bind the browser's actual URL to the fixed time and variable scope."""
    requested = manifest.get("requested", {})
    model = dashboard.get("provisionedModel", {})
    context = manifest["capture_context"]
    errors = []
    query = parse_qs(
        urlparse(model.get("observedUrl", "")).query, keep_blank_values=True
    )
    expected = {**context["time_range"], "theme": requested.get("theme")}
    expected.update(
        {f"var-{key}": value for key, value in context["variables"].items() if value}
    )
    for key, value in expected.items():
        if not query_values_match(key, query.get(key), [str(value)]):
            errors.append(f"browser URL context mismatch: {key}")
    errors.extend(fixed_time_errors(context["time_range"]))
    scope = parse_qs(manifest.get("scope_query", ""), keep_blank_values=True)
    for key, values in scope.items():
        if not query_values_match(key, query.get(key), values):
            errors.append(f"browser scope mismatch: {key}")
    expected_variables = {
        key for key in expected.keys() | scope.keys() if key.startswith("var-")
    }
    if unexpected_browser_variables(model, context, expected_variables, query):
        errors.append("browser variable set mismatch")
    return errors


def unexpected_browser_variables(
    model: dict, context: dict, expected: set[str], query: dict
) -> bool:
    """Reject unknown selectors and the reintroduction of explicitly empty ones."""
    # Grafana resolves dashboard-specific selectors (stage, adapter, etc.) and
    # appends them to the observed URL. They must be declared by the already
    # source-verified model. An explicitly empty capture selector stays absent.
    declared = {
        f"var-{item['name']}"
        for item in model.get("before", {}).get("templating", {}).get("list", [])
    }
    dedicated = {f"var-{key}" for key in context["variables"]}
    extra = {key for key in query if key.startswith("var-")} - expected
    return bool(extra - (declared - dedicated))


def fixed_time_errors(bounds: dict) -> list[str]:
    """Require increasing fixed millisecond bounds in the UTC timezone."""
    errors = []
    if bounds.get("timezone") != "UTC":
        errors.append("UTC acceptance timezone required")
    if not all(str(bounds.get(key, "")).isdigit() for key in ("from", "to")):
        errors.append("fixed UTC acceptance time range required")
    elif int(bounds["from"]) >= int(bounds["to"]):
        errors.append("invalid acceptance time range")
    return errors


def browser_scale_errors(requested: dict, state: dict) -> list[str]:
    """Bind both CSS dimensions and neutral root/visual scales to the viewport."""
    errors = []
    scale = state.get("devicePixelRatio")
    if (
        not isinstance(scale, (float, int))
        or scale != requested.get("browser_zoom", 0) / 100
    ):
        errors.append("device scale mismatch")
    else:
        for dimension in ("width", "height"):
            actual = state.get("layoutViewport", {}).get(dimension)
            if (
                not isinstance(actual, (float, int))
                or abs(actual * scale - requested["viewport"][dimension]) > 1
            ):
                errors.append(f"CSS viewport mismatch: {dimension}")
    if (
        state.get("cssZoom") not in {"1", "normal"}
        or state.get("visualViewportScale") != 1
    ):
        errors.append("non-neutral browser scale")
    if state.get("physicalViewport") != requested.get("viewport"):
        errors.append("physical viewport mismatch")
    return errors


def requested_viewport_valid(manifest: dict) -> bool:
    """Require a usable requested viewport before any numeric comparisons."""
    requested = manifest.get("requested")
    if not isinstance(requested, dict) or not isinstance(
        requested.get("viewport"), dict
    ):
        return False
    return all(
        isinstance(requested["viewport"].get(key), (float, int))
        and requested["viewport"][key] > 0
        for key in ("width", "height")
    )


def browser_context_errors(manifest: dict, dashboard: dict) -> list[str]:
    """Check time, variables, physical/CSS viewport, scale, theme and chrome."""
    from scripts.ops.observability.grafana import (
        check_grafana_dashboard_audit_preflight as preflight,
    )

    if not requested_viewport_valid(manifest):
        return ["invalid requested viewport"]
    context_error = preflight._validate_capture_context(manifest)
    if context_error:
        return [context_error]
    requested = manifest.get("requested", {})
    state = dashboard.get("browserState", {})
    model = dashboard.get("provisionedModel", {})
    context = manifest["capture_context"]
    errors = browser_url_errors(manifest, dashboard)
    error = preflight._browser_state_error(
        str(dashboard["uid"]),
        state,
        requested_zoom=requested.get("browser_zoom", 0),
        requested_kiosk=requested.get("kiosk_mode", ""),
    )
    if error:
        errors.append(error)
    errors.extend(browser_scale_errors(requested, state))
    if dashboard.get("actualTheme") != requested.get("theme"):
        errors.append("actual theme mismatch")
    if not model.get("browserVersion") or not isinstance(
        state.get("visibleGrafanaChrome"), bool
    ):
        errors.append("missing browser version/chrome context")
    elif state.get("actualKiosk") == "full" and state["visibleGrafanaChrome"]:
        errors.append("visible browser chrome in full kiosk")
    if context["row_state"]["expand_collapsed_rows"] != manifest.get(
        "expand_collapsed_rows"
    ):
        errors.append("row state mismatch")
    return errors


def normalized_model(model: dict) -> dict:
    """Ignore only Grafana's root database identity and provisioning revision."""
    return {key: value for key, value in model.items() if key not in {"id", "version"}}


def model_errors(source: dict, evidence: object) -> list[str]:
    """Require the browser-loaded model and both bracketing reads to match."""
    if not isinstance(evidence, dict):
        return ["missing provisioned model evidence"]
    loaded = evidence.get("loaded")
    if not isinstance(loaded, list) or not loaded:
        return ["missing browser-loaded model"]
    errors = []
    for label, model in [
        ("before", evidence.get("before")),
        *[("loaded", value) for value in loaded],
        ("after", evidence.get("after")),
    ]:
        if not isinstance(model, dict) or normalized_model(model) != normalized_model(
            source
        ):
            errors.append(f"{label} provisioned model differs from source")
    return errors


def attachment_errors(root: Path, evidence: object) -> list[str]:
    """Verify a referenced PNG without allowing a path outside its capture pack."""
    if not isinstance(evidence, dict):
        return ["invalid PNG attachment metadata"]
    name = evidence.get("file")
    if not isinstance(name, str) or not name:
        return ["missing PNG attachment path"]
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        return [f"PNG attachment escapes capture pack: {name}"]
    if not path.is_file():
        return [f"missing PNG attachment: {name}"]
    raw = path.read_bytes()
    if len(raw) < 24 or raw[:8] != b"\x89PNG\r\n\x1a\n":
        return [f"invalid PNG attachment: {name}"]
    structure_errors = png_structure_errors(raw)
    if structure_errors:
        return [f"{name}: {error}" for error in structure_errors]
    width, height = struct.unpack(">II", raw[16:24])
    expected = (hashlib.sha256(raw).hexdigest(), len(raw), width, height)
    actual = tuple(evidence.get(key) for key in ("sha256", "bytes", "width", "height"))
    return (
        []
        if expected == actual
        else [f"PNG attachment digest/dimensions mismatch: {name}"]
    )


def dashboard_attachment_errors(root: Path, dashboard: dict) -> list[str]:
    """Bind critical closeups, original full-capture tiles and pagination pages."""
    attachments = list(dashboard.get("criticalPanelScreenshots", []))
    attachments.extend(dashboard.get("scrollCapture", {}).get("tiles", []))
    for table in dashboard.get("tablePagination", []):
        attachments.extend(table.get("pages", []))
    for control in dashboard.get("seriesControls", []):
        attachments.extend(control.get("entries", []))
    return [
        error for evidence in attachments for error in attachment_errors(root, evidence)
    ]


def browser_resource_errors(manifest: dict, dashboard: dict) -> list[str]:
    """Bind the observed browser resource to this UID, origin and occurrence."""
    errors = []
    model = dashboard.get("provisionedModel") or {}
    if model.get("captureId") != manifest.get("capture_id", ""):
        errors.append("model occurrence mismatch")
    observed = urlparse(model.get("observedUrl", ""))
    base = urlparse(manifest.get("base_url", ""))
    if (observed.scheme, observed.netloc) != (
        base.scheme,
        base.netloc,
    ) or not observed.path.startswith(f"/d/{dashboard.get('uid')}/"):
        errors.append("observed browser resource mismatch")
    return errors


def collapsed_row_structure(dashboard: dict) -> tuple[list[dict], set[str]]:
    """Read collapsed rows and their child IDs from the source-verified model."""
    source = dashboard.get("provisionedModel", {}).get("before", {})
    rows = [
        panel
        for panel in source.get("panels", [])
        if panel.get("type") == "row" and panel.get("collapsed")
    ]
    children = {
        str(panel["id"])
        for row in rows
        for panel in row.get("panels", [])
        if panel.get("type") != "row"
    }
    return rows, children


def observed_row_errors(manifest: dict, dashboard: dict) -> list[str]:
    """Cross-check requested row expansion with clicks and observed panel inventory."""
    rows, children = collapsed_row_structure(dashboard)
    if not rows:
        return []
    geometry = dashboard.get("layoutGeometry", {}).get("panelGeometry")
    if not isinstance(geometry, dict):
        return ["missing observed row panel inventory"]
    expansion = dashboard.get("rowExpansion", [])
    if not isinstance(expansion, list) or not all(
        isinstance(row, dict) for row in expansion
    ):
        return ["invalid observed row expansion"]
    if manifest.get("expand_collapsed_rows"):
        return expanded_row_errors(rows, expansion, children, set(geometry))
    if children.intersection(geometry) or any(row.get("clicked") for row in expansion):
        return ["observed rows contradict collapsed capture"]
    return []


def expanded_row_errors(
    rows: list[dict], expansion: list[dict], children: set[str], observed: set[str]
) -> list[str]:
    """Require every collapsed source row to open and expose its child panels."""
    errors = []
    if sorted(row["title"] for row in rows) != sorted(
        str(row.get("title", "")) for row in expansion
    ) or not all(row.get("clicked") is True for row in expansion):
        errors.append("observed row expansion is incomplete")
    if not children.issubset(observed):
        errors.append("expanded row child panels missing from browser inventory")
    return errors


def _dashboard_errors(
    manifest_path: Path, repo_root: Path, path: Path, dashboard: dict, manifest: dict
) -> list[str]:
    from scripts.ops.observability.grafana import (
        check_grafana_dashboard_audit_preflight as preflight,
    )

    if not requested_viewport_valid(manifest):
        return ["invalid requested viewport"]
    source = manifest.get("source", {})
    commit = source.get("commit_sha", "")
    uid = dashboard.get("uid")
    item_errors = []
    current = path.read_bytes()
    # Git checkouts may materialize LF or CRLF; no other source bytes
    # are normalized. The claimed commit is checked independently below.
    lf = current.replace(b"\r\n", b"\n")
    source_digests = {
        hashlib.sha256(raw).hexdigest()
        for raw in (current, lf, lf.replace(b"\n", b"\r\n"))
    }
    identity = dashboard.get("dashboardSource", {})
    if (
        identity.get("sha256") not in source_digests
        or source.get("dashboards", {}).get(uid) != identity
    ):
        item_errors.append("source digest mismatch")
    if re.fullmatch(r"[0-9a-f]{40}", commit):
        committed = subprocess.run(
            ["git", "show", f"{commit}:grafana/dashboards/{path.name}"],
            cwd=repo_root,
            capture_output=True,
            check=False,
            timeout=15,
        )
        if committed.returncode or committed.stdout.replace(
            b"\r\n", b"\n"
        ) != current.replace(b"\r\n", b"\n"):
            item_errors.append("source is not the claimed committed JSON")
    item_errors.extend(
        model_errors(json.loads(current), dashboard.get("provisionedModel"))
    )
    if (
        str(identity.get("path", "")).replace("\\", "/")
        != f"grafana/dashboards/{path.name}"
    ):
        item_errors.append("source path mismatch")
    item_errors.extend(browser_resource_errors(manifest, dashboard))
    if dashboard.get("file") != f"{uid}.png":
        item_errors.append("PNG resource mismatch")
    else:
        png_error = preflight._validate_screenshot_evidence(
            uid,
            dashboard,
            requested_width=manifest["requested"]["viewport"]["width"],
            screenshot_dir=manifest_path.parent,
        )
        if png_error:
            item_errors.append(png_error)
    item_errors.extend(dashboard_attachment_errors(manifest_path.parent, dashboard))
    item_errors.extend(
        attachment_errors(manifest_path.parent, dashboard.get("screenshotEvidence", {}))
    )
    item_errors.extend(browser_context_errors(manifest, dashboard))
    item_errors.extend(observed_row_errors(manifest, dashboard))
    return item_errors


def manifest_identity_errors(
    manifest_path: Path,
    manifest: dict,
    raw: bytes,
    expected_sha256: str | None,
    expected_commit: str | None,
) -> list[str]:
    """Require an immutable full-set identity and external pins when supplied."""
    errors: list[str] = []
    if (
        expected_sha256 is not None
        and hashlib.sha256(raw).hexdigest() != expected_sha256
    ):
        errors.append("pinned immutable manifest SHA mismatch")
    capture_id = manifest.get("capture_id", "")
    expected_name = f"render-manifest--full-set--{capture_id}.json"
    if not isinstance(capture_id, str) or not re.fullmatch(
        r"[A-Za-z0-9._-]+", capture_id
    ):
        errors.append("missing or invalid capture ID")
    if (
        manifest_path.name != expected_name
        or manifest.get("immutable_manifest") != expected_name
        or manifest.get("manifest_kind") != "full-set"
    ):
        errors.append("explicit immutable full-set manifest required")
    source = manifest.get("source", {})
    commit = source.get("commit_sha", "")
    if expected_commit is not None and commit != expected_commit:
        errors.append("pinned source commit mismatch")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        errors.append("missing committed source")
    if source.get("working_tree_dirty") is not False:
        errors.append("source working tree was not clean")
    return errors


def verify_capture(
    manifest_path: Path,
    *,
    repo_root: Path,
    expected_sha256: str | None = None,
    expected_commit: str | None = None,
    manifest_bytes: bytes | None = None,
) -> dict:
    """Verify a file or one caller-held byte snapshot shared with scoped assessment."""
    raw = manifest_path.read_bytes() if manifest_bytes is None else manifest_bytes
    manifest = json.loads(raw)
    errors = manifest_identity_errors(
        manifest_path, manifest, raw, expected_sha256, expected_commit
    )
    expected = {
        json.loads(p.read_text(encoding="utf-8"))["uid"]: p
        for p in (repo_root / "grafana/dashboards").glob("*.json")
    }
    dashboards = manifest.get("dashboards", [])
    if not expected:
        errors.append("missing shipped dashboard roster")
    if sorted(d.get("uid", "") for d in dashboards) != sorted(expected):
        errors.append("full-set UID coverage mismatch")
    if manifest.get("file_set") != sorted(f"{uid}.png" for uid in expected):
        errors.append("full-set file_set mismatch")
    if manifest.get("file_count") != len(expected):
        errors.append("full-set file_count mismatch")
    results = []
    for dashboard in dashboards:
        uid = dashboard.get("uid")
        path = expected.get(uid)
        if path is None:
            errors.append(f"unexpected UID: {uid}")
            continue
        item_errors = _dashboard_errors(
            manifest_path, repo_root, path, dashboard, manifest
        )
        results.append(
            {
                "uid": uid,
                "status": "FAIL" if item_errors else "PASS",
                "errors": item_errors,
            }
        )
    return {
        "status": "PASS"
        if not errors and all(r["status"] == "PASS" for r in results)
        else "FAIL",
        "manifest": str(manifest_path),
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "capture_id": manifest.get("capture_id", ""),
        "errors": errors,
        "dashboards": results,
        "scope": "provenance only; layout and accessibility are separate verdicts",
    }
