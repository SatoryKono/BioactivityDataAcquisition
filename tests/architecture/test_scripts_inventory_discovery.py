"""Regression tests for scripts inventory discovery blind spots."""

from __future__ import annotations

import pytest

import importlib.util
import json
import sys
from pathlib import Path

from tests.helpers import repo_root, run_repo_python


pytestmark = pytest.mark.architecture

def _load_inventory_module():
    root = repo_root()
    module_path = (
        root / "scripts" / "engineering" / "repo" / "check_scripts_inventory.py"
    )
    spec = importlib.util.spec_from_file_location(
        "check_scripts_inventory_module", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_iter_scripts_includes_non_python_entrypoints_in_current_scope() -> None:
    """Inventory must cover non-Python utility entrypoints currently present in scope."""
    module = _load_inventory_module()
    root = repo_root()

    svg2png_path = "/".join(["scripts", "diagrams", "svg2png.mjs"])

    rel_paths = {
        path.relative_to(root).as_posix() for path in module._iter_scripts(root)
    }

    assert svg2png_path in rel_paths
    assert not any(path.endswith(".sql") for path in rel_paths)


def test_discover_refs_normalizes_windows_path_separators() -> None:
    """Windows-style script refs should resolve through path aliases."""
    module = _load_inventory_module()
    root = repo_root()
    targets = [
        root / "scripts" / "ops" / "launchers" / "codex" / "codex-exec.bat",
        root / "scripts" / "ops" / "launchers" / "codex" / "codex.bat",
        root / "scripts" / "ops" / "runtime" / "wsl" / "start-wsl-proxy.bat",
    ]
    original_iter_search_files = module._iter_search_files
    docs_dir = root / "docs" / "03-guides" / "development"
    docs_file = docs_dir / "codex-paths.md"
    docs_file.write_text(
        "\n".join(
            (
                r"scripts\codex-exec.bat",
                r"scripts\codex.bat",
                r"scripts\start-wsl-proxy.bat",
            )
        )
        + "\n",
        encoding="utf-8",
    )

    def _iter_only_codex_setup_docs(_: Path) -> list[Path]:
        return [docs_file]

    module._iter_search_files = _iter_only_codex_setup_docs
    try:
        refs = module._discover_refs(root, targets)
    finally:
        module._iter_search_files = original_iter_search_files
        docs_file.unlink(missing_ok=True)

    codex_exec_key = "/".join(["scripts", "codex-exec.bat"])
    codex_key = "/".join(["scripts", "codex.bat"])
    proxy_key = "/".join(["scripts", "start-wsl-proxy.bat"])

    assert any(
        item.path == "docs/03-guides/development/codex-paths.md"
        for item in refs[codex_exec_key]
    )
    assert any(
        item.path == "docs/03-guides/development/codex-paths.md"
        for item in refs[codex_key]
    )
    assert any(
        item.path == "docs/03-guides/development/codex-paths.md"
        for item in refs[proxy_key]
    )


def test_discover_refs_counts_pre_commit_local_hook_entrypoints() -> None:
    """Pre-commit local hook entries should mark wrappers and targets active."""
    module = _load_inventory_module()
    root = repo_root()
    targets = [
        root / "scripts" / "engineering" / "dev" / "run_project_python.py",
        root / "scripts" / "engineering" / "qa" / "vcr" / "check_root_vcr_cassettes.py",
        root
        / "scripts"
        / "engineering"
        / "qa"
        / "vcr"
        / "check_vcr_filename_policy.py",
    ]
    original_iter_search_files = module._iter_search_files

    def _iter_only_pre_commit(_: Path) -> list[Path]:
        return [root / ".pre-commit-config.yaml"]

    module._iter_search_files = _iter_only_pre_commit
    try:
        refs = module._discover_refs(root, targets)
    finally:
        module._iter_search_files = original_iter_search_files

    wrapper_refs = refs["scripts/engineering/dev/run_project_python.py"]
    placement_refs = refs["scripts/engineering/qa/vcr/check_root_vcr_cassettes.py"]
    naming_refs = refs["scripts/engineering/qa/vcr/check_vcr_filename_policy.py"]

    assert any(item.path == ".pre-commit-config.yaml" for item in wrapper_refs)
    assert any(item.path == ".pre-commit-config.yaml" for item in placement_refs)
    assert any(item.path == ".pre-commit-config.yaml" for item in naming_refs)
    assert {item.source_group for item in wrapper_refs} >= {"ci"}


def test_discover_refs_counts_unified_dispatcher_command_modules() -> None:
    """Dispatcher command maps should mark their command modules active."""
    module = _load_inventory_module()
    root = repo_root()
    target = root / "scripts" / "engineering" / "qa" / "check_docs_drift.py"
    dispatcher = root / "scripts" / "engineering" / "qa" / "__main__.py"
    original_iter_search_files = module._iter_search_files

    def _iter_only_qa_dispatcher(_: Path) -> list[Path]:
        return [dispatcher]

    module._iter_search_files = _iter_only_qa_dispatcher
    try:
        refs = module._discover_refs(root, [target])
    finally:
        module._iter_search_files = original_iter_search_files

    assert any(
        item.path == "scripts/engineering/qa/__main__.py"
        and item.source_group == "scripts"
        for item in refs["scripts/engineering/qa/check_docs_drift.py"]
    )


def test_agent_usage_includes_codex_agents_and_skills() -> None:
    """Agent usage should detect both skill wrappers and logical agent specs."""
    module = _load_inventory_module()

    refs = [
        module.RefEvidence(
            path=".codex/skills/technical-designer-mermaid/SKILL.md",
            line=1,
            text="/".join(["scripts", "diagrams", "lint_diagrams.py"]),
            source_group="skills",
        ),
        module.RefEvidence(
            path=".codex/agents/py-doc-bot.md",
            line=1,
            text="/".join(["scripts", "diagrams", "lint_diagrams.py"]),
            source_group="agents",
        ),
    ]

    assert module._agent_usage(refs) == [
        "py-doc-bot",
        "technical-designer-mermaid",
    ]


def test_inventory_json_output_is_ascii_safe_for_windows_codepages() -> None:
    """--json should not fail when stdout encoding cannot represent Unicode text."""
    root = repo_root()
    result = run_repo_python(
        "scripts/engineering/repo/check_scripts_inventory.py",
        "--json",
        cwd=root,
        env={"PYTHONIOENCODING": "cp1251"},
    )

    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout)
    assert payload["summary"]["total_scripts"] >= 1


def test_docs_generated_and_archive_surfaces_are_skipped_from_inventory_scan() -> None:
    """Inventory scan should stay out of bulky generated/archive doc surfaces."""
    module = _load_inventory_module()

    assert module._is_skipped_rel_path("docs/reports/generated/inventory.md")
    assert module._is_skipped_rel_path("docs/reports/evidence/pillar.yaml")
    assert module._is_skipped_rel_path(
        "docs/99-archive/root-status-artifacts/report.md"
    )
    assert module._is_skipped_rel_path("docs/02-architecture/generated/diagram.svg")
    assert module._is_skipped_rel_path("docs/plans/wip.md")
    assert not module._is_skipped_rel_path("docs/03-guides/script-management/README.md")
