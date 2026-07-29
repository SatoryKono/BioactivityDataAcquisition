# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Repository-backed contracts for the project-local Zed configuration."""

from __future__ import annotations

import json
import runpy
from pathlib import Path
from typing import Any

import pytest


pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]

ROOT = Path(__file__).resolve().parents[4]
ZED_ROOT = ROOT / ".zed"


def _load_json(relative_path: str) -> Any:
    """Load a tracked Zed JSON document."""
    return json.loads((ZED_ROOT / relative_path).read_text(encoding="utf-8"))


def test_zed_xenon_adapts_ci_excludes_to_windows_paths() -> None:
    """Windows Xenon should receive patterns matching its backslash paths."""
    namespace = runpy.run_path(
        str(ROOT / "scripts" / "engineering" / "dev" / "zed_xenon.py")
    )
    assert (
        namespace["_platform_xenon_exclude"](
            "tests/*,src/memory/*",
            separator="\\",
        )
        == r"tests\*,src\memory\*"
    )


@pytest.mark.parametrize(
    "relative_path",
    [
        "settings.json",
        "tasks.json",
        "mcp.json",
        "snippets/python.json",
        "snippets/yaml.json",
    ],
)
def test_tracked_zed_json_is_valid(relative_path: str) -> None:
    """Every tracked Zed JSON surface should be parseable."""
    assert _load_json(relative_path) is not None


def test_zed_language_settings_delegate_to_project_sources_of_truth() -> None:
    """Zed should use current settings shapes and avoid duplicating tool config."""
    settings = _load_json("settings.json")
    python_settings = settings["languages"]["Python"]

    assert settings["autosave"] == "on_focus_change"
    assert "autosave_delay_ms" not in settings
    assert settings["file_scan_inclusions"] == []
    assert settings["redact_private_values"] is True
    assert python_settings["hard_tabs"] is False
    assert "indent_style" not in python_settings
    assert "source.fixAll.ruff" not in python_settings["code_actions_on_format"]
    assert settings["lsp"]["ruff"] == {
        "initialization_options": {
            "settings": {"configurationPreference": "filesystemFirst"}
        }
    }

    basedpyright = settings["lsp"]["basedpyright"]
    analysis = basedpyright["settings"]["basedpyright.analysis"]
    assert "initialization_options" not in basedpyright
    assert analysis["typeCheckingMode"] == "strict"
    assert analysis["diagnosticMode"] == "openFilesOnly"
    assert "stubPath" not in analysis
    assert "PYTHONPATH" not in settings["terminal"]["env"]


def test_zed_docker_compose_language_server_covers_repo_compose_files() -> None:
    """Compose manifests should use the dedicated Compose language service."""
    settings = _load_json("settings.json")
    compose_settings = settings["languages"]["Docker Compose"]
    compose_file_types = settings["file_types"]["Docker Compose"]

    assert settings["auto_install_extensions"]["docker-compose"] is True
    assert compose_settings["language_servers"] == ["docker-compose", "..."]
    assert compose_settings["formatter"] == "language_server"
    assert compose_settings["hard_tabs"] is False
    assert compose_settings["tab_size"] == 2
    assert "docker-compose*.yml" in compose_file_types
    assert "docker-compose*.yaml" in compose_file_types
    assert "scripts/ops/runtime/docker/compose/*.yml" in compose_file_types
    assert "scripts/ops/observability/*compose*.yml" in compose_file_types


