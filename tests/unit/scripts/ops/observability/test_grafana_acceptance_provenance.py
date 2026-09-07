"""Reject unbound acceptance windows and self-consistent false source hashes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ops.observability.grafana import (
    check_grafana_dashboard_audit_preflight as preflight,
)
from scripts.ops.observability.grafana import rerender_grafana_screenshots as rerender

pytestmark = pytest.mark.unit


def test_partial_render_preserves_success_and_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = rerender._parse_args(
        ["--output-dir", str(tmp_path), "--occurrence-id", "partial-test"]
    )
    records = [
        rerender.DashboardRecord(uid=uid, title=uid, url="/d/" + uid)
        for uid in ("bioetl-runtime", "bioetl-dq-v2", "bioetl-overview-v2")
    ]
    monkeypatch.setattr(rerender, "_load_dashboards", lambda _: records)
    visited = []

    def capture(cfg):
        uid = cfg.selected_uids[0]
        visited.append(uid)
        failed = uid == "bioetl-dq-v2"
        return int(failed), {
            "dashboards": [
                {
                    "uid": uid,
                    "file": uid + ".png",
                    "renderStatus": "error" if failed else "rendered",
                }
            ],
            "terminal_state_validation": {"status": "error" if failed else "ok"},
        }

    monkeypatch.setattr(rerender, "_run_playwright_with_retry", capture)
    assert rerender._run_playwright_fallback(config) == 1
    manifest = json.loads((tmp_path / "render-manifest.json").read_text())
    assert len(visited) == 3
    assert len(manifest["dashboards"]) == 3
    assert manifest["terminal_state_validation"]["status"] == "error"
    assert {d["uid"]: d["renderStatus"] for d in manifest["dashboards"]}[
        "bioetl-dq-v2"
    ] == "error"


def test_explicit_occurrence_cannot_overwrite_evidence(tmp_path: Path) -> None:
    image = tmp_path / "bioetl-runtime.png"
    image.write_bytes(b"original evidence")
    result = rerender.main(
        [
            "--output-dir",
            str(tmp_path),
            "--occurrence-id",
            "existing",
            "--password",
            "unit-test-only",
        ]
    )
    assert result == 1
    assert image.read_bytes() == b"original evidence"


def test_fixed_window_reaches_url_and_immutable_manifest(tmp_path: Path) -> None:
    config = rerender._parse_args(
        [
            "--range-from",
            "1788782400000",
            "--range-to",
            "1788804000000",
            "--output-dir",
            str(tmp_path),
            "--occurrence-id",
            "fixed-window-test",
        ]
    )
    query = rerender._scope_query_params(config)
    assert (query["from"], query["to"]) == ("1788782400000", "1788804000000")
    rerender._finalize_manifest(config, {"dashboards": []})
    manifest = json.loads((tmp_path / "render-manifest.json").read_text())
    assert manifest["capture_context"]["time_range"] == {
        "from": query["from"],
        "to": query["to"],
        "timezone": "UTC",
    }


@pytest.mark.parametrize(
    "args",
    [
        ["--range-from", "1788782400000"],
        ["--range-to", "1788804000000"],
        ["--range-from", "now-6h", "--range-to", "now"],
        ["--range-from", "10", "--range-to", "10"],
        ["--range-from", "20", "--range-to", "10"],
    ],
)
def test_fixed_window_rejects_partial_relative_or_reversed_bounds(
    args: list[str],
) -> None:
    with pytest.raises(SystemExit):
        rerender._parse_args(args)


def test_source_digest_is_compared_to_actual_checkout() -> None:
    source = rerender._dashboard_source_by_uid()["bioetl-runtime"]
    assert preflight._dashboard_source_error("bioetl-runtime", source, source) is None
    wrong = {**source, "sha256": "0" * 64}
    assert "does not match checkout" in preflight._dashboard_source_error(
        "bioetl-runtime", wrong, wrong
    )


def test_source_cannot_bind_another_dashboard() -> None:
    source = rerender._dashboard_source_by_uid()["bioetl-overview-v2"]
    assert "source path drift" in preflight._dashboard_source_error(
        "bioetl-runtime", source, source
    )
