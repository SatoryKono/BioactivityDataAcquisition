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
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml


pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]

ROOT = Path(__file__).resolve().parents[4]
ZED_ROOT = ROOT / ".zed"
DEV_SCRIPTS = ROOT / "scripts" / "engineering" / "dev"
TEST_MATRIX = ROOT / "configs" / "quality" / "test_matrix.yaml"

VALID_SAVE = {"all", "current", "none"}
VALID_REVEAL = {"always", "never", "no_focus"}
VALID_HIDE = {"always", "never", "on_success"}

# Expensive / mutating tasks must not allow concurrent duplicate starts.
NON_CONCURRENT_LABEL_PREFIXES = (
    "Environment:",
    "Format:",
    "Check:",
    "Test:",
    "Coverage:",
    "Audit:",
    "Generate:",
)


def _load_json(relative_path: str) -> Any:
    """Load a tracked Zed JSON document."""
    return json.loads((ZED_ROOT / relative_path).read_text(encoding="utf-8"))


def _load_lane_module() -> dict[str, Any]:
    if str(DEV_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(DEV_SCRIPTS))
    return runpy.run_path(str(DEV_SCRIPTS / "zed_pytest_lane.py"))


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
    assert settings["format_on_save"] == "off"
    assert settings["tab_size"] == 4
    assert settings["file_scan_inclusions"] == []
    assert settings["redact_private_values"] is True
    assert python_settings["hard_tabs"] is False
    assert python_settings["tab_size"] == 4
    assert python_settings["format_on_save"] == "off"
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

    yaml_settings = settings["languages"]["YAML"]
    json_settings = settings["languages"]["JSON"]
    jsonc_settings = settings["languages"]["JSONC"]
    assert yaml_settings["tab_size"] == 2
    assert json_settings["tab_size"] == 2
    assert jsonc_settings["tab_size"] == 2
    assert yaml_settings["format_on_save"] == "on"
    assert json_settings["format_on_save"] == "on"


