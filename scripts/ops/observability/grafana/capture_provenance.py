"""Verify an explicitly selected immutable capture, independently of layout."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import struct
from pathlib import Path
from urllib.parse import urlparse


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


def attachment_errors(root: Path, evidence: dict) -> list[str]:
    """Verify a referenced PNG without allowing a path outside its capture pack."""
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
    return [
        error for evidence in attachments for error in attachment_errors(root, evidence)
    ]


def verify_capture(manifest_path: Path, *, repo_root: Path) -> dict:
    """Fail closed on source, occurrence, PNG or observed model substitution."""
    from scripts.ops.observability.grafana import (
        check_grafana_dashboard_audit_preflight as preflight,
    )

    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    errors: list[str] = []
    capture_id = manifest.get("capture_id", "")
    expected_name = f"render-manifest--full-set--{capture_id}.json"
    if (
        manifest_path.name != expected_name
        or manifest.get("immutable_manifest") != expected_name
        or manifest.get("manifest_kind") != "full-set"
    ):
        errors.append("explicit immutable full-set manifest required")
    source = manifest.get("source", {})
    commit = source.get("commit_sha", "")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        errors.append("missing committed source")
    if source.get("working_tree_dirty") is not False:
        errors.append("source working tree was not clean")
    expected = {
        json.loads(p.read_text(encoding="utf-8"))["uid"]: p
        for p in (repo_root / "grafana/dashboards").glob("*.json")
    }
    dashboards = manifest.get("dashboards", [])
    if sorted(d.get("uid", "") for d in dashboards) != sorted(expected):
        errors.append("full-set UID coverage mismatch")
    results = []
    for dashboard in dashboards:
        uid = dashboard.get("uid")
        item_errors = []
        path = expected.get(uid)
        if path is None:
            errors.append(f"unexpected UID: {uid}")
            continue
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
        if identity.get("path") != f"grafana/dashboards/{path.name}":
            item_errors.append("source path mismatch")
        model = dashboard.get("provisionedModel") or {}
        if model.get("captureId") != capture_id:
            item_errors.append("model occurrence mismatch")
        observed = urlparse(model.get("observedUrl", ""))
        base = urlparse(manifest.get("base_url", ""))
        if (observed.scheme, observed.netloc) != (
            base.scheme,
            base.netloc,
        ) or not observed.path.startswith(f"/d/{uid}/"):
            item_errors.append("observed browser resource mismatch")
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
        "capture_id": capture_id,
        "errors": errors,
        "dashboards": results,
        "scope": "provenance only; layout and accessibility are separate verdicts",
    }
