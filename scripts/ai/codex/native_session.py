"""Private Windows session launcher behind the existing MCP operational CLI.

Select a previously qualified app-owned executable by exact digest. Workspace
comes only from the inherited physical cwd. The root environment file is read,
never copied; only the selected Ref credential is added to the child's env.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

REF_URL = "https://api.ref.tools/mcp"
SELECTOR_VERSIONS = Path("D:/pc-agent/tools/codex-session-versions")
SELECTOR_PYTHON = Path.home() / "AppData/Local/Programs/Python/Python313/python.exe"


def physical(path):
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise PermissionError("A physical absolute native path is required")
    for part in (path, *path.parents):
        if part.is_symlink() or getattr(part, "is_junction", lambda: False)():
            raise PermissionError("Native session path traverses a reparse point")
    return path


def qualified_binary(path, expected):
    approved = Path.home() / "AppData/Local/OpenAI/Codex/bin"
    if (
        path.name.lower() != "codex.exe"
        or ".." in path.parts
        or not path.is_relative_to(approved)
    ):
        raise PermissionError("Use the qualified app-owned native Codex executable")
    physical(path)
    if (
        re.fullmatch("[0-9a-f]{64}", expected) is None
        or hashlib.sha256(path.read_bytes()).hexdigest() != expected
    ):
        raise PermissionError("Native Codex executable drift")
    return path


def ref_environment(parent, values, mode):
    result = dict(parent)
    result.pop("REF_TOOL_API_KEY", None)
    if mode == "api-key":
        key = values.get("REF_TOOL_API_KEY")
        if not isinstance(key, str) or not key.strip():
            raise PermissionError("Root Ref credential is absent")
        result["REF_TOOL_API_KEY"] = key
    elif mode != "oauth":
        raise ValueError("Unknown Ref authorization mode")
    return result


def validate_ref(config, mode):
    entry = config.get("mcp_servers", {}).get("ref", {})
    if entry.get("url") != REF_URL or any(
        entry.get(k) for k in ("headers", "http_headers", "bearer_token_env_var")
    ):
        raise PermissionError(
            "Ref route needs an explicit separate authorization review"
        )
    expected = {"x-ref-api-key": "REF_TOOL_API_KEY"} if mode == "api-key" else {}
    if entry.get("env_http_headers", {}) != expected:
        raise PermissionError("Ref API-key and OAuth routes must remain separate")


def toml_value(value):
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ",".join(toml_value(item) for item in value) + "]"
    if isinstance(value, dict):
        return (
            "{"
            + ",".join(
                json.dumps(key) + "=" + toml_value(item) for key, item in value.items()
            )
            + "}"
        )
    raise ValueError("Unsupported native session setting")


def ref_only_overrides(config):
    """Select Ref without loading unrelated workspace bindings or credentials."""
    servers = config.get("mcp_servers", {})
    if not isinstance(servers, dict) or "ref" not in servers:
        raise PermissionError("Ref-only requires a configured Ref entry")
    result = []
    for name, entry in servers.items():
        if (
            not isinstance(name, str)
            or re.fullmatch(r"[A-Za-z0-9_-]+", name) is None
            or not isinstance(entry, dict)
        ):
            raise PermissionError("Ref-only requires safe configured server names")
        result.extend(
            ["--config", f"mcp_servers.{name}.enabled={toml_value(name == 'ref')}"]
        )
    return result


def _markdownify_entry(source, root, servers):
    from scripts.ai.codex.local_mcp_routes import common_directory

    if not source.exists():
        return None
    value = json.loads(physical(source).read_bytes())
    if (
        value.get("schema") != 1
        or Path(value["workspace"]) != root
        or value.get("server") != "Markdownify-BioETL"
        or common_directory(root, expected=Path(value["git_common"])) is None
    ):
        raise PermissionError(
            "Markdownify session binding does not match this workspace"
        )
    entry = value["entry"]
    if (
        set(entry) - {"command", "args", "startup_timeout_sec", "tool_timeout_sec"}
        or not isinstance(entry.get("command"), str)
        or not isinstance(entry.get("args"), list)
        or not all(isinstance(item, str) for item in entry["args"])
    ):
        raise PermissionError(
            "Markdownify session binding must be credential-free stdio"
        )
    if value["server"] in servers and servers[value["server"]] != entry:
        raise PermissionError("Existing unrelated Markdownify entry needs review")
    return value["server"], entry


def _selector_paths(entry, name):
    args = entry.get("args", [])
    if len(args) != 5 or args[:3] != ["-I", "-S", "-B"] or args[4] != name:
        raise PermissionError(
            "Native session requires its reviewed inherited-cwd selector"
        )
    command = Path(entry["command"])
    selector = Path(args[3])
    if (
        command != SELECTOR_PYTHON
        or not command.is_absolute()
        or not selector.is_absolute()
        or selector.name != "session_client.py"
        or selector.parent.parent != SELECTOR_VERSIONS
    ):
        raise PermissionError(
            "Native session requires its qualified installed selector"
        )
    return command, selector


def _validate_selector(entry, name):
    from scripts.ai.mcp.session_client import _verify_dispatcher

    command, selector = _selector_paths(entry, name)
    physical(command)
    physical(selector)
    manifest = _verify_dispatcher(selector.parent)
    if "session_client.py" not in manifest["files"] or not any(
        Path(path) == command for path in manifest["host_pins"]
    ):
        raise PermissionError("Installed selector must pin its script and interpreter")


def session_overrides(
    config, root, *, manifest=None, markdownify=None, acceptance=False
):
    """Use supported CLI-scoped fields without changing the global user TOML."""
    from scripts.ai.codex.local_mcp_routes import (
        apply_local_routes,
        select_local_routes_manifest,
    )

    manifest, _ = select_local_routes_manifest(manifest)
    raw = physical(manifest).read_bytes()
    binding = json.loads(raw)
    if any(name not in binding.get("entries", {}) for name in ("memory", "ast-grep")):
        raise PermissionError("Explicit session transport bindings are missing")
    servers = config.get("mcp_servers", {})
    if any(name not in servers for name in ("memory", "ast-grep")):
        raise PermissionError("Required native session servers are not configured")
    selected = apply_local_routes(
        {name: servers[name] for name in ("memory", "ast-grep")},
        root,
        manifest=manifest,
    )
    if manifest.read_bytes() != raw:
        raise PermissionError("Session transport binding changed")
    for name, entry in selected.items():
        _validate_selector(entry, name)
    if acceptance:
        entry = dict(selected["memory"])
        entry["args"] = list(entry["args"])
        if entry["args"][-1:] != ["memory"]:
            raise PermissionError(
                "Acceptance graph requires the reviewed session selector"
            )
        entry["args"][-1] = "memory-acceptance"
        selected["memory-acceptance"] = entry
    source = markdownify or Path.home() / ".config/pc-agent/markdownify-bioetl.json"
    optional = _markdownify_entry(source, root, servers)
    if optional is not None:
        selected[optional[0]] = optional[1]
    result = []
    for name, entry in selected.items():
        result.extend(["--config", "mcp_servers." + name + "=" + toml_value(entry)])
    return result


def workspace():
    root = next(
        (p for p in (Path.cwd(), *Path.cwd().parents) if (p / ".git").exists()), None
    )
    if root is None:
        raise PermissionError("Native session requires its actual project cwd")
    path = Path("D:/pc-agent/tools/shared-mcp/ast-workspace-profile.py")
    spec = importlib.util.spec_from_file_location("native_session_workspace", path)
    roots = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(roots)
    root = roots.physical_root(physical(root))
    return root, roots.CANONICAL


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--auth", choices=("api-key", "oauth"), default="api-key")
    parser.add_argument("--check", action="store_true")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--ref-only",
        action="store_true",
        help="Qualify Ref in an ordinary session with other MCP servers disabled",
    )
    modes.add_argument(
        "--acceptance",
        action="store_true",
        help="Enable the separate registered acceptance graph",
    )
    args = parser.parse_args(argv)
    session_cwd = physical(Path.cwd())
    root, canonical = workspace()
    if not session_cwd.is_relative_to(root):
        raise PermissionError("Session cwd is outside its validated workspace")
    binary = qualified_binary(args.executable, args.sha256)
    config = tomllib.loads(
        (Path.home() / ".codex/config.toml").read_text(encoding="utf-8")
    )
    validate_ref(config, args.auth)
    overrides = (
        ref_only_overrides(config)
        if args.ref_only
        else session_overrides(config, root, acceptance=args.acceptance)
    )
    from dotenv import dotenv_values

    values = (
        dotenv_values(physical(canonical / ".env")) if args.auth == "api-key" else {}
    )
    environment = ref_environment(os.environ, values, args.auth)
    if args.check:
        selection = {"ref_only": args.ref_only}
        if args.ref_only:
            selection["selected_servers"] = ["ref"]
        print(
            json.dumps(
                {
                    "workspace": str(root),
                    "executable": str(binary),
                    "auth": args.auth,
                    **selection,
                    "root_credential_present": bool(
                        environment.get("REF_TOOL_API_KEY")
                    ),
                    "session_overrides": len(overrides) // 2,
                    "spawned": False,
                    "native_request": "NOT_TESTED",
                }
            )
        )
        return 0
    return subprocess.call(
        [str(binary), "--cd", str(session_cwd), *overrides],
        cwd=session_cwd,
        env=environment,
        stdin=sys.stdin.buffer,
        stdout=sys.stdout.buffer,
        stderr=sys.stderr.buffer,
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        sys.stderr.write(
            "Native session launch refused; no credential printed or fallback selected.\n"
        )
        raise SystemExit(64) from None
