# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture guardrails for full pytest capability bootstrap."""

from __future__ import annotations

import pytest

import tomllib
from pathlib import Path


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "pyproject.toml"
RUN_PYTEST_SH = ROOT / "scripts" / "engineering" / "dev" / "run_pytest.sh"
SETUP_PLUGINS_SH = ROOT / "scripts" / "ops" / "launchers" / "codex" / "setup_plugins.sh"


def _optional_dependencies() -> dict[str, list[str]]:
    with PYPROJECT.open("rb") as file_handle:
        payload = tomllib.load(file_handle)
    return payload["project"]["optional-dependencies"]


def _normalised_distribution_names(entries: list[str]) -> set[str]:
    names: set[str] = set()
    for entry in entries:
        candidate = entry.split(";", 1)[0].strip()
        for token in (">=", "==", "~=", "<=", "!=", "<", ">"):
            candidate = candidate.split(token, 1)[0]
        candidate = candidate.split("[", 1)[0].strip()
        if candidate:
            names.add(candidate)
    return names


def test_pyproject_declares_full_test_capability_extra() -> None:
    optional = _optional_dependencies()

    assert "tests_full" in optional
    names = _normalised_distribution_names(optional["tests_full"])

    assert {
        "pytest-benchmark",
        "import-linter",
        "radon",
        "vulture",
    }.issubset(names)


def test_setup_plugins_installs_full_test_capability_extra() -> None:
    content = SETUP_PLUGINS_SH.read_text(encoding="utf-8")

    assert "--extra tests_full" in content
    assert ".[dev,tests,tests_full,tracing]" in content
    assert "BIOETL_REQUIRE_TEST_CAPABILITIES" in content


def test_setup_plugins_propagates_python_probe_failures() -> None:
    content = SETUP_PLUGINS_SH.read_text(encoding="utf-8")
    run_python_body = content.split("run_python() {", 1)[1].split("\n}", 1)[0]

    assert "return 0" not in run_python_body


def test_run_pytest_wrapper_escalates_to_full_capabilities_for_optional_surfaces() -> (
    None
):
    content = RUN_PYTEST_SH.read_text(encoding="utf-8")

    assert "_needs_full_test_capabilities_for_selection()" in content
    assert (
        'export BIOETL_REQUIRE_TEST_CAPABILITIES="$REQUIRE_FULL_TEST_CAPABILITIES"'
        in content
    )
    for expected_path in (
        "tests/architecture",
        "tests/benchmarks",
        "tests/unit/application/core",
        "tests/unit/composition/bootstrap/runtime",
        "tests/unit/infrastructure/observability",
        "tests/unit/infrastructure/serialization",
    ):
        assert expected_path in content
