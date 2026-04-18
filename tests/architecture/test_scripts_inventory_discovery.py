"""Regression tests for scripts inventory discovery blind spots."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_inventory_module():
    root = _project_root()
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
    root = _project_root()

    svg2png_path = "/".join(["scripts", "diagrams", "svg2png.mjs"])

    rel_paths = {
        path.relative_to(root).as_posix() for path in module._iter_scripts(root)
    }

    assert svg2png_path in rel_paths
    assert not any(path.endswith(".sql") for path in rel_paths)


def test_discover_refs_normalizes_windows_path_separators(tmp_path: Path) -> None:
    """Windows-style script refs should resolve through path aliases."""
    module = _load_inventory_module()
    root = _project_root()
    targets = [
        root / "scripts" / "ops" / "launchers" / "codex" / "codex-exec.bat",
        root / "scripts" / "ops" / "launchers" / "codex" / "codex.bat",
        root / "scripts" / "ops" / "runtime" / "wsl" / "start-wsl-proxy.bat",
    ]
    original_iter_search_files = module._iter_search_files
    docs_dir = tmp_path / "docs" / "03-guides" / "development"
    docs_dir.mkdir(parents=True)
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
    root = _project_root()
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "cp1251"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/engineering/repo/check_scripts_inventory.py",
            "--json",
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout)
    assert payload["summary"]["total_scripts"] >= 1
