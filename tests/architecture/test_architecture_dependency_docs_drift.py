"""Architecture tests for dependency-map docs-as-code drift guardrails."""

from __future__ import annotations

import pytest

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import runpy
import sys


pytestmark = pytest.mark.architecture


def test_dependency_map_script_exists() -> None:
    script = Path("scripts/engineering/qa/generate_architecture_dependency_map.py")
    assert script.exists(), "Missing dependency map generator script"


def test_mkdocs_nav_includes_dependency_map() -> None:
    mkdocs = Path("mkdocs.yml").read_text(encoding="utf-8")
    assert "02-architecture/generated/module-dependency-map.md" in mkdocs


def test_docs_workflow_checks_dependency_map_drift() -> None:
    workflow = Path(".github/workflows/docs.yml").read_text(encoding="utf-8")
    assert "Check architecture dependency docs drift" in workflow
    assert (
        "scripts/engineering/qa/generate_architecture_dependency_map.py --check"
        in workflow
    )


def test_docs_workflow_autogen_dependency_map_on_pr() -> None:
    workflow = Path(".github/workflows/docs.yml").read_text(encoding="utf-8")
    assert "Regenerate architecture dependency docs (PR preflight)" in workflow
    assert (
        "scripts/engineering/qa/generate_architecture_dependency_map.py --update"
        in workflow
    )
    assert "Assert regenerated dependency docs are committed" in workflow


def test_tests_workflow_checks_dependency_map_drift() -> None:
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert "Check architecture dependency docs drift" in workflow
    assert (
        "scripts/engineering/qa/generate_architecture_dependency_map.py --check"
        in workflow
    )


def test_pre_commit_checks_dependency_map_drift() -> None:
    pre_commit = Path(".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert "check-architecture-dependency-map-drift" in pre_commit
    assert (
        "scripts/engineering/qa/generate_architecture_dependency_map.py --check"
        in pre_commit
    )


def test_nightly_workflow_regenerates_dependency_map() -> None:
    workflow_path = Path(".github/workflows/architecture-docs-nightly.yml")
    assert workflow_path.exists(), "Missing nightly architecture docs workflow"

    workflow = workflow_path.read_text(encoding="utf-8")
    assert "schedule:" in workflow
    assert 'cron: "15 2 * * *"' in workflow
    assert "workflow_dispatch:" in workflow
    assert "Regenerate architecture dependency map" in workflow
    assert (
        "scripts/engineering/qa/generate_architecture_dependency_map.py --update"
        in workflow
    )
    assert "Upload architecture docs artifacts" in workflow
    assert "architecture-dependency-map-nightly" in workflow


def test_dependency_map_drift_check_passes_current_repo(
    monkeypatch,
) -> None:
    # Skip on WSL and Windows due to filesystem performance causing dependency map generation timeout

    if sys.platform.startswith("win"):
        pytest.skip("Skipped on Windows due to filesystem performance")
    try:
        with open("/proc/version") as f:
            if "microsoft" in f.read().lower():
                pytest.skip("Skipped on WSL due to filesystem performance")
    except OSError:
        pass

    script_globals = runpy.run_path(
        "scripts/engineering/qa/generate_architecture_dependency_map.py",
        run_name="bioetl_architecture_dependency_map_test",
    )
    main = script_globals["main"]
    stdout = io.StringIO()
    stderr = io.StringIO()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate_architecture_dependency_map.py",
            "--check",
        ],
    )
    with redirect_stdout(stdout), redirect_stderr(stderr):
        result = main()

    assert result == 0, (
        "Dependency-map artifact drift check failed.\n"
        f"stdout:\n{stdout.getvalue()}\n"
        f"stderr:\n{stderr.getvalue()}\n"
    )


def test_dependency_map_check_explains_source_fingerprint_only_drift(
    tmp_path,
    capsys,
) -> None:
    script_globals = runpy.run_path(
        "scripts/engineering/qa/generate_architecture_dependency_map.py",
        run_name="bioetl_architecture_dependency_map_test",
    )
    check_file_sync = script_globals["_check_file_sync"]
    artifact_path = tmp_path / "module-dependency-map.json"
    actual = {
        "summary": {
            "scanned_modules": 1,
            "total_internal_imports": 0,
            "layer_edges": 0,
            "cross_layer_group_edges": 0,
            "cross_layer_group_edges_total": 0,
            "violations": 0,
            "source_fingerprint": "old",
        },
        "layer_edges": [],
        "cross_layer_group_edges": [],
        "violations": [],
    }
    expected = {
        **actual,
        "summary": {
            **actual["summary"],
            "source_fingerprint": "new",
        },
    }
    artifact_path.write_text(json.dumps(actual, indent=2) + "\n", encoding="utf-8")

    assert not check_file_sync(
        artifact_path,
        json.dumps(expected, indent=2) + "\n",
    )

    stdout = capsys.readouterr().out
    assert "source fingerprint mismatch" in stdout
    assert "actual='old'" in stdout
    assert "expected='new'" in stdout
    assert "topology content matches" in stdout


def test_dependency_map_generated_markdown_uses_canonical_generator_path() -> None:
    markdown = Path(
        "docs/02-architecture/generated/module-dependency-map.md"
    ).read_text(encoding="utf-8")
    assert (
        "scripts/engineering/qa/generate_architecture_dependency_map.py" in markdown
    ), "Generated dependency-map markdown should point to the canonical generator"


def test_dependency_map_generated_markdown_declares_scope_boundary() -> None:
    markdown = Path(
        "docs/02-architecture/generated/module-dependency-map.md"
    ).read_text(encoding="utf-8")
    assert "layer-policy and coarse topology snapshot only" in markdown, (
        "Generated dependency-map markdown must declare that it is a policy/"
        "topology snapshot, not a general architecture health score."
    )
    assert "not a hotspot, duplication, size, or churn scorecard" in markdown, (
        "Generated dependency-map markdown must keep the boundary between "
        "blocking import-policy drift and separate hotspot metrics."
    )
