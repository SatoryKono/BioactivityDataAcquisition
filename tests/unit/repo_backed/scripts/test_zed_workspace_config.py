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
"""Contracts for optional project-local Zed configuration."""

from __future__ import annotations

import json
import re
import runpy
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml


pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]

ROOT = Path(__file__).resolve().parents[4]
ZED_ROOT = ROOT / ".zed"
TEMPLATE_ROOT = ROOT / "configs" / "ide" / "zed"
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
    """Load a local Zed JSON document when this machine provides one."""
    path = ZED_ROOT / relative_path
    if not path.is_file():
        pytest.skip(f"Optional local Zed config is absent: {relative_path}")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(params=("template", "local"))
def project_config_root(request: pytest.FixtureRequest) -> Path:
    root = TEMPLATE_ROOT if request.param == "template" else ZED_ROOT
    if request.param == "local" and not (root / "settings.json").is_file():
        pytest.skip("Optional local Zed settings are absent")
    return root


def _project_json(root: Path, filename: str) -> Any:
    return json.loads((root / filename).read_text(encoding="utf-8"))


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
    windows_cli = namespace["_xenon_cli"](
        executable=r"C:\repo\.venv-win\Scripts\python.exe",
        platform="win32",
    )
    posix_cli = namespace["_xenon_cli"](
        executable="/repo/.venv/bin/python",
        platform="linux",
    )
    assert windows_cli.name == "xenon.exe"
    assert posix_cli.name == "xenon"
    source = (ROOT / "scripts" / "engineering" / "dev" / "zed_xenon.py").read_text(
        encoding="utf-8"
    )
    assert '"-m"' not in source


@pytest.mark.parametrize(
    "relative_path",
    [
        "settings.json",
        "tasks.json",
        "keymap.json",
        "mcp.json",
        "snippets/python.json",
        "snippets/yaml.json",
    ],
)
def test_present_zed_json_is_valid(relative_path: str) -> None:
    """Every present local Zed JSON surface should be parseable."""
    assert _load_json(relative_path) is not None


def test_zed_task_picker_shortcut_spawns_tasks() -> None:
    """The documented task shortcut should open the task picker."""
    keymap = _load_json("keymap.json")
    assert keymap["bindings"]["ctrl-shift-t"] == "task::Spawn"


def test_zed_language_settings_delegate_to_project_sources_of_truth(
    project_config_root: Path,
) -> None:
    """The base profile delegates tool policy, not personal save/format choices."""
    settings = _project_json(project_config_root, "settings.json")
    python_settings = settings["languages"]["Python"]
    assert "autosave_delay_ms" not in settings
    assert "indent_style" not in python_settings
    assert "source.fixAll.ruff" not in python_settings.get("code_actions_on_format", {})
    assert python_settings["language_servers"] == ["basedpyright", "ruff"]
    for server in ("basedpyright", "ruff"):
        assert "binary" not in settings.get("lsp", {}).get(server, {})
    assert settings["terminal"]["env"]["PYTHONPATH"] == ""
    assert "agent" not in settings, "User Agent policy is a separate opt-in template"
    assert "context_servers" not in settings
    assert (ROOT / ".editorconfig").is_file()
    assert (ROOT / "pyproject.toml").is_file()