def test_zed_file_scan_exclusions_cover_local_caches_and_debug_exports() -> None:
    """Scan exclusions hide local-only/heavy surfaces without hiding all data/."""
    exclusions = set(_load_json("settings.json")["file_scan_exclusions"])
    for pattern in (
        "**/.venv-win",
        "**/.venv-wsl",
        "**/.cache",
        "**/.worktrees",
        "**/data/debug_exports",
        "**/reports/coverage",
    ):
        assert pattern in exclusions
    assert "**/data/**" not in exclusions
    assert "**/reports/**" not in exclusions


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
    permissions = agent["tool_permissions"]
    terminal_permissions = permissions["tools"]["terminal"]

    assert permissions["default"] == "confirm"
    assert terminal_permissions["default"] == "confirm"
    assert any(
        "\\.env" in rule["pattern"] for rule in terminal_permissions["always_confirm"]
    )
    deny_patterns = " ".join(
        rule["pattern"] for rule in terminal_permissions["always_deny"]
    )
    assert "Remove-Item" in deny_patterns
    assert "git\\s+clean" in deny_patterns or "git\\s+clean" in deny_patterns
    assert "reset\\s+--hard" in deny_patterns

    for tool_name in ("edit_file", "write_file", "delete_path", "move_path"):
        tool_cfg = permissions["tools"][tool_name]
        assert tool_cfg["default"] == "confirm"
        rules = tool_cfg["always_deny"]
        assert any("\\.env" in rule["pattern"] for rule in rules)
        assert any("pem|key|cert|crt" in rule["pattern"] for rule in rules)

    for read_tool in (
        "diagnostics",
        "fetch",
        "find_path",
        "grep",
        "list_directory",
        "read_file",
        "search_web",
    ):
        assert permissions["tools"][read_tool]["default"] == "allow"

    ask_profile = agent["profiles"]["bioetl-ask"]
    write_profile = agent["profiles"]["bioetl-write"]
    assert agent["default_profile"] == "bioetl-ask"
    assert ask_profile["tools"]["terminal"] is False
    assert ask_profile["tools"]["spawn_agent"] is False
    assert write_profile["tools"]["spawn_agent"] is False
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
    assert all(task["command"] == venv_python for task in tasks)
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

    required_labels = {
        "Environment: verify",
        "Test: current file",
        "Test: nearest symbol",
        "Test: smoke",
        "Test: unit-fast",
        "Test: architecture-fast",
        "Coverage: local estimate (85%)",
        "Check: architecture imports",
        "Check: MCP manifests",
        "Generate: MCP tracked manifests",
    }
    assert required_labels <= set(labels)

    # Marker expressions with spaces must not appear in task args: PowerShell -C
    # re-tokenizes them into bare paths (``and`` / ``not``), breaking pytest.
    for task in tasks:
        if task["label"].startswith("Test:") or task["label"].startswith("Coverage:"):
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

    architecture = next(
        task for task in tasks if task["label"] == "Test: architecture-fast"
    )
    assert architecture["args"] == [lane_script, "architecture-fast"]

    coverage = next(
        task for task in tasks if task["label"] == "Coverage: local estimate (85%)"
    )
    assert coverage["args"] == [lane_script, "coverage-local"]

    env_verify = next(task for task in tasks if task["label"] == "Environment: verify")
    assert env_verify["args"] == ["scripts/engineering/dev/zed_env_doctor.py"]

    arch = next(
        task for task in tasks if task["label"] == "Check: architecture imports"
    )
    assert arch["command"] == venv_python
    assert arch["args"] == ["scripts/engineering/dev/zed_lint_imports.py"]
    # Must not point import-linter at pyproject.toml (contracts live in .importlinter).
    assert "pyproject.toml" not in arch["args"]
    assert "lint-imports.exe" not in arch["command"]

    complexity = next(task for task in tasks if task["label"] == "Audit: complexity")
    assert complexity["command"] == venv_python
    assert complexity["args"] == ["scripts/engineering/dev/zed_xenon.py"]
    # Raw xenon without excludes is not the project gate (see exemption registry).
    assert "-m" not in complexity["args"]
    assert "xenon" not in complexity["args"]

    dead_code = next(task for task in tasks if task["label"] == "Audit: dead code")
    assert dead_code["command"] == venv_python
    assert dead_code["args"] == ["scripts/engineering/dev/zed_vulture.py"]
    # Bare vulture at conf 60 floods Pandera schema fields as false positives.
    assert "vulture" not in dead_code["args"]

    security = next(task for task in tasks if task["label"] == "Audit: security")
    assert security["command"] == venv_python
    assert security["args"] == [
        "scripts/engineering/dev/zed_run.py",
        "-m",
        "bandit",
        "-c",
        "pyproject.toml",
        "-r",
        "src/bioetl",
    ]
    # Bare ``bandit -r src/`` ignores [tool.bandit] skips and scans non-product trees.
    assert "src/" not in security["args"]

    type_check = next(task for task in tasks if task["label"] == "Check: types")
    assert type_check["command"] == venv_python
    assert type_check["args"] == [
        "scripts/engineering/dev/zed_run.py",
        "-m",
        "mypy",
        "--config-file",
        "pyproject.toml",
        "src/bioetl",
    ]
    # Full ``mypy src/`` pulls memory tooling; CI product gate is src/bioetl.
    assert type_check["args"][-1] == "src/bioetl"

    mcp_check = next(task for task in tasks if task["label"] == "Check: MCP manifests")
    assert "--check" in mcp_check["args"]
    mcp_gen = next(
        task for task in tasks if task["label"] == "Generate: MCP tracked manifests"
    )
    assert "--check" not in mcp_gen["args"]
    assert "setup_mcp.py" in mcp_gen["args"][0]

    serialized = json.dumps(tasks)
    assert "codex agent run" not in serialized
    assert "devin skill invoke" not in serialized
    assert '"import-linter"' not in serialized
    assert "zed_lint_imports.py" in serialized
    assert "zed_xenon.py" in serialized
    assert "zed_vulture.py" in serialized
    assert "zed_env_doctor.py" in serialized


