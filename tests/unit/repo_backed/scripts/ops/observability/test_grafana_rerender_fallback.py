"""Repo-backed tests for Grafana rerender fallback behavior."""

import json
from pathlib import Path
from typing import Any
from urllib.error import URLError

import pytest

from scripts.ops.observability.grafana import (
    rerender_grafana_screenshots as rerender_subject,
)


pytestmark = pytest.mark.repo_backed


def test_rerender_falls_back_to_playwright_on_render_failure(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setenv("GF_SECURITY_ADMIN_PASSWORD", "changeme")
    monkeypatch.setattr(rerender_subject, "_load_dashboards", lambda *_: [])
    monkeypatch.setattr(
        rerender_subject,
        "_render_via_api",
        lambda *_: (_ for _ in ()).throw(URLError("timed out")),
    )
    monkeypatch.setattr(rerender_subject, "_run_playwright_fallback", lambda *_: 0)

    result = rerender_subject.main(
        ["--output-dir", str(tmp_path), "--fallback", "auto"]
    )
    assert result == 0


def test_rerender_auto_fallback_skips_frontend_probe_on_render_failure(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setenv("GF_SECURITY_ADMIN_PASSWORD", "changeme")
    monkeypatch.setattr(rerender_subject, "_load_dashboards", lambda *_: [])
    monkeypatch.setattr(
        rerender_subject,
        "_render_via_api",
        lambda *_: (_ for _ in ()).throw(URLError("timed out")),
    )
    monkeypatch.setattr(rerender_subject, "_run_playwright_fallback", lambda *_: 0)

    def fail_if_probed(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("frontend settings probe should be skipped")

    monkeypatch.setattr(rerender_subject, "_request_json", fail_if_probed)
    result = rerender_subject.main(
        ["--output-dir", str(tmp_path), "--fallback", "auto"]
    )
    assert result == 0


def test_rerender_playwright_fallback_splits_and_merges_multi_dashboard_runs(
    monkeypatch: Any, tmp_path: Path
) -> None:
    script_path = tmp_path / "rerender_grafana_screenshots.cjs"
    script_path.write_text("// noop\n", encoding="utf-8")
    calls: list[str] = []

    class _Result:
        returncode = 0

    monkeypatch.setattr(
        rerender_subject, "_playwright_script_path", lambda: script_path
    )
    monkeypatch.setattr(
        rerender_subject, "_resolve_node_executable", lambda: "/usr/bin/node"
    )
    monkeypatch.setattr(rerender_subject, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        rerender_subject,
        "_load_dashboards",
        lambda _config: [
            rerender_subject.DashboardRecord(
                uid="bioetl-provider-health-v2",
                url="/d/bioetl-provider-health-v2/3-provider-health",
                title="3. Provider Health",
            ),
            rerender_subject.DashboardRecord(
                uid="bioetl-runtime",
                url="/d/bioetl-runtime/2-runtime",
                title="2. Runtime",
            ),
        ],
    )

    def fake_run(command: list[str], **kwargs: object) -> _Result:
        env = kwargs["env"]
        assert isinstance(env, dict)
        uid = str(env["GRAFANA_SCREENSHOT_UIDS"])
        calls.append(uid)
        # Varied PNG-like payload keeps blank-screenshot validation meaningful.
        png = bytearray()
        png.extend(bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]))
        png.extend(bytes([0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52]))
        png.extend((1600).to_bytes(4, "big"))
        png.extend((2200).to_bytes(4, "big"))
        png.extend(bytes(range(256)) * 20)
        (tmp_path / f"{uid}.png").write_bytes(bytes(png))
        (tmp_path / "render-manifest.json").write_text(
            json.dumps(
                {
                    "engine": "playwright",
                    "terminal_state_validation": {"status": "ok"},
                    "dashboards": [
                        {
                            "uid": uid,
                            "title": uid,
                            "file": f"{uid}.png",
                            "renderedPanelCount": 1,
                            "renderStatus": "rendered",
                            "actualViewport": {"width": 1600, "height": 2200},
                            "actualTheme": "dark",
                            "screenshotEvidence": {
                                "file": f"{uid}.png",
                                "bytes": len(png),
                                "width": 1600,
                                "height": 2200,
                                "sha256": "test-digest",
                            },
                            "terminalStateValidation": {
                                "status": "ok",
                                "panelStates": [{"id": 1, "classification": "healthy"}],
                            },
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return _Result()

    monkeypatch.setattr(rerender_subject.subprocess, "run", fake_run)
    config = rerender_subject.RenderConfig(
        base_url="http://localhost:3000",
        username="admin",
        password="changeme",
        service_account_token="",
        output_dir=tmp_path,
        width=1600,
        height=2200,
        timeout_seconds=45.0,
        selected_uids=(),
        fallback="auto",
    )

    assert rerender_subject._run_playwright_fallback(config) == 0
    assert calls == ["bioetl-provider-health-v2", "bioetl-runtime"]
    merged = json.loads((tmp_path / "render-manifest.json").read_text())
    assert merged["engine"] == "playwright"
    assert [item["uid"] for item in merged["dashboards"]] == calls
    assert merged["requested"] == {
        "viewport": {"width": 1600, "height": 2200},
        "theme": "dark",
        "capture_surface": "full",
        "kiosk_mode": "off",
        "browser_zoom": 100,
    }
    assert merged["terminal_state_validation"]["status"] == "ok"


def test_rerender_resolves_node_from_repo_local_bin(
    monkeypatch: Any, tmp_path: Path
) -> None:
    node_path = tmp_path / "node_modules" / ".bin" / "node.exe"
    node_path.parent.mkdir(parents=True, exist_ok=True)
    node_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(rerender_subject.shutil, "which", lambda _name: None)
    monkeypatch.setattr(rerender_subject, "_repo_root", lambda: tmp_path)

    assert rerender_subject._resolve_node_executable() == str(node_path)