def test_zed_file_scan_exclusions_cover_local_caches_and_debug_exports(
    project_config_root: Path,
) -> None:
    """Scan exclusions hide local-only/heavy surfaces without hiding all data/."""
    exclusions = set(
        _project_json(project_config_root, "settings.json")["file_scan_exclusions"]
    )
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
    if "Docker Compose" not in settings.get("languages", {}):
        pytest.skip(
            "Dedicated Compose IDE settings are optional in the base Zed profile"
        )
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
    """The opt-in user template retains secret guards; this is not runtime proof."""
    settings = _project_json(TEMPLATE_ROOT, "agent-settings.json")
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
    assert "git\\s+clean" in deny_patterns
    assert "reset\\s+--hard" in deny_patterns

    for tool_name in (
        "edit_file",
        "write_file",
        "delete_path",
        "move_path",
        "copy_path",
    ):
        tool_cfg = permissions["tools"][tool_name]
        assert tool_cfg["default"] == "confirm"
        rules = tool_cfg["always_deny"]
        assert any("\\.env" in rule["pattern"] for rule in rules)
        assert any("pem|key|cert|crt" in rule["pattern"] for rule in rules)

    for external_tool in ("fetch", "search_web", "skill"):
        assert permissions["tools"][external_tool]["default"] == "confirm"

    ask_profile = agent["profiles"]["bioetl-ask"]
    write_profile = agent["profiles"]["bioetl-write"]
    assert agent["default_profile"] == "bioetl-ask"
    for tool in (
        "terminal",
        "edit_file",
        "write_file",
        "delete_path",
        "move_path",
        "copy_path",
        "create_directory",
        "spawn_agent",
        "skill",
        "fetch",
        "search_web",
    ):
        assert ask_profile["tools"][tool] is False
    for tool in ("read_file", "grep", "find_path", "list_directory", "diagnostics"):
        assert ask_profile["tools"][tool] is True
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


@pytest.mark.parametrize(
    "tool",
    [
        "edit_file",
        "write_file",
        "delete_path",
        "move_path",
        "copy_path",
        "create_directory",
    ],
)
@pytest.mark.parametrize(
    "path",
    [
        ".env",
        ".env.local",
        "config/.env.production",
        r"D:\repo\.env",
        r"D:\repo\.env.local",
    ],
)
def test_zed_user_template_blocks_env_mutations(tool: str, path: str) -> None:
    settings = _project_json(TEMPLATE_ROOT, "agent-settings.json")
    rules = settings["agent"]["tool_permissions"]["tools"][tool]["always_deny"]
    assert any(re.search(rule["pattern"], path, re.IGNORECASE) for rule in rules)
    for harmless in ("src/environment.py", "docs/environment.md", "config/env.yaml"):
        assert not any(
            re.search(rule["pattern"], harmless, re.IGNORECASE) for rule in rules
        )


@pytest.mark.parametrize(
    "tool", ["edit_file", "write_file", "delete_path", "move_path", "copy_path"]
)
@pytest.mark.parametrize(
    "path", ["private.pem", "private.KEY", "server.cert", "server.crt"]
)
def test_zed_user_template_blocks_private_key_mutations(tool: str, path: str) -> None:
    settings = _project_json(TEMPLATE_ROOT, "agent-settings.json")
    rules = settings["agent"]["tool_permissions"]["tools"][tool]["always_deny"]
    assert any(re.search(rule["pattern"], path, re.IGNORECASE) for rule in rules)


@pytest.mark.parametrize(
    "command", ["Remove-Item data", "git clean -fd", "git reset --hard HEAD"]
)
def test_zed_user_template_blocks_destructive_terminal_commands(command: str) -> None:
    settings = _project_json(TEMPLATE_ROOT, "agent-settings.json")
    rules = settings["agent"]["tool_permissions"]["tools"]["terminal"]["always_deny"]
    assert any(re.search(rule["pattern"], command, re.IGNORECASE) for rule in rules)
    assert not any(
        re.search(rule["pattern"], "git status --short", re.IGNORECASE)
        for rule in rules
    )


def test_zed_runtime_mcp_servers_are_a_generated_manifest_subset() -> None:
    """Agent-attached MCP set is empty; inventory may still list shared servers."""
    settings_servers = set(_load_json("settings.json").get("context_servers") or {})
    generated_servers = set(_load_json("mcp.json")["mcpServers"])

    assert settings_servers <= generated_servers
    assert settings_servers == set()