def test_zed_agent_permissions_preserve_secret_boundaries() -> None:
    """Agent terminal and file tools should preserve the repository secret policy."""
    settings = _load_json("settings.json")
    agent = settings["agent"]
    terminal_permissions = agent["tool_permissions"]["tools"]["terminal"]

    assert terminal_permissions["default"] == "confirm"
    assert any(
        "\\.env" in rule["pattern"] for rule in terminal_permissions["always_confirm"]
    )
    for tool_name in ("edit_file", "write_file", "delete_path", "move_path"):
        rules = agent["tool_permissions"]["tools"][tool_name]["always_deny"]
        assert any("\\.env" in rule["pattern"] for rule in rules)
        assert any("pem|key|cert|crt" in rule["pattern"] for rule in rules)

    ask_profile = agent["profiles"]["bioetl-ask"]
    write_profile = agent["profiles"]["bioetl-write"]
    assert ask_profile["tools"]["terminal"] is False
    assert write_profile["enable_all_context_servers"] is False
    assert ask_profile["enable_all_context_servers"] is False

    # Agent must not attach MCP by default (prevents stdio thrash / multi-client
    # duplicates). MCP lives on the shared HTTP plane outside Zed Agent profiles.
    runtime_servers = set(settings.get("context_servers") or {})
    assert runtime_servers == set()
    assert set(ask_profile.get("context_servers") or {}) == set()
    assert set(write_profile.get("context_servers") or {}) == set()


def test_zed_runtime_mcp_servers_are_a_generated_manifest_subset() -> None:
    """Agent-attached MCP set is empty; inventory may still list shared servers."""
    settings_servers = set(_load_json("settings.json").get("context_servers") or {})
    generated_servers = set(_load_json("mcp.json")["mcpServers"])

    assert settings_servers <= generated_servers
    assert settings_servers == set()


def test_zed_tasks_use_venv_python_without_path_uv() -> None:
    """Tasks must call .venv-win tools directly so Zed PowerShell works without uv PATH."""
    tasks = _load_json("tasks.json")
    labels = [task["label"] for task in tasks]

    assert len(labels) == len(set(labels))
    assert all(task["cwd"] == "$ZED_WORKTREE_ROOT" for task in tasks)

    venv_python = "$ZED_WORKTREE_ROOT/.venv-win/Scripts/python.exe"
    venv_lint_imports = "$ZED_WORKTREE_ROOT/.venv-win/Scripts/lint-imports.exe"
    assert all(task["command"] in {venv_python, venv_lint_imports} for task in tasks)
    # No bare `uv` command — GUI PowerShell often has no uv on PATH.
    assert all(task["command"] != "uv" for task in tasks)
    assert "uv run" not in json.dumps(tasks)

    lane_script = "scripts/engineering/dev/zed_pytest_lane.py"
    tagged = [task for task in tasks if "python-test" in task.get("tags", [])]
    assert [task["label"] for task in tagged] == ["Test: current file"]
    assert tagged[0]["command"] == venv_python
    assert tagged[0]["args"][:2] == [lane_script, "file"]
    assert "$ZED_FILE" in tagged[0]["args"]
    assert tagged[0].get("env", {}).get("VCR_RECORD_MODE") == "none"

    required_test_labels = {
        "Test: current file",
        "Test: nearest symbol",
        "Test: smoke",
        "Test: unit-fast",
        "Test: architecture",
        "Test: coverage (gate 85%)",
    }
    assert required_test_labels <= set(labels)

    # Marker expressions with spaces must not appear in task args: PowerShell -C
    # re-tokenizes them into bare paths (``and`` / ``not``), breaking pytest.
    for task in tasks:
        if task["label"].startswith("Test:"):
            assert lane_script in task["args"]
            for arg in task["args"]:
                if arg.startswith("$"):
                    continue
                assert " and " not in arg
                assert " or " not in arg

    nearest = next(task for task in tasks if task["label"] == "Test: nearest symbol")
    assert nearest["args"][:2] == [lane_script, "nearest"]
    assert "$ZED_FILE" in nearest["args"]
    assert "$ZED_SYMBOL" in nearest["args"]

    architecture = next(task for task in tasks if task["label"] == "Test: architecture")
    assert architecture["args"] == [lane_script, "architecture"]

    coverage = next(
        task for task in tasks if task["label"] == "Test: coverage (gate 85%)"
    )
    assert coverage["args"] == [lane_script, "coverage"]

    arch = next(task for task in tasks if task["label"] == "Architecture compliance")
    assert arch["command"] == venv_python
    assert arch["args"] == ["scripts/engineering/dev/zed_lint_imports.py"]
    # Must not point import-linter at pyproject.toml (contracts live in .importlinter).
    assert "pyproject.toml" not in arch["args"]
    assert "lint-imports.exe" not in arch["command"]

    complexity = next(task for task in tasks if task["label"] == "Complexity check")
    assert complexity["command"] == venv_python
    assert complexity["args"] == ["scripts/engineering/dev/zed_xenon.py"]
    # Raw xenon without excludes is not the project gate (see exemption registry).
    assert "-m" not in complexity["args"]
    assert "xenon" not in complexity["args"]

    dead_code = next(task for task in tasks if task["label"] == "Dead code detection")
    assert dead_code["command"] == venv_python
    assert dead_code["args"] == ["scripts/engineering/dev/zed_vulture.py"]
    # Bare vulture at conf 60 floods Pandera schema fields as false positives.
    assert "vulture" not in dead_code["args"]

    security = next(task for task in tasks if task["label"] == "Security scan")
    assert security["command"] == venv_python
    assert security["args"] == [
        "-m",
        "bandit",
        "-c",
        "pyproject.toml",
        "-r",
        "src/bioetl",
    ]
    # Bare ``bandit -r src/`` ignores [tool.bandit] skips and scans non-product trees.
    assert "src/" not in security["args"]

    type_check = next(task for task in tasks if task["label"] == "Type check")
    assert type_check["command"] == venv_python
    assert type_check["args"] == [
        "-m",
        "mypy",
        "--config-file",
        "pyproject.toml",
        "src/bioetl",
    ]
    # Full ``mypy src/`` pulls memory tooling; CI product gate is src/bioetl.
    assert type_check["args"][-1] == "src/bioetl"

    serialized = json.dumps(tasks)
    assert "codex agent run" not in serialized
    assert "devin skill invoke" not in serialized
    assert '"import-linter"' not in serialized
    assert "zed_lint_imports.py" in serialized
    assert "zed_xenon.py" in serialized
    assert "zed_vulture.py" in serialized


