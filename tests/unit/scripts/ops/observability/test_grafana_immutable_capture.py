"""RF-001 negative controls for provisioned and immutable capture identity."""

from __future__ import annotations

import copy
import hashlib
import json
import struct
import zlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.ops.observability.grafana import capture_provenance as provenance

pytestmark = pytest.mark.unit


def test_only_root_database_fields_are_normalized() -> None:
    source = {
        "uid": "test",
        "id": None,
        "version": 1,
        "panels": [{"id": 4, "version": 1}],
    }
    provisioned = {**source, "id": 42, "version": 99}
    evidence = {"before": provisioned, "loaded": [provisioned], "after": provisioned}
    assert provenance.model_errors(source, evidence) == []
    changed = copy.deepcopy(evidence)
    changed["after"]["panels"] = [{"id": 5, "version": 1}]
    assert provenance.model_errors(source, changed)


@pytest.mark.parametrize("phase", ["before", "loaded", "after"])
def test_semantic_model_substitution_is_rejected(phase: str) -> None:
    source = {"uid": "test", "panels": [{"targets": [{"expr": "up"}]}]}
    evidence = {
        "before": copy.deepcopy(source),
        "loaded": [copy.deepcopy(source)],
        "after": copy.deepcopy(source),
    }
    target = evidence[phase][0] if phase == "loaded" else evidence[phase]
    target["panels"][0]["targets"][0]["expr"] = "vector(0)"
    assert provenance.model_errors(source, evidence)


def test_api_reads_without_browser_model_are_insufficient() -> None:
    assert provenance.model_errors(
        {"uid": "test"}, {"before": {}, "after": {}, "loaded": []}
    )


@pytest.fixture
def capture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    source_dir = tmp_path / "grafana/dashboards"
    source_dir.mkdir(parents=True)
    source = {"uid": "test", "id": None, "version": 1, "panels": []}
    raw = json.dumps(source).encode()
    (source_dir / "test.json").write_bytes(raw)
    monkeypatch.setattr(
        provenance.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(returncode=0, stdout=raw),
    )
    output = tmp_path / "capture"
    output.mkdir()

    def chunk(kind, data):
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data))
        )

    png_data = b"\x89PNG\r\n\x1a\n"
    png_data += chunk(b"IHDR", struct.pack(">IIBBBBB", 1366, 768, 8, 2, 0, 0, 0))
    png_data += chunk(b"IDAT", zlib.compress((b"\0" + b"\xff\xff\xff" * 1366) * 768))
    png_data += chunk(b"IEND", b"")
    (output / "test.png").write_bytes(png_data)
    png = (output / "test.png").read_bytes()
    identity = {
        "path": "grafana/dashboards/test.json",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "version": 1,
    }
    name = "render-manifest--full-set--test-capture.json"
    manifest = {
        "capture_id": "test-capture",
        "immutable_manifest": name,
        "manifest_kind": "full-set",
        "file_set": ["test.png"],
        "file_count": 1,
        "base_url": "http://localhost:3000",
        "requested": {
            "viewport": {"width": 1366, "height": 768},
            "theme": "dark",
            "browser_zoom": 100,
            "kiosk_mode": "off",
            "capture_surface": "viewport",
        },
        "capture_context": {
            "time_range": {"from": "1000", "to": "2000", "timezone": "UTC"},
            "variables": {"workflow": "", "pipeline": "", "run_type": "", "run_id": ""},
            "row_state": {"expand_collapsed_rows": False},
        },
        "expand_collapsed_rows": False,
        "source": {
            "commit_sha": "a" * 40,
            "working_tree_dirty": False,
            "dashboards": {"test": identity},
        },
        "dashboards": [
            {
                "uid": "test",
                "file": "test.png",
                "dashboardSource": identity,
                "provisionedModel": {
                    "before": source,
                    "loaded": [source],
                    "after": source,
                    "captureId": "test-capture",
                    "observedUrl": "http://localhost:3000/d/test/title?from=1000&to=2000&timezone=UTC&theme=dark",
                    "browserVersion": "123.0.0",
                },
                "actualTheme": "dark",
                "browserState": {
                    "requestedZoom": 100,
                    "cssZoom": "1",
                    "actualKiosk": "off",
                    "devicePixelRatio": 1,
                    "layoutViewport": {"width": 1366, "height": 768},
                    "physicalViewport": {"width": 1366, "height": 768},
                    "visibleGrafanaChrome": True,
                },
                "screenshotEvidence": {
                    "file": "test.png",
                    "sha256": hashlib.sha256(png).hexdigest(),
                    "bytes": len(png),
                    "width": 1366,
                    "height": 768,
                },
            }
        ],
    }
    path = output / name
    path.write_text(json.dumps(manifest))
    return tmp_path, path, manifest


