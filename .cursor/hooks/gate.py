#!/usr/bin/env python3
"""Cursor project hook for BioETL guardrails.

Stdlib only. Reads one JSON event on stdin and writes one JSON object to
stdout. The script does not create or append files: stdin may contain a
shell command.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections.abc import Callable, Mapping
from typing import Any

_PROTECTED_BRANCHES = frozenset({"main", "master"})
_READ_ONLY_TOOLS = frozenset(
    {
        "AwaitShell",
        "FetchMcpResource",
        "Glob",
        "Grep",
        "ListMcpResources",
        "Read",
        "SemanticSearch",
        "Shell",
        "Task",
        "WebFetch",
        "WebSearch",
    }
)
_MUTATING_TOOLS = frozenset(
    {
        "ApplyPatch",
        "Delete",
        "Edit",
        "EditNotebook",
        "StrReplace",
        "TabWrite",
        "Write",
        "WriteFile",
    }
)
_EDIT_KEYS = frozenset(
    {"contents", "edits", "new_string", "old_string", "patch", "stream"}
)
_PATH_KEYS = frozenset(
    {
        "file",
        "file_path",
        "notebook_path",
        "path",
        "relativeWorkspacePath",
        "relative_workspace_path",
        "target_file",
        "target_notebook",
        "uri",
    }
)
_WRITE_COMMANDS = frozenset(
    {
        "add-content",
        "clear-content",
        "copy",
        "copy-item",
        "cp",
        "del",
        "erase",
        "move",
        "move-item",
        "mv",
        "new-item",
        "out-file",
        "remove-item",
        "ren",
        "rename",
        "rename-item",
        "rm",
        "rmdir",
        "set-content",
        "tee",
        "tee-object",
        "touch",
        "truncate",
        "unlink",
    }
)
_GIT_PATH_WRITES = frozenset({"checkout", "clean", "mv", "restore", "rm"})
_PUSH_VALUE_OPTIONS = frozenset(
    {"--exec", "--push-option", "--receive-pack", "--repo", "-o"}
)
_DEBT_SUFFIXES = (
    "configs/quality/architecture_metric_exemptions.yaml",
    "configs/quality/debt_scorecard.yaml",
    "configs/quality/duplication_complexity_exemptions.yaml",
    "configs/quality/source_test_mapping_exceptions.yaml",
    "tests/performance/hotspot_budgets.json",
)
_SCRATCH = re.compile(
    r"(?i)^("
    r"_tmp_.+\.py|_cr_.+\.py|_publish_.+\.py|_fail_.+\.txt|_a\.txt|"
    r"tmp_sub_.+\.txt|temp_closeout\.json|\.tmp_.+|nul"
    r")$"
)
_REDIRECT = re.compile(r"(?i)(?:^|[\s|;&])\d*>{1,2}\s*(\S+)")
_DOCKER = re.compile(
    r"(?i)(?<![A-Za-z0-9_-])docker(?:-compose)?(?:\.exe)?(?![A-Za-z0-9_-])"
)
_DOCKER_ACTION = re.compile(
    r"(?i)(?<![A-Za-z0-9_-])(?:up|start|restart|run)(?![A-Za-z0-9_-])"
)
_MONITORING_FILE = "docker-compose.monitoring.yml"
_DENY_INPUT: dict[str, str] = {
    "permission": "deny",
    "user_message": (
        "Хук Cursor получил пустой или невалидный ввод и остановил действие."
    ),
    "agent_message": (
        "Hook gate denied the action because stdin was empty or not valid JSON."
    ),
}
SESSION_CONTEXT = (
    "В этом репозитории ответы пользователю на русском. "
    "Не создавать, не менять, не переименовывать и не удалять .env и .env.* "
    "без явного разрешения в этой задаче. .env.example можно менять. "
    "Чтение .env разрешено. "
    "Бюджеты техдолга, exemptions, hotspot thresholds и family caps можно "
    "только уменьшить или оставить. "
    "Не создавать корневой мусор: _tmp_*.py, _cr_*.py, _publish_*.py, "
    "_fail_*.txt, _a.txt, tmp_sub_*.txt, temp_closeout.json, .tmp_*, nul, NUL. "
    "После правок выполни post-change для затронутой поверхности и перечисли "
    "прогнанные и пропущенные проверки."
)
_DEBT_CONTEXT = (
    "Файл входит в бюджет техдолга. Лимит, exemption, hotspot threshold "
    "или family cap можно только уменьшить или оставить. Рост запрещён. "
    "Итог проверяет CI."
)
_PERMISSION_RANK = {"allow": 0, "ask": 1, "deny": 2}


def main() -> int:
    """Read one hook event and write its decision."""
    raw = sys.stdin.read()
    if not raw.strip():
        _emit(_DENY_INPUT)
        return 0
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        _emit(_DENY_INPUT)
        return 0
    if not isinstance(event, dict):
        _emit(_DENY_INPUT)
        return 0
    _emit(decide(event))
    return 0


def decide(
    event: Mapping[str, Any],
    *,
    branch_lookup: Callable[[str], str | None] | None = None,
) -> dict[str, Any]:
    """Return the JSON object for one hook event."""
    name = event.get("hook_event_name")
    if name == "beforeShellExecution":
        return _decide_shell(event, branch_lookup or _git_branch)
    if name == "preToolUse":
        return _decide_pre_tool(event)
    if name == "sessionStart":
        return {"additional_context": SESSION_CONTEXT}
    if name == "postToolUse":
        return _decide_post_tool(event)
    if name in {"beforeMCPExecution", "beforeReadFile", "subagentStart"}:
        return {"permission": "allow"}
    return {}


def _decide_shell(
    event: Mapping[str, Any],
    branch_lookup: Callable[[str], str | None],
) -> dict[str, str]:
    command = event.get("command")
    if not isinstance(command, str):
        return dict(_DENY_INPUT)
    roots = _workspace_roots(event)
    cwd = event.get("cwd")
    cwd_text = cwd if isinstance(cwd, str) else ""
    decisions = [
        _classify_segment(segment, roots, cwd_text, branch_lookup)
        for segment in _split_commands(command)
    ]
    if not decisions:
        return {"permission": "allow"}
    chosen = max(decisions, key=lambda item: _PERMISSION_RANK[item[0]])
    permission, user_message, agent_message = chosen
    if permission == "allow":
        return {"permission": "allow"}
    return {
        "permission": permission,
        "user_message": user_message,
        "agent_message": agent_message,
    }


def _decide_pre_tool(event: Mapping[str, Any]) -> dict[str, str]:
    tool_name = event.get("tool_name")
    if not isinstance(tool_name, str):
        tool_name = ""
    tool_input = _tool_input(event.get("tool_input"))
    if not _is_file_mutation(tool_name, tool_input):
        return {"permission": "allow"}
    roots = _workspace_roots(event)
    for path in _iter_paths(tool_input):
        kind = _path_kind(path, roots)
        if kind == "env":
            return _deny(
                "Запись .env и .env.* запрещена без явного разрешения в задаче.",
                "Hook gate denied a write or delete of a secret env file.",
            )
        if kind == "scratch":
            return _deny(
                "Корневой scratch-файл создавать нельзя.",
                "Hook gate denied a root scratch file.",
            )
    return {"permission": "allow"}


def _decide_post_tool(event: Mapping[str, Any]) -> dict[str, str]:
    tool_name = event.get("tool_name")
    if not isinstance(tool_name, str):
        tool_name = ""
    tool_input = _tool_input(event.get("tool_input"))
    if not _is_file_mutation(tool_name, tool_input):
        return {}
    roots = _workspace_roots(event)
    for path in _iter_paths(tool_input):
        if _is_debt_path(path, roots):
            return {"additional_context": _DEBT_CONTEXT}
    return {}


def _classify_segment(
    segment: str,
    roots: list[str],
    cwd: str,
    branch_lookup: Callable[[str], str | None],
) -> tuple[str, str, str]:
    denies: list[tuple[str, str, str]] = []
    asks: list[tuple[str, str, str]] = []
    for invocation in _git_invocations(segment):
        verdict = _classify_git(invocation, cwd, branch_lookup)
        if verdict[0] == "deny":
            denies.append(verdict)
        elif verdict[0] == "ask":
            asks.append(verdict)
    path_kind = _segment_write_kind(segment, roots)
    if path_kind == "env":
        denies.append(
            _deny_tuple(
                "Команда записывает или удаляет .env / .env.*.",
                "Hook gate denied a shell write of a secret env file.",
            )
        )
    elif path_kind == "scratch":
        denies.append(
            _deny_tuple(
                "Команда создаёт корневой scratch-файл. "
                "Для подавления вывода в PowerShell используй $null.",
                "Hook gate denied a root scratch file. Use $null instead of nul.",
            )
        )
    if _starts_monitoring(segment):
        asks.append(
            (
                "ask",
                "Запуск docker-compose.monitoring.yml требует подтверждения.",
                "Hook gate asked before starting the optional monitoring stack.",
            )
        )
    if denies:
        return denies[0]
    if asks:
        return asks[0]
    return ("allow", "", "")


def _classify_git(
    tokens: list[str],
    cwd: str,
    branch_lookup: Callable[[str], str | None],
) -> tuple[str, str, str]:
    parsed = _git_command(tokens)
    if parsed is None:
        return ("allow", "", "")
    subcommand, args = parsed
    if subcommand == "config":
        return _deny_tuple(
            "git config менять и читать через хук нельзя.",
            "Hook gate denied git config.",
        )
    if subcommand == "reset" and _has_flag(args, "--hard"):
        return _deny_tuple(
            "git reset --hard запрещён.",
            "Hook gate denied git reset --hard.",
        )
    if subcommand == "commit" and (
        _has_flag(args, "--no-verify")
        or "-n" in args
        or _has_flag(args, "--no-gpg-sign")
    ):
        return _deny_tuple(
            "git commit без хуков или без подписи запрещён.",
            "Hook gate denied git commit --no-verify or --no-gpg-sign.",
        )
    if subcommand == "rebase" and (
        _has_flag(args, "-i") or _has_prefix(args, "--interactive")
    ):
        return _deny_tuple(
            "Интерактивный git rebase запрещён.",
            "Hook gate denied interactive git rebase.",
        )
    if subcommand == "add" and (
        _has_flag(args, "-i") or _has_prefix(args, "--interactive")
    ):
        return _deny_tuple(
            "Интерактивный git add запрещён.",
            "Hook gate denied interactive git add.",
        )
    if subcommand == "push":
        return _classify_push(args, cwd, branch_lookup)
    if subcommand == "commit" and _has_flag(args, "--amend"):
        return (
            "ask",
            "git commit --amend требует подтверждения.",
            "Hook gate asked before git commit --amend.",
        )
    return ("allow", "", "")


def _classify_push(
    args: list[str],
    cwd: str,
    branch_lookup: Callable[[str], str | None],
) -> tuple[str, str, str]:
    if not _push_is_force(args):
        return ("allow", "", "")
    refspecs = _push_refspecs(args)
    destinations = [_ref_destination(refspec) for refspec in refspecs]
    if any(dest in _PROTECTED_BRANCHES for dest in destinations):
        return _deny_tuple(
            "Принудительный push в main или master запрещён.",
            "Hook gate denied a force push to main or master.",
        )
    if not refspecs:
        branch = branch_lookup(cwd)
        if branch in _PROTECTED_BRANCHES:
            return _deny_tuple(
                "Принудительный push в main или master запрещён.",
                "Hook gate denied a force push of the current main or master branch.",
            )
    return (
        "ask",
        "Принудительный push не в main/master требует подтверждения.",
        "Hook gate asked before a force push.",
    )


def _starts_monitoring(segment: str) -> bool:
    if _MONITORING_FILE not in segment:
        return False
    return (
        _DOCKER.search(segment) is not None
        and _DOCKER_ACTION.search(segment) is not None
    )


def _segment_write_kind(segment: str, roots: list[str]) -> str | None:
    visible = _strip_unquoted_comment(segment)
    redirected = [
        kind
        for match in _REDIRECT.finditer(visible)
        if (kind := _path_kind(match.group(1).strip("\"'"), roots)) is not None
    ]
    if "env" in redirected:
        return "env"
    if "scratch" in redirected:
        return "scratch"
    tokens = _tokenize(visible)
    kinds = [kind for token in tokens if (kind := _path_kind(token, roots)) is not None]
    if not kinds:
        return None
    lowered = [token.lower() for token in tokens]
    writes = any(token in _WRITE_COMMANDS for token in lowered)
    if _find_git(tokens) is not None:
        parsed = _git_command(tokens)
        writes = writes or (parsed is not None and parsed[0] in _GIT_PATH_WRITES)
    if not writes:
        return None
    if "env" in kinds:
        return "env"
    if "scratch" in kinds:
        return "scratch"
    return None


def _is_file_mutation(tool_name: str, tool_input: Any) -> bool:
    if tool_name in _READ_ONLY_TOOLS or tool_name.startswith("MCP:"):
        return False
    if tool_name in _MUTATING_TOOLS:
        return True
    if re.search(r"(?i)(write|delete|remove|strreplace|applypatch|edit)", tool_name):
        return True
    return isinstance(tool_input, dict) and bool(_EDIT_KEYS.intersection(tool_input))


def _is_debt_path(path: str, roots: list[str]) -> bool:
    relative = _relative_path(path, roots)
    return any(relative.endswith(suffix) for suffix in _DEBT_SUFFIXES)


def _path_kind(token: str, roots: list[str]) -> str | None:
    relative = _relative_path(token, roots)
    if not relative or relative.endswith("/"):
        return None
    name = relative.rsplit("/", 1)[-1]
    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        return "env"
    if "/" not in relative and _SCRATCH.fullmatch(name):
        return "scratch"
    return None


def _relative_path(token: str, roots: list[str]) -> str:
    cleaned = token.strip().strip("\"'").replace("\\", "/")
    cleaned = re.sub(r"^\d*>+", "", cleaned)
    if cleaned.startswith("file://"):
        cleaned = cleaned[7:]
    lowered = cleaned.lower()
    for root in roots:
        root_norm = root.replace("\\", "/").rstrip("/")
        prefix = root_norm.lower() + "/"
        if lowered.startswith(prefix):
            cleaned = cleaned[len(root_norm) + 1 :]
            break
    while cleaned.startswith("./"):
        cleaned = cleaned[2:]
    return cleaned


def _iter_paths(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _PATH_KEYS and isinstance(item, str):
                found.append(item)
            elif isinstance(item, dict | list):
                found.extend(_iter_paths(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_iter_paths(item))
    return found


def _tool_input(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return value


def _workspace_roots(event: Mapping[str, Any]) -> list[str]:
    roots = event.get("workspace_roots")
    if not isinstance(roots, list):
        return []
    return [root for root in roots if isinstance(root, str)]


def _split_commands(command: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    index = 0
    while index < len(command):
        char = command[index]
        if quote is not None:
            buf.append(char)
            if char == quote:
                quote = None
            index += 1
            continue
        if char in {'"', "'"}:
            quote = char
            buf.append(char)
            index += 1
            continue
        if command.startswith("&&", index) or command.startswith("||", index):
            parts.append("".join(buf))
            buf = []
            index += 2
            continue
        if char in {";", "|", "\n"}:
            parts.append("".join(buf))
            buf = []
            index += 1
            continue
        buf.append(char)
        index += 1
    parts.append("".join(buf))
    return [part.strip() for part in parts if part.strip()]


def _strip_unquoted_comment(segment: str) -> str:
    buf: list[str] = []
    quote: str | None = None
    for char in segment:
        if quote is not None:
            buf.append(char)
            if char == quote:
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
            buf.append(char)
            continue
        if char == "#":
            break
        buf.append(char)
    return "".join(buf)


def _tokenize(segment: str) -> list[str]:
    tokens: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    for char in segment:
        if quote is not None:
            if char == quote:
                quote = None
            else:
                buf.append(char)
            continue
        if char in {'"', "'"}:
            quote = char
            continue
        if char.isspace():
            if buf:
                tokens.append("".join(buf))
                buf = []
            continue
        buf.append(char)
    if buf:
        tokens.append("".join(buf))
    return tokens


def _git_invocations(segment: str) -> list[list[str]]:
    tokens = _tokenize(segment)
    if _find_git(tokens) is None:
        return []
    return [tokens]


def _find_git(tokens: list[str]) -> int | None:
    for index, token in enumerate(tokens):
        name = token.replace("\\", "/").rsplit("/", 1)[-1].lower()
        if name in {"git", "git.exe"}:
            return index
    return None


def _git_command(tokens: list[str]) -> tuple[str, list[str]] | None:
    index = _find_git(tokens)
    if index is None:
        return None
    cursor = index + 1
    while cursor < len(tokens):
        token = tokens[cursor]
        if token in {"-C", "-c", "--git-dir", "--namespace", "--work-tree"}:
            cursor += 2
            continue
        if token.startswith(("--git-dir=", "--work-tree=", "--namespace=")):
            cursor += 1
            continue
        if token.startswith("-"):
            cursor += 1
            continue
        return token.lower(), tokens[cursor + 1 :]
    return None


def _push_is_force(args: list[str]) -> bool:
    for arg in args:
        if arg in {"-f", "--force", "--force-if-includes", "--force-with-lease"}:
            return True
        if arg.startswith(("--force=", "--force-with-lease=")):
            return True
    return False


def _push_refspecs(args: list[str]) -> list[str]:
    positional: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--":
            positional.extend(args[index + 1 :])
            break
        if arg.startswith("-"):
            if arg in _PUSH_VALUE_OPTIONS:
                index += 2
                continue
            index += 1
            continue
        positional.append(arg)
        index += 1
    if len(positional) >= 2:
        return positional[1:]
    if len(positional) == 1 and (
        ":" in positional[0] or _ref_destination(positional[0]) in _PROTECTED_BRANCHES
    ):
        return positional
    return []


def _ref_destination(refspec: str) -> str:
    ref = refspec[1:] if refspec.startswith("+") else refspec
    if ":" in ref:
        ref = ref.split(":", 1)[1]
    prefix = "refs/heads/"
    if ref.startswith(prefix):
        return ref[len(prefix) :]
    return ref


def _has_flag(args: list[str], flag: str) -> bool:
    return flag in args or any(arg.startswith(flag + "=") for arg in args)


def _has_prefix(args: list[str], prefix: str) -> bool:
    return any(arg == prefix or arg.startswith(prefix + "=") for arg in args)


def _git_branch(cwd: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd or None,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    name = completed.stdout.strip()
    return name or None


def _deny(user_message: str, agent_message: str) -> dict[str, str]:
    return {
        "permission": "deny",
        "user_message": user_message,
        "agent_message": agent_message,
    }


def _deny_tuple(user_message: str, agent_message: str) -> tuple[str, str, str]:
    return ("deny", user_message, agent_message)


def _emit(payload: Mapping[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