def test_zed_tasks_use_venv_python_without_path_uv(project_config_root: Path) -> None:
    """The reviewed base catalog uses the checkout interpreter, never PATH uv."""
    tasks = _project_json(project_config_root, "tasks.json")
    labels = [task["label"] for task in tasks]

    assert len(labels) == len(set(labels))
    assert all(task["cwd"] == "$ZED_WORKTREE_ROOT" for task in tasks)

    venv_python = "$ZED_WORKTREE_ROOT/.venv-win/Scripts/python.exe"
    assert all(task["command"] == venv_python for task in tasks)
    # No bare `uv` command — GUI PowerShell often has no uv on PATH.
    assert all(task["command"] != "uv" for task in tasks)
    assert "uv run" not in json.dumps(tasks)

    project_label = "pytest: current test file (project settings)"
    quick_label = "pytest: current test file (quick; project addopts disabled)"
    tagged = [task for task in tasks if "python-test" in task.get("tags", [])]
    assert [task["label"] for task in tagged] == [project_label]
    assert tagged[0]["args"] == [
        "-m",
        "pytest",
        "-o",
        "cache_dir=.cache/pytest/windows",
        "$ZED_FILE",
    ]
    assert tagged[0].get("env", {}).get("VCR_RECORD_MODE") == "none"
    assert set(labels) == {
        "Python: active project interpreter",
        "Environment: verify",
        project_label,
        quick_label,
        "Ruff: check current file",
        "Ruff: check formatting of current file",
    }
    by_label = {task["label"]: task for task in tasks}
    assert by_label[quick_label]["args"] == [
        "-m",
        "pytest",
        "-q",
        "-o",
        "addopts=",
        "-o",
        "cache_dir=.cache/pytest/windows",
        "$ZED_FILE",
    ]
    assert by_label["Environment: verify"]["args"] == [
        "scripts/engineering/dev/zed_env_doctor.py"
    ]
    assert by_label["Ruff: check current file"]["args"] == [
        "-m",
        "ruff",
        "check",
        "$ZED_FILE",
    ]
    assert by_label["Ruff: check formatting of current file"]["args"] == [
        "-m",
        "ruff",
        "format",
        "--check",
        "$ZED_FILE",
    ]
    serialized = json.dumps(tasks)
    assert "codex agent run" not in serialized
    assert "devin skill invoke" not in serialized


def test_security_workflow_preserves_dependency_advisory_checks() -> None:
    """Security policy is independent of the optional IDE task catalog."""
    security_workflow = (ROOT / ".github" / "workflows" / "security.yml").read_text(
        encoding="utf-8"
    )
    assert "Do not restore --ignore-vuln for that advisory." in security_workflow
    assert "--ignore-vuln CVE-2026-3219" not in security_workflow
    assert "--ignore-vuln PYSEC-2026-3721" not in security_workflow


def test_zed_task_save_reveal_and_concurrency_policy(project_config_root: Path) -> None:
    """Current-file tasks save only that file; diagnostics do not save buffers."""
    tasks = _project_json(project_config_root, "tasks.json")
    for task in tasks:
        label = task["label"]
        assert task.get("save") in VALID_SAVE, label
        assert task.get("reveal") in VALID_REVEAL, label
        assert task.get("hide") in VALID_HIDE, label
        assert task["hide"] == "never", label
        assert task.get("allow_concurrent_runs") is False, label

        if label in {"Python: active project interpreter", "Environment: verify"}:
            assert task["save"] == "none"
        else:
            assert task["save"] == "current"
        assert task["reveal"] == "always", label

        if label.startswith(NON_CONCURRENT_LABEL_PREFIXES):
            assert task["allow_concurrent_runs"] is False

        # Mutating / long / security-sensitive tasks keep output visible.
        if label.startswith(("Generate:", "Audit:", "Coverage:", "Format:")):
            assert task["reveal"] == "always"
            assert task["hide"] == "never"


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
    for lane_key in ("coverage-local", "coverage"):
        coverage_args = lane_module["LANES"][lane_key]
        assert "--ignore=tests/unit/scripts" in coverage_args
        assert "--ignore=tests/unit/memory" in coverage_args
        assert "--ignore=tests/integration/memory" in coverage_args
        assert "--ignore=tests/integration" in coverage_args
        assert "--ignore=tests/security" in coverage_args
        assert "--ignore=tests/unit/repo_backed" in coverage_args
        assert "--cov-fail-under=85" in coverage_args
        assert "--cov-report=term:skip-covered" in coverage_args
        assert "--cov-report=term-missing" not in coverage_args
        assert not any(
            arg == "--cov-report=html:reports/coverage/htmlcov"
            or arg.startswith("--cov-report=html")
            for arg in coverage_args
        )

    scripts_lane = matrix_lanes["unit-scripts-tooling"]
    assert scripts_lane["paths"] == ["tests/unit/scripts/"]


