"""Repository-backed contracts for the project-local Zed configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]

ROOT = Path(__file__).resolve().parents[4]
ZED_ROOT = ROOT / ".zed"


def _load_json(relative_path: str) -> Any:
    """Load a tracked Zed JSON document."""
    return json.loads((ZED_ROOT / relative_path).read_text(encoding="utf-8"))


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

    runtime_servers = set(settings["context_servers"])
    enabled_servers = set(write_profile["context_servers"])
    assert runtime_servers == {"memory", "fetch", "deepwiki"}
    assert enabled_servers == runtime_servers
    assert "filesystem" not in runtime_servers


def test_zed_runtime_mcp_servers_are_a_generated_manifest_subset() -> None:
    """Native Zed MCP servers should stay within the generated manifest inventory."""
    settings_servers = set(_load_json("settings.json")["context_servers"])
    generated_servers = set(_load_json("mcp.json")["mcpServers"])

    assert settings_servers <= generated_servers
    assert settings_servers == {"memory", "fetch", "deepwiki"}


def test_zed_tasks_use_uv_and_contextual_python_runnable() -> None:
    """Project tasks should use uv and bind the Python runnable narrowly."""
    tasks = _load_json("tasks.json")
    labels = [task["label"] for task in tasks]

    assert len(labels) == len(set(labels))
    assert all(task["command"] == "uv" for task in tasks)
    assert all(task["cwd"] == "$ZED_WORKTREE_ROOT" for task in tasks)

    tagged = [task for task in tasks if "python-test" in task.get("tags", [])]
    assert [task["label"] for task in tagged] == ["Test: current file"]
    assert "$ZED_FILE" in tagged[0]["args"]
    assert "--no-cov" in tagged[0]["args"]
    assert tagged[0]["args"][:3] == ["run", "--active", "--no-sync"]
    assert tagged[0].get("env", {}).get("VCR_RECORD_MODE") == "none"
    assert tagged[0].get("env", {}).get("UV_PROJECT_ENVIRONMENT") == ".venv-win"

    assert all(task["args"][:3] == ["run", "--active", "--no-sync"] for task in tasks)

    required_test_labels = {
        "Test: current file",
        "Test: nearest symbol",
        "Test: smoke",
        "Test: unit-fast",
        "Test: architecture",
        "Test: coverage (gate 85%)",
    }
    assert required_test_labels <= set(labels)

    nearest = next(task for task in tasks if task["label"] == "Test: nearest symbol")
    assert "$ZED_SYMBOL" in nearest["args"]
    assert "-k" in nearest["args"]

    coverage = next(
        task for task in tasks if task["label"] == "Test: coverage (gate 85%)"
    )
    assert any(arg.startswith("--cov=") or arg == "--cov" for arg in coverage["args"])
    assert "--cov-fail-under=85" in coverage["args"]

    serialized = json.dumps(tasks)
    assert "codex agent run" not in serialized
    assert "devin skill invoke" not in serialized
    assert '"import-linter"' not in serialized
    assert "lint-imports" in serialized
    assert "pyproject.toml" in serialized


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
    assert terminal["env"]["UV_PROJECT_ENVIRONMENT"] == ".venv-win"
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