def test_zed_terminal_prefers_windows_venv_and_offline_vcr() -> None:
    """Terminal should prefer dual-OS venvs and keep local VCR offline-safe."""
    settings = _load_json("settings.json")
    terminal = settings["terminal"]
    detect = terminal["detect_venv"]["on"]["directories"]

    assert detect[0] == ".venv-win"
    assert ".venv" in detect
    assert ".venv-wsl" in detect
    assert terminal["env"]["VCR_RECORD_MODE"] == "none"
    assert terminal["env"]["PYTHONDONTWRITEBYTECODE"] == "1"
    assert terminal["env"]["VIRTUAL_ENV"] == ".venv-win"
    assert settings["gutter"]["runnables"] is True


def test_zed_snippets_follow_current_bioetl_contracts() -> None:
    """Tracked snippets should avoid retired imports, typing, and storage shapes."""
    python_snippets = _load_json("snippets/python.json")
    yaml_snippets = _load_json("snippets/yaml.json")

    for snippet in python_snippets.values():
        assert "from __future__ import annotations" in snippet["body"]

    rendered_python = "\n".join(
        line for snippet in python_snippets.values() for line in snippet["body"]
    )
    rendered_yaml = "\n".join(
        line for snippet in yaml_snippets.values() for line in snippet["body"]
    )

    assert "bioetl.infrastructure.logging" not in rendered_python
    assert "bioetl.pipelines" not in rendered_python
    assert "Optional[" not in rendered_python
    assert "class Config:" not in rendered_python
    assert "data/silver" not in rendered_yaml
    assert "data/gold" not in rendered_yaml
    assert "format: parquet" not in rendered_yaml
    assert "pipeline_name:" in rendered_yaml
    assert "idempotency_contract: merge_upsert" in rendered_yaml