def test_latest_pointer_cannot_select_or_change_acceptance(capture) -> None:
    root, path, _ = capture
    (path.parent / "render-manifest.json").write_text('{"another": "capture"}')
    assert provenance.verify_capture(path, repo_root=root)["status"] == "PASS"
    assert (
        provenance.verify_capture(path.parent / "render-manifest.json", repo_root=root)[
            "status"
        ]
        == "FAIL"
    )


@pytest.mark.parametrize(
    "mutation", ["png", "source", "occurrence", "subset", "missing", "provisioned"]
)
def test_substituted_evidence_never_passes(capture, mutation: str) -> None:
    root, path, manifest = capture
    if mutation == "png":
        (path.parent / "test.png").write_bytes(b"corrupt")
    elif mutation == "missing":
        (path.parent / "test.png").unlink()
    elif mutation == "source":
        manifest["dashboards"][0]["dashboardSource"]["sha256"] = "0" * 64
    elif mutation == "occurrence":
        manifest["dashboards"][0]["provisionedModel"]["captureId"] = "other"
    elif mutation == "provisioned":
        manifest["dashboards"][0]["provisionedModel"]["after"] = {"uid": "other"}
    else:
        manifest["dashboards"] = []
    path.write_text(json.dumps(manifest))
    assert provenance.verify_capture(path, repo_root=root)["status"] == "FAIL"


def test_git_line_endings_are_portable_but_source_content_is_bound(
    capture, monkeypatch
) -> None:
    root, path, manifest = capture
    source_path = root / "grafana/dashboards/test.json"
    lf = json.dumps(json.loads(source_path.read_bytes()), indent=2).encode() + b"\n"
    crlf = lf.replace(b"\n", b"\r\n")
    source_path.write_bytes(lf)
    manifest["dashboards"][0]["dashboardSource"]["sha256"] = hashlib.sha256(
        crlf
    ).hexdigest()
    monkeypatch.setattr(
        provenance.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(returncode=0, stdout=lf),
    )
    path.write_text(json.dumps(manifest), encoding="utf-8")
    assert provenance.verify_capture(path, repo_root=root)["status"] == "PASS"
    source_path.write_bytes(lf.replace(b'"panels": []', b'"panels": [{}]'))
    assert provenance.verify_capture(path, repo_root=root)["status"] == "FAIL"


@pytest.mark.parametrize("kind", ["critical", "tile", "page"])
def test_every_linked_capture_surface_is_hash_bound(capture, kind: str) -> None:
    root, path, manifest = capture
    dashboard = manifest["dashboards"][0]
    evidence = copy.deepcopy(dashboard["screenshotEvidence"])
    evidence["file"] = "closeup.png"
    (path.parent / "closeup.png").write_bytes((path.parent / "test.png").read_bytes())
    if kind == "critical":
        dashboard["criticalPanelScreenshots"] = [evidence]
    elif kind == "tile":
        dashboard["scrollCapture"] = {"tiles": [evidence]}
    else:
        dashboard["tablePagination"] = [{"pages": [evidence]}]
    path.write_text(json.dumps(manifest), encoding="utf-8")
    assert provenance.verify_capture(path, repo_root=root)["status"] == "PASS"
    (path.parent / "closeup.png").write_bytes(b"substituted")
    assert provenance.verify_capture(path, repo_root=root)["status"] == "FAIL"


