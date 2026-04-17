"""Architecture tests for dependency-map docs-as-code drift guardrails."""

from __future__ import annotations

import difflib
from pathlib import Path
import sys
from types import ModuleType


def _load_dep_map_module() -> ModuleType:
    script = Path(
        "scripts/engineering/qa/generate_architecture_dependency_map.py"
    ).resolve()
    module = ModuleType("dep_map_drift_gen")
    module.__file__ = str(script)
    module.__package__ = ""
    sys.modules["dep_map_drift_gen"] = module
    source = script.read_text(encoding="utf-8")
    exec(compile(source, str(script), "exec"), module.__dict__)
    return module


def _format_diff(label: str, actual: str, expected: str) -> str:
    diff_lines = list(
        difflib.unified_diff(
            actual.splitlines(),
            expected.splitlines(),
            fromfile=f"committed:{label}",
            tofile=f"generated:{label}",
            lineterm="",
        )
    )
    return "\n".join(diff_lines[:40])


def _strip_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return text
    return parts[1]


def test_dependency_map_script_exists() -> None:
    script = Path("scripts/engineering/qa/generate_architecture_dependency_map.py")
    assert script.exists(), "Missing dependency map generator script"


def test_dependency_map_wrapper_is_compatibility_only() -> None:
    wrapper = Path("scripts/generate_architecture_dependency_map.py").read_text(
        encoding="utf-8"
    )
    assert "Compatibility wrapper" in wrapper
    assert "scripts/engineering/qa/generate_architecture_dependency_map.py" in wrapper


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


def test_dependency_map_drift_check_passes_current_repo() -> None:
    mod = _load_dep_map_module()
    snapshot = mod.collect_dependency_snapshot(Path("src/bioetl"))
    expected_md = mod.build_markdown(snapshot)
    expected_json = mod.build_json(snapshot)

    md_path = Path("docs/02-architecture/generated/module-dependency-map.md")
    json_path = Path("docs/02-architecture/generated/module-dependency-map.json")
    actual_md = _strip_frontmatter(md_path.read_text(encoding="utf-8"))
    actual_json = json_path.read_text(encoding="utf-8")

    assert actual_md == expected_md, (
        "Dependency-map markdown artifact drifted from generator output.\n"
        f"{_format_diff(str(md_path), actual_md, expected_md)}"
    )

    assert actual_json == expected_json, (
        "Dependency-map JSON artifact drifted from generator output.\n"
        f"{_format_diff(str(json_path), actual_json, expected_json)}"
    )


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
