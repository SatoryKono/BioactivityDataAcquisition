"""Repo-backed tests for Grafana rerender fallback behavior."""

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