def test_attachment_path_must_stay_within_pack(capture) -> None:
    root, path, manifest = capture
    evidence = copy.deepcopy(manifest["dashboards"][0]["screenshotEvidence"])
    evidence["file"] = "../outside.png"
    (path.parent.parent / "outside.png").write_bytes(
        (path.parent / "test.png").read_bytes()
    )
    assert provenance.attachment_errors(path.parent, evidence)


def test_windows_source_separators_preserve_resource_identity(capture):
    root, path, manifest = capture
    manifest["dashboards"][0]["dashboardSource"]["path"] = (
        "grafana\\dashboards\\test.json"
    )
    path.write_text(json.dumps(manifest), encoding="utf-8")
    assert provenance.verify_capture(path, repo_root=root)["status"] == "PASS"
    manifest["dashboards"][0]["dashboardSource"]["path"] = "grafana/other/test.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    assert provenance.verify_capture(path, repo_root=root)["status"] == "FAIL"


@pytest.mark.parametrize(
    "mutation",
    [
        "truncated_png",
        "url_time",
        "url_variable",
        "dsf",
        "css_viewport",
        "file_count",
        "file_set",
    ],
)
def test_context_and_rehashed_corruption_are_rejected(capture, mutation):
    root, path, manifest = capture
    dashboard = manifest["dashboards"][0]
    if mutation == "truncated_png":
        png_path = path.parent / "test.png"
        raw = png_path.read_bytes()[:24]
        png_path.write_bytes(raw)
        dashboard["screenshotEvidence"].update(
            sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw)
        )
    elif mutation == "url_time":
        dashboard["provisionedModel"]["observedUrl"] = dashboard["provisionedModel"][
            "observedUrl"
        ].replace("from=1000", "from=999")
    elif mutation == "url_variable":
        manifest["capture_context"]["variables"]["pipeline"] = "chembl_assay"
    elif mutation == "dsf":
        dashboard["browserState"]["devicePixelRatio"] = 2
    elif mutation == "css_viewport":
        dashboard["browserState"]["layoutViewport"]["width"] = 1000
    elif mutation == "file_count":
        manifest["file_count"] = 99
    else:
        manifest["file_set"] = ["other.png"]
    path.write_text(json.dumps(manifest))
    assert provenance.verify_capture(path, repo_root=root)["status"] == "FAIL"


def test_external_manifest_and_commit_pins_reject_self_consistent_replacement(capture):
    root, path, manifest = capture
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert (
        provenance.verify_capture(
            path, repo_root=root, expected_sha256=digest, expected_commit="a" * 40
        )["status"]
        == "PASS"
    )
    manifest["generated_at"] = "another occurrence"
    path.write_text(json.dumps(manifest))
    assert (
        provenance.verify_capture(path, repo_root=root, expected_sha256=digest)[
            "status"
        ]
        == "FAIL"
    )
    assert (
        provenance.verify_capture(path, repo_root=root, expected_commit="b" * 40)[
            "status"
        ]
        == "FAIL"
    )


def test_grafana_iso_rewrite_preserves_exact_time_bounds(capture):
    root, path, manifest = capture
    model = manifest["dashboards"][0]["provisionedModel"]
    model["observedUrl"] = model["observedUrl"].replace(
        "from=1000", "from=1970-01-01T00:00:01.000Z"
    )
    path.write_text(json.dumps(manifest))
    assert provenance.verify_capture(path, repo_root=root)["status"] == "PASS"
    model["observedUrl"] = model["observedUrl"].replace("01.000Z", "01.001Z")
    path.write_text(json.dumps(manifest))
    assert provenance.verify_capture(path, repo_root=root)["status"] == "FAIL"
