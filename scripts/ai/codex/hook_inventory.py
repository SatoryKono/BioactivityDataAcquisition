"""Read-only hook discovery; never execute runtime commands or hook contents.

Only local Git metadata queries are executed. Vendor documentation describes
capabilities, not proof that a particular installed build implements them.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib
from typing import Any

RUNTIMES = {
    "codex": (
        ".codex/config.toml",
        ".codex/hooks.json",
        "https://developers.openai.com/codex/hooks",
    ),
    "junie": (
        ".junie/config.json",
        ".junie/config.json",
        "https://junie.jetbrains.com/docs/junie-cli-hooks.html",
    ),
    "devin": (
        ".devin/config.json",
        ".devin/hooks.v1.json",
        "https://docs.devin.ai/cli/extensibility/hooks/overview",
    ),
    "opencode": (
        "opencode.json",
        ".opencode/plugins",
        "https://opencode.ai/docs/plugins/",
    ),
}
GIT_HOOKS = ("pre-commit", "pre-push", "commit-msg", "reference-transaction")
MAX_BYTES = 1024 * 1024


def _read_bytes(path: Path) -> bytes:
    """Bound reads even when another process grows or replaces the file."""
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("configuration exceeds diagnostic size limit")
    return raw


def _read_config(path: Path) -> dict[str, Any]:
    """Parse an object without exposing its values in parser diagnostics."""
    raw = _read_bytes(path).decode("utf-8-sig")
    data = tomllib.loads(raw) if path.suffix == ".toml" else json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("configuration must be an object")
    return data


def _file_evidence(path: Path) -> dict[str, Any]:
    """Record identity without emitting configuration or command contents."""
    result: dict[str, Any] = {"path": str(path), "present": False}
    try:
        result["present"] = path.exists()
        if path.is_file():
            result["sha256"] = hashlib.sha256(_read_bytes(path)).hexdigest()
    except (OSError, ValueError):
        result["status"] = "ERROR"
    return result


def _git(root: Path, *args: str) -> str:
    """Run a bounded metadata query without optional Git locks."""
    completed = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=3,
        check=False,
    )
    if completed.returncode:
        # Do not echo configuration values or arbitrary stderr to diagnostics.
        raise ValueError("Git metadata query failed")
    return completed.stdout.strip()


def _event_sources(sources: list[tuple[Path, Any]]) -> dict[str, list[str]]:
    """Keep every observed event's origin, including inline-only sources."""
    events: dict[str, set[str]] = {}
    for path, hooks in sources:
        if isinstance(hooks, dict):
            for event in hooks:
                events.setdefault(event, set()).add(str(path))
    return {event: sorted(paths) for event, paths in sorted(events.items())}


def _opencode_candidates(root: Path) -> list[dict[str, Any]]:
    """Fingerprint alternate project configs; never guess JSONC contents."""
    results = []
    for name in (
        "opencode.jsonc",
        ".opencode/opencode.json",
        ".opencode/opencode.jsonc",
    ):
        path = root / name
        item = _file_evidence(path)
        if path.is_file():
            if path.suffix == ".jsonc":
                item.update(parse_status="UNSUPPORTED", plugins_configured=None)
            else:
                try:
                    config = _read_config(path)
                    item.update(
                        parse_status="OBSERVED",
                        plugins_configured=bool(
                            config.get("plugin") or config.get("plugins")
                        ),
                    )
                except (OSError, ValueError):
                    item.update(parse_status="ERROR", plugins_configured=None)
        results.append(item)
    return results


def _merge_opencode_evidence(result: dict[str, Any]) -> None:
    """Avoid an absence claim when an alternate config cannot be parsed."""
    candidates = result["additional_configurations"]
    if any(item.get("plugins_configured") is True for item in candidates):
        result["plugins_configured"] = True
    if any(item.get("parse_status") in {"UNSUPPORTED", "ERROR"} for item in candidates):
        if result.get("config_status") != "ERROR":
            result["config_status"] = "INCOMPLETE"
        if not result["plugins_configured"]:
            result["plugins_configured"] = None