def test_zed_task_save_reveal_and_concurrency_policy() -> None:
    """Every task has explicit save/reveal/hide/concurrency behavior."""
    tasks = _load_json("tasks.json")
    for task in tasks:
        label = task["label"]
        assert task.get("save") in VALID_SAVE, label
        assert task.get("reveal") in VALID_REVEAL, label
        assert task.get("hide") in VALID_HIDE, label
        assert task.get("allow_concurrent_runs") is False, label

        if label in {"Test: current file", "Test: nearest symbol"}:
            assert task["save"] == "current"
        elif label == "Environment: verify":
            assert task["save"] == "none"
        else:
            assert task["save"] == "all"

        if label.startswith(NON_CONCURRENT_LABEL_PREFIXES):
            assert task["allow_concurrent_runs"] is False

        # Fast checks hide on success and avoid focus thrash when successful.
        if label in {"Check: lint", "Check: MCP manifests", "Environment: verify"}:
            assert task["hide"] == "on_success"

        # Mutating / long / security-sensitive tasks keep output visible.
        if label.startswith(("Generate:", "Audit:", "Coverage:", "Format:")):
            assert task["reveal"] == "always"
            assert task["hide"] == "never" or label.startswith("Format:")


def test_zed_pytest_lanes_match_canonical_test_matrix() -> None:
    """Zed lane paths/markers stay parity-locked to test_matrix.yaml suites."""
    lane_module = _load_lane_module()
    specs = lane_module["canonical_lane_specs"]()
    matrix = yaml.safe_load(TEST_MATRIX.read_text(encoding="utf-8"))
    matrix_lanes = matrix["test_lanes"]["lanes"]

    expected_keys = {
        "smoke",
        "unit-fast",
        "architecture-fast",
        "integration-replay",
        "contracts",
        "security",
        "e2e-smoke",
    }
    assert expected_keys <= set(specs)

    for lane_key, membership in specs.items():
        suite_name = membership["suite_name"]
        canonical = matrix_lanes[suite_name]
        assert membership["paths"] == list(canonical["paths"]), lane_key
        assert membership["marker"] == canonical["marker_expression"], lane_key

        canonical_args = list(canonical.get("pytest_args") or [])
        canonical_ignores = [
            arg.split("=", 1)[1]
            for arg in canonical_args
            if isinstance(arg, str) and arg.startswith("--ignore=")
        ]
        assert membership["ignores"] == canonical_ignores, lane_key

        if suite_name == "integration-replay":
            assert membership["vcr_record_none"] is True
            assert (canonical.get("environment") or {}).get("VCR_RECORD_MODE") == "none"

    # Local coverage estimate must not claim coverage-verify authority.
    assert "coverage-local" not in lane_module["CANONICAL_SUITE_BY_LANE"]
    assert "coverage-verify" not in lane_module["CANONICAL_SUITE_BY_LANE"].values()


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


def test_zed_env_doctor_healthy_and_missing_module(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Doctor reports healthy envs and actionable missing-module diagnostics."""
    if str(DEV_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(DEV_SCRIPTS))
    from scripts.engineering.dev import zed_env_doctor as doctor

    # Healthy path under the real worktree / current interpreter.
    findings = doctor.diagnose(modules=("pytest",), repo_root=ROOT)
    # Interpreter may not be under .venv-win when pytest uses another path; filter.
    codes = {f.code for f in findings}
    assert "missing_module" not in codes

    # Missing module surfaces a recovery command without raising.
    missing = doctor.check_modules(("definitely_missing_module_xyz",))
    assert len(missing) == 1
    assert missing[0].code == "missing_module"
    assert "setup_env_windows.ps1" in missing[0].recovery
    report = doctor.format_report(missing)
    assert "definitely_missing_module_xyz" in report
    assert "ModuleNotFoundError" not in report

    # Missing interpreter path.
    empty_root = tmp_path / "empty"
    empty_root.mkdir()
    missing_venv = doctor.check_interpreter(repo_root=empty_root)
    assert missing_venv[0].code == "missing_venv"
    assert "setup_env_windows.ps1" in missing_venv[0].recovery


def test_zed_env_doctor_cli_exits_nonzero_on_missing_module(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """CLI exits non-zero with actionable text when a required import is absent."""
    if str(DEV_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(DEV_SCRIPTS))
    from scripts.engineering.dev import zed_env_doctor as doctor

    monkeypatch.setattr(
        doctor,
        "diagnose",
        lambda **_kwargs: [
            doctor.Finding(
                code="missing_module",
                message="Required package is not importable: import-linter (importlinter)",
                recovery=r"Refresh the editable install: .\scripts\engineering\dev\setup_env_windows.ps1",
            )
        ],
    )
    code = doctor.main(["--require", "importlinter"])
    captured = capsys.readouterr()
    assert code == 2
    assert "missing_module" in captured.err
    assert "setup_env_windows.ps1" in captured.err
