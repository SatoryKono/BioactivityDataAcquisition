from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

from scripts.ai.codex import efficiency_baseline


def test_collect_baseline_is_bounded_and_secret_free(
    monkeypatch, tmp_path: Path
) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(efficiency_baseline.time, "monotonic", lambda: 1.0)

    report = efficiency_baseline.collect_baseline(
        root=tmp_path,
        runs=3,
        timeout_seconds=5,
    )

    assert report["schema_version"] == "bioetl-codex-efficiency-baseline-v1"
    assert report["policy"] == {
        "runs": 3,
        "timeout_seconds": 5,
        "captures_subprocess_output": False,
        "starts_optional_services": False,
    }
    assert len(calls) == 15
    assert all(kwargs["timeout"] == 5 for _, kwargs in calls)
    assert all(kwargs["stdout"] is subprocess.DEVNULL for _, kwargs in calls)
    assert all(kwargs["stderr"] is subprocess.DEVNULL for _, kwargs in calls)
    rendered = json.dumps(report)
    assert "OPENAI_API_KEY" not in rendered
    assert "GITHUB_TOKEN" not in rendered


def test_run_probe_reports_timeout_without_output(monkeypatch, tmp_path: Path) -> None:
    def fake_run(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(["codex"], timeout=1)

    monkeypatch.setattr(subprocess, "run", fake_run)
    report = efficiency_baseline._run_probe(
        "probe",
        ["codex", "--version"],
        root=tmp_path,
        timeout_seconds=1,
    )

    assert report["status"] == "timed_out"
    assert report["returncode"] is None