def git_inventory(root: Path) -> dict[str, Any]:
    """Resolve effective hooks directory with Git, including linked worktrees."""
    try:
        raw = _git(root, "rev-parse", "--path-format=absolute", "--git-path", "hooks")
        hooks = Path(raw)
        if not hooks.is_absolute():
            hooks = root / hooks
        records = []
        for name in GIT_HOOKS:
            path = hooks / name
            item = _file_evidence(path)
            candidate = path.is_file() and os.access(path, os.X_OK)
            item.update(name=name, discoverable=candidate, execution="NOT_PROVEN")
            records.append(item)
        return {
            "status": "OBSERVED",
            "directory": str(hooks.resolve()),
            "hooks": records,
        }
    except (OSError, ValueError, subprocess.SubprocessError):
        return {
            "status": "ERROR",
            "reason": "effective Git hooks directory unavailable",
        }


def runtime_inventory(root: Path, name: str, command: str | None) -> dict[str, Any]:
    """Report command resolution without interpreting or running launchers."""
    config_name, hook_name, documentation = RUNTIMES[name]
    result: dict[str, Any] = {
        "runtime": name,
        "command": command,
        "resolved_command": str(Path(command).resolve()) if command else None,
        "version": None,
        "version_status": "NOT_PROVEN" if command else "MISSING",
        "version_method": "requires binary-bound vendor metadata or explicit version evidence",
        "capability_status": "NOT_PROVEN",
        "enabled_by_diagnostic": False,
        "documentation": documentation,
        "execution": "NOT_PROVEN",
        "scope": "current OS/process PATH only; does not inspect another WSL distribution",
        "config": _file_evidence(root / config_name),
        "hook_surface": _file_evidence(root / hook_name),
        "configured_events": [],
    }
    if name == "opencode":
        result["additional_configurations"] = _opencode_candidates(root)
    _populate_configuration(root, name, result)

    return result


def _configuration_source(path: Path) -> tuple[dict[str, Any], str]:
    """One unreadable source must not suppress an independent valid source."""
    try:
        if not path.exists():
            return {}, "MISSING"
        return _read_config(path), "OBSERVED"
    except (OSError, ValueError, RecursionError):
        return {}, "ERROR"


def _populate_configuration(root: Path, name: str, result: dict[str, Any]) -> None:
    """Retain partial facts and per-source parse states without absence claims."""
    config_name, hook_name, _ = RUNTIMES[name]
    path, hook_path = root / config_name, root / hook_name
    config, config_status = _configuration_source(path)
    if hook_path == path:
        hook_config, hook_status = config, config_status
    elif name == "opencode":
        hook_config, hook_status = {}, "NOT_APPLICABLE"
    else:
        hook_config, hook_status = _configuration_source(hook_path)
    result["source_parse_status"] = {
        str(path): config_status,
        str(hook_path): hook_status,
    }
    result["config_status"] = (
        "ERROR" if "ERROR" in {config_status, hook_status} else "OBSERVED"
    )
    hooks = hook_config.get("hooks", hook_config if name == "devin" else {})
    events = _event_sources([(path, config.get("hooks", {})), (hook_path, hooks)])
    result["configured_events"] = sorted(events)
    result["event_sources"] = events
    result["inline_hooks_present"] = (
        None if config_status == "ERROR" else bool(config.get("hooks"))
    )
    result["plugins_configured"] = (
        None
        if config_status == "ERROR"
        else bool(config.get("plugin") or config.get("plugins"))
    )
    if name == "opencode":
        _merge_opencode_evidence(result)
    result["discovery_note"] = {
        "junie": "project hooks require explicit --config-location; EAP capability must be verified",
        "opencode": "subordinate surface; plugin APIs must match installed major version",
    }.get(
        name,
        "trust, managed policy, user/session/plugin layers require separate verification",
    )


def collect(root: Path) -> dict[str, Any]:
    """Collect local evidence; unknown installed capabilities never become PASS."""
    runtimes = [runtime_inventory(root, name, shutil.which(name)) for name in RUNTIMES]
    return {
        "schema_version": 1,
        "status": "NOT_PROVEN",
        "platform": sys.platform,
        "python": sys.executable,
        "python_version": sys.version.split()[0],
        "repo_root": str(root.resolve()),
        "git": git_inventory(root),
        "runtimes": runtimes,
        "layers": {
            "git_configuration": _file_evidence(root / ".pre-commit-config.yaml"),
            "command_wrapper": _file_evidence(
                root / "scripts/engineering/dev/pretest_guardrails.sh"
            ),
            "ci": _file_evidence(root / ".github/workflows/skills-consistency.yml"),
        },
    }