def test_zed_pytest_lane_rejects_overlapping_runs(tmp_path: Path) -> None:
    """The runner must serialize pytest lanes beyond Zed's task-local guard."""
    lane_module = _load_lane_module()
    exclusive_lane_lock = lane_module["_exclusive_lane_lock"]
    busy_error = lane_module["ZedLaneBusyError"]
    lock_path = tmp_path / "zed-pytest-lane.lock"

    with exclusive_lane_lock(lock_path):
        with pytest.raises(busy_error, match="already running"):
            with exclusive_lane_lock(lock_path):
                pytest.fail("overlapping lane unexpectedly acquired the lock")


def test_zed_terminal_prefers_windows_venv_and_offline_vcr(
    project_config_root: Path,
) -> None:
    """The Windows profile never activates a potentially Linux-owned venv."""
    settings = _project_json(project_config_root, "settings.json")
    terminal = settings["terminal"]
    detect = terminal["detect_venv"]["on"]["directories"]

    assert detect == [".venv-win"]
    assert terminal["detect_venv"]["on"]["activate_script"] == "power_shell"
    assert terminal["env"]["VCR_RECORD_MODE"] == "none"
    assert terminal["env"]["PYTHONDONTWRITEBYTECODE"] == "1"
    assert "VIRTUAL_ENV" not in terminal["env"], "Let activation set an absolute path"


def test_zed_snippets_follow_current_bioetl_contracts() -> None:
    """Tracked snippets should avoid retired imports, typing, and storage shapes."""
    python_snippets = _load_json("snippets/python.json")
    yaml_snippets = _load_json("snippets/yaml.json")

    for snippet in python_snippets.values():
        assert "from __future__ import annotations" in snippet["body"]
        assert str(snippet["prefix"]).startswith("bioetl-")

    for snippet in yaml_snippets.values():
        assert str(snippet["prefix"]).startswith("bioetl-")

    required_python = {
        "bioetl-vo",
        "bioetl-port",
        "bioetl-impl",
        "bioetl-config",
        "bioetl-factory",
        "bioetl-error",
        "bioetl-test-unit",
        "bioetl-test-async",
        "bioetl-test-arch",
        "bioetl-extract",
        "bioetl-transform",
        "bioetl-validate",
        "bioetl-export",
        "bioetl-log",
        "bioetl-event",
    }
    required_yaml = {
        "bioetl-pipeline-config",
        "bioetl-dq-rule",
        "bioetl-retry-policy",
        "bioetl-rate-limit",
        "bioetl-composite-enricher",
        "bioetl-field-priority",
    }
    python_prefixes = {snippet["prefix"] for snippet in python_snippets.values()}
    yaml_prefixes = {snippet["prefix"] for snippet in yaml_snippets.values()}
    assert required_python <= python_prefixes
    assert required_yaml <= yaml_prefixes

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
    assert "print(" not in rendered_python
    assert "structlog.get_logger" not in rendered_python
    assert "LoggerPort" in rendered_python
    assert "BioETLDomainError" in rendered_python
    assert "data/silver" not in rendered_yaml
    assert "data/gold" not in rendered_yaml
    assert "format: parquet" not in rendered_yaml
    assert "pipeline_name:" in rendered_yaml
    assert "idempotency_contract: merge_upsert" in rendered_yaml
    assert "seed.output_keys" in rendered_yaml
    assert "requests_per_second:" in rendered_yaml
    assert "use_retry_after:" in rendered_yaml


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


def test_local_zed_keymap_has_unique_reachable_bindings() -> None:
    """Strict JSON parsing rejects shadowed key chords in a supplied local keymap."""

    def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    keymap_path = ZED_ROOT / "keymap.json"
    if not keymap_path.is_file():
        pytest.skip("Optional local Zed config is absent: keymap.json")
    payload = json.loads(
        keymap_path.read_text(encoding="utf-8"),
        object_pairs_hook=_unique_object,
    )
    bindings = payload["bindings"]

    assert bindings["ctrl-d"] == "editor::SelectNextOccurrence"
    assert bindings["ctrl-alt-d"] == "editor::DuplicateLine"
