"""Architecture gates for core port-adapter-factory coverage artifacts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
JSON_ARTIFACT = (
    PROJECT_ROOT / "reports" / "quality" / "port-adapter-factory-coverage.json"
)


def _payload() -> dict[str, object]:
    assert JSON_ARTIFACT.exists(), (
        "Missing port-adapter-factory coverage artifact; regenerate with "
        "python -m scripts.engineering.qa report-port-adapter-factory-coverage"
    )
    payload = json.loads(JSON_ARTIFACT.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _rows() -> list[dict[str, object]]:
    rows = _payload().get("rows")
    assert isinstance(rows, list)
    normalized: list[dict[str, object]] = []
    for row in rows:
        assert isinstance(row, dict)
        normalized.append(row)
    return normalized


@pytest.mark.architecture
def test_port_adapter_factory_coverage_has_no_unresolved_core_ports() -> None:
    payload = _payload()
    assert payload.get("scope") == "core_active_ports"
    assert payload.get("unresolved_count") == 0

    violations = [
        f"{row.get('port_name')}: {row.get('missing_surfaces')}"
        for row in _rows()
        if row.get("coverage_status") != "covered"
    ]
    assert not violations, "\n".join(violations)


@pytest.mark.architecture
def test_port_adapter_factory_coverage_paths_exist() -> None:
    violations: list[str] = []
    for row in _rows():
        port_name = row.get("port_name")
        for key in ("port_path",):
            path = row.get(key)
            if not isinstance(path, str) or not (PROJECT_ROOT / path).is_file():
                violations.append(f"{port_name}: missing {key} {path!r}")
        for key in ("adapter_paths", "factory_paths", "test_paths"):
            paths = row.get(key)
            if not isinstance(paths, list) or not paths:
                violations.append(f"{port_name}: missing {key}")
                continue
            for path in paths:
                if not isinstance(path, str) or not (PROJECT_ROOT / path).is_file():
                    violations.append(f"{port_name}: missing {key} path {path!r}")
    assert not violations, "\n".join(violations)


@pytest.mark.architecture
def test_port_adapter_factory_coverage_artifact_is_current() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa",
            "report-port-adapter-factory-coverage",
            "--check",
            "--json-out",
            str(JSON_ARTIFACT),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
