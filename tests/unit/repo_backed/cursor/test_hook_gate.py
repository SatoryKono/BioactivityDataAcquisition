"""Repo-backed unit tests for the Cursor project hook at .cursor/hooks/gate.py."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]

_ROOT = Path(__file__).resolve().parents[4]
_GATE_PATH = _ROOT / ".cursor" / "hooks" / "gate.py"
_HOOKS_PATH = _ROOT / ".cursor" / "hooks.json"


class _Empty:
    def read(self) -> str:
        return ""


def _load_gate() -> ModuleType:
    spec = importlib.util.spec_from_file_location("cursor_hook_gate", _GATE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _shell(command: str, *, branch: str = "feature") -> dict[str, object]:
    event = {
        "hook_event_name": "beforeShellExecution",
        "command": command,
        "cwd": str(_ROOT),
        "workspace_roots": [str(_ROOT)],
    }
    decision = _GATE.decide(event, branch_lookup=lambda _cwd: branch)
    assert isinstance(decision, dict)
    return decision


@pytest.mark.parametrize(
    ("command", "permission"),
    [
        ("git status", "allow"),
        ("git commit -m msg", "allow"),
        ("git push origin feature", "allow"),
        ("git reset --soft HEAD~1", "allow"),
        ("git rebase main", "allow"),
        ("git add -A", "allow"),
        ("Get-Content .env", "allow"),
        ("Set-Content .env.example x", "allow"),
        ("echo x > src/_tmp_a.py", "allow"),
        ("Get-Content docker-compose.monitoring.yml", "allow"),
        ("rm _tmp_notes.py", "allow"),
        ("git config user.name x", "deny"),
        ("git -C repo config --list", "deny"),
        ("git reset --hard", "deny"),
        ("git submodule foreach 'git reset --hard'", "deny"),
        ("git commit --no-verify -m x", "deny"),
        ("git commit -nm x", "deny"),
        ("git commit --amend --no-verify", "deny"),
        ("git commit --no-gpg-sign -m x", "deny"),
        ("git rebase -i HEAD~2", "deny"),
        ("git add -i", "deny"),
        ("git push --force origin main", "deny"),
        ("git push --force-with-lease origin master", "deny"),
        ("git push -f origin refs/heads/main", "deny"),
        ("git push origin +feature:main", "deny"),
        ("git push --mirror origin", "deny"),
        ("git push origin --delete main", "deny"),
        ("Set-Content .env x", "deny"),
        ("Remove-Item .env.local", "deny"),
        ("echo x > .env", "deny"),
        ("echo x>.env", "deny"),
        ("echo x>>.env", "deny"),
        ("sed -i 's/a/b/' .env", "deny"),
        ("echo x > _tmp_a.py", "deny"),
        ("echo x > ./NUL", "deny"),
        ("echo x > test_probe.py", "deny"),
        ("echo x > tests/../_tmp_x.py", "deny"),
        ("git commit --amend -m x", "ask"),
        ("git push --force origin feature", "ask"),
        ("git push -f origin feature", "ask"),
        ("docker compose -f docker-compose.monitoring.yml up -d", "ask"),
    ],
)
def test_shell_permission(command: str, permission: str) -> None:
    assert _shell(command)["permission"] == permission


def test_force_push_of_current_main_is_denied() -> None:
    decision = _shell("git push --force", branch="main")
    assert decision["permission"] == "deny"


def test_force_push_via_c_uses_target_repo_branch() -> None:
    decision = _GATE.decide(
        {
            "hook_event_name": "beforeShellExecution",
            "command": "git -C otherrepo push -f origin",
            "cwd": str(_ROOT),
            "workspace_roots": [str(_ROOT)],
        },
        branch_lookup=lambda cwd: "main" if cwd.endswith("otherrepo") else "feature",
    )
    assert decision["permission"] == "deny"


def test_read_of_env_file_is_allowed() -> None:
    decision = _GATE.decide(
        {
            "hook_event_name": "preToolUse",
            "tool_name": "Read",
            "tool_input": {"path": str(_ROOT / ".env")},
            "workspace_roots": [str(_ROOT)],
        }
    )
    assert decision == {"permission": "allow"}


def test_write_of_env_file_is_denied() -> None:
    decision = _GATE.decide(
        {
            "hook_event_name": "preToolUse",
            "tool_name": "Write",
            "tool_input": {"path": ".env.local", "contents": "TOKEN=1"},
        }
    )
    assert decision["permission"] == "deny"


def test_delete_of_root_scratch_is_allowed() -> None:
    decision = _GATE.decide(
        {
            "hook_event_name": "preToolUse",
            "tool_name": "Delete",
            "tool_input": {"path": "_tmp_notes.py"},
        }
    )
    assert decision == {"permission": "allow"}


def test_write_of_root_scratch_test_module_is_denied() -> None:
    decision = _GATE.decide(
        {
            "hook_event_name": "preToolUse",
            "tool_name": "Write",
            "tool_input": {"path": "test_probe.py", "contents": "pass\n"},
        }
    )
    assert decision["permission"] == "deny"


def test_root_test_module_write_is_allowed() -> None:
    decision = _GATE.decide(
        {
            "hook_event_name": "preToolUse",
            "tool_name": "Write",
            "tool_input": {"path": "tests/test_example.py", "contents": "pass\n"},
        }
    )
    assert decision == {"permission": "allow"}


def test_apply_patch_env_path_is_denied() -> None:
    decision = _GATE.decide(
        {
            "hook_event_name": "preToolUse",
            "tool_name": "ApplyPatch",
            "tool_input": {
                "patch": "*** Update File: .env\n@@\n-OLD\n+NEW\n",
            },
        }
    )
    assert decision["permission"] == "deny"


def test_mcp_write_env_is_denied() -> None:
    decision = _GATE.decide(
        {
            "hook_event_name": "preToolUse",
            "tool_name": "MCP:write_file",
            "tool_input": {"path": ".env", "contents": "TOKEN=1"},
        }
    )
    assert decision["permission"] == "deny"


def test_session_start_adds_russian_context() -> None:
    decision = _GATE.decide({"hook_event_name": "sessionStart"})
    context = decision["additional_context"]
    assert isinstance(context, str)
    assert "русском" in context


def test_debt_file_edit_adds_context() -> None:
    decision = _GATE.decide(
        {
            "hook_event_name": "postToolUse",
            "tool_name": "StrReplace",
            "tool_input": {"path": "configs/quality/debt_scorecard.yaml"},
        }
    )
    assert "additional_context" in decision


def test_dashboard_budget_edit_adds_no_context() -> None:
    decision = _GATE.decide(
        {
            "hook_event_name": "postToolUse",
            "tool_name": "StrReplace",
            "tool_input": {
                "path": "docs/03-guides/dashboards/contracts/layout-budgets.yaml"
            },
        }
    )
    assert decision == {}


def test_empty_stdin_denies(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "stdin", _Empty())
    assert _GATE.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["permission"] == "deny"


@pytest.mark.parametrize(
    "raw",
    [
        "{not-json",
        json.dumps({"hook_event_name": "unknownEvent"}),
    ],
)
def test_invalid_or_unknown_event_is_fail_closed(
    raw: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "stdin", type("S", (), {"read": lambda self: raw})())
    assert _GATE.main() == 0
    payload = json.loads(capsys.readouterr().out)
    if "not-json" in raw:
        assert payload["permission"] == "deny"
    else:
        assert payload == {}


def test_cli_allows_git_status() -> None:
    completed = subprocess.run(
        [sys.executable, str(_GATE_PATH)],
        input=json.dumps(
            {"hook_event_name": "beforeShellExecution", "command": "git status"}
        ),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0
    assert json.loads(completed.stdout)["permission"] == "allow"


def test_hooks_manifest_points_at_existing_script() -> None:
    payload = json.loads(_HOOKS_PATH.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    hooks = payload["hooks"]
    assert set(hooks) == {
        "beforeShellExecution",
        "preToolUse",
        "sessionStart",
        "postToolUse",
    }
    for name in ("beforeShellExecution", "preToolUse"):
        entry = hooks[name][0]
        assert entry["command"] == "python .cursor/hooks/gate.py"
        assert entry["failClosed"] is True
        assert "matcher" not in entry
    for name in ("sessionStart", "postToolUse"):
        entry = hooks[name][0]
        assert entry["command"] == "python .cursor/hooks/gate.py"
        assert "failClosed" not in entry
    assert _GATE_PATH.is_file()
