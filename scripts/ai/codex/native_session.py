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
BASE_PYTHON = Path("C:/Users/Fedor/AppData/Local/Programs/Python/Python313/python.exe")
SESSION_CLIENT = "session_client.py"
MARKDOWNIFY_CLIENT = "safe_markdownify.py"
MARKDOWNIFY_VERSIONS = Path("D:/pc-agent/tools/markdownify-owner-versions")
SESSION_VERSIONS = Path("D:/pc-agent/tools/codex-session-versions")
SHA256_PATTERN = "[0-9a-f]{64}"


def physical(path):
    if not path.is_absolute() or ".." in path.parts:
        raise PermissionError("A physical absolute native path is required")
    for part in reversed((path, *path.parents)):
        if part.is_symlink() or getattr(part, "is_junction", lambda: False)():
            raise PermissionError("Native session path traverses a reparse point")
    if path.resolve(strict=True) != path:
        raise PermissionError("A physical absolute native path is required")
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
        re.fullmatch(SHA256_PATTERN, expected) is None
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
        return json.dumps(value, allow_nan=False)
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


def _validate_markdownify_client(entry):
    args = entry["args"]
    if (
        Path(entry["command"]) != BASE_PYTHON
        or len(args) != 5
        or args[:3] != ["-I", "-S", "-B"]
        or args[-1] != "client"
    ):
        raise PermissionError("Markdownify requires its qualified isolated client")
    script = Path(args[3])
    if (
        not script.is_absolute()
        or script.name != MARKDOWNIFY_CLIENT
        or script.parent.parent != MARKDOWNIFY_VERSIONS
        or re.fullmatch(SHA256_PATTERN, script.parent.name) is None
    ):
        raise PermissionError("Markdownify requires its qualified absolute client")
    version = next(
        (path for path in MARKDOWNIFY_VERSIONS.iterdir() if path == script.parent), None
    )
    if version is None:
        raise PermissionError("Qualified Markdownify version is not installed")
    _check_client_manifest(
        version / MARKDOWNIFY_CLIENT, "owner.json", MARKDOWNIFY_CLIENT
    )


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
    _validate_markdownify_client(entry)
    if value["server"] in servers and servers[value["server"]] != entry:
        raise PermissionError("Existing unrelated Markdownify entry needs review")
    return value["server"], entry


def _check_client_manifest(script, manifest_name, required_source):
    directory = physical(script.parent)
    try:
        raw = (directory / manifest_name).read_bytes()
    except FileNotFoundError:
        raise PermissionError("Qualified selector manifest is absent") from None
    manifest = json.loads(raw)
    if hashlib.sha256(raw).hexdigest() != directory.name or manifest.get("schema") != 1:
        raise PermissionError("Qualified selector manifest changed")
    if required_source not in manifest.get("files", {}):
        raise PermissionError("Qualified selector source is unregistered")
    for relative, expected in manifest["files"].items():
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            raise PermissionError("Qualified selector source path is invalid")
        if (
            hashlib.sha256(physical(directory / path).read_bytes()).hexdigest()
            != expected
        ):
            raise PermissionError("Qualified selector source changed")
    return manifest


def _check_selector_manifest(script):
    manifest = _check_client_manifest(script, "dispatcher.json", SESSION_CLIENT)
    pins = manifest.get("host_pins", {})
    if str(BASE_PYTHON) not in pins:
        raise PermissionError("Qualified selector interpreter is unregistered")
    for path, expected in pins.items():
        if hashlib.sha256(physical(Path(path)).read_bytes()).hexdigest() != expected:
            raise PermissionError("Qualified selector host dependency changed")


def _validate_selector(name, entry):
    args = entry.get("args", [])
    if len(args) != 5 or args[:3] != ["-I", "-S", "-B"] or args[4] != name:
        raise PermissionError(
            "Native session requires its reviewed inherited-cwd selector"
        )
    script = Path(args[3])
    if (
        Path(entry.get("command", "")) != BASE_PYTHON
        or not script.is_absolute()
        or script.name != SESSION_CLIENT
        or script.parent.parent != SESSION_VERSIONS
        or re.fullmatch(SHA256_PATTERN, script.parent.name) is None
    ):
        raise PermissionError("Native session requires its qualified absolute selector")
    version = next(
        (path for path in SESSION_VERSIONS.iterdir() if path == script.parent), None
    )
    if version is None:
        raise PermissionError("Qualified selector version is not installed")
    _check_selector_manifest(version / SESSION_CLIENT)


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
        _validate_selector(name, entry)
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


def _run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--auth", choices=("api-key", "oauth"), default="api-key")
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
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
    overrides = session_overrides(config, root, acceptance=args.acceptance)
    from dotenv import dotenv_values

    values = (
        dotenv_values(physical(canonical / ".env")) if args.auth == "api-key" else {}
    )
    environment = ref_environment(os.environ, values, args.auth)
    if args.check:
        print(
            json.dumps(
                {
                    "workspace": str(root),
                    "executable": str(binary),
                    "auth": args.auth,
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


def main(argv=None):
    try:
        result = _run(argv)
        return 0 if result is None else result
    except Exception:
        sys.stderr.write(
            "Native session launch refused; no credential printed or fallback selected."
            + "\n"
        )
        return 64


if __name__ == "__main__":
    raise SystemExit(main())
