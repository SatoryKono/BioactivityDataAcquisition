"""Secret-minimized MCP route evidence projected from native Codex resolution.

This module does not merge TOML, select a competing transport, deduplicate
profiles, or claim tool readiness. Native config/read owns those decisions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
from typing import Any
from urllib.parse import urlsplit

from scripts.ai.codex.native_mcp_config import ConfigCapture

RESOLVER_VERSION = "native-config-read/v1"
_POLICY_FIELDS = (
    "enabled",
    "enabled_tools",
    "disabled_tools",
    "startup_timeout_sec",
    "tool_timeout_sec",
    "required",
    "defer_loading",
)
_SAFE_ENV = frozenset(
    {
        "PROJECT_PATH",
        "ADR_PATH",
        "ADR_DIRECTORY",
        "GITHUB_TOOLSETS",
        "GITHUB_EXCLUDE_TOOLS",
        "GITHUB_READ_ONLY",
        "GITHUB_LOCKDOWN_MODE",
        "BIOETL_AI_MEMORY_MODE",
        "MEMORY_SEED_PATH",
        "MEMORY_FILE_PATH",
    }
)
_SOURCE_FIELDS = ("type", "file", "dotCodexFolder", "profile", "id", "name")
_INSTANCE_FIELDS = (
    "generation",
    "owner_pid",
    "owner_birth",
    "gateway_pid",
    "gateway_birth",
    "backend_pid",
    "backend_birth",
    "pid",
    "birth",
    "service",
    "profile",
    "observed_utc",
)
_SAFE_WORDS = frozenset(
    {
        "-I",
        "-S",
        "-B",
        "-u",
        "--stdio",
        "--production",
        "client",
        "owner",
        "status",
        "context7",
        "ast-grep",
        "adr-analysis",
        "code-analyzer",
    }
)
_VARIABLE = re.compile(r"[A-Za-z_]\w*\Z", re.ASCII)
_PROFILE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}\Z")
_MEMORY_PROJECT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z")
_SECRET_FLAG = re.compile(r"token|password|secret|api[-_]?key|authorization", re.I)
_BINARY_NAMES = frozenset(
    {
        "python",
        "python3",
        "node",
        "npx",
        "uv",
        "uvx",
        "pwsh",
        "powershell",
        "bash",
        "docker",
        "codex",
    }
)


def _digest(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _source(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    return {key: value[key] for key in _SOURCE_FIELDS if key in value}


def _path_argument(value: str) -> bool:
    if "\n" in value or "\r" in value or "://" in value:
        return False
    return Path(value).is_absolute() or PureWindowsPath(value).is_absolute()


def _argument(value: str, previous: str) -> tuple[str, bool]:
    if _SECRET_FLAG.search(previous) or previous in {"-c", "-e", "--eval", "--command"}:
        return "[omitted]", False
    if previous == "--profile" and _PROFILE.fullmatch(value):
        return value, True
    if value in _SAFE_WORDS:
        return value, True
    if value in {"--profile", "--root", "--workspace"}:
        return value, True
    if value.startswith("-"):
        # Attached -c/-e code and unknown option names may contain secrets too.
        return "[opaque option]", False
    if _path_argument(value) and (
        previous in {"--root", "--workspace"}
        or Path(value).suffix.lower()
        in {".py", ".mjs", ".js", ".ps1", ".sh", ".cmd", ".exe"}
    ):
        return value, True
    return "[opaque argument]", False


def _arguments(values: object) -> tuple[list[str], bool]:
    if not isinstance(values, list) or not all(
        isinstance(value, str) for value in values
    ):
        return [], False
    result: list[str] = []
    complete = True
    previous = ""
    for value in values:
        projected, retained = _argument(value, previous)
        result.append(projected)
        complete = complete and retained
        previous = value.split("=", 1)[0]
    return result, complete


def _memory_workspace_options(values: object) -> list[str] | None:
    """Recognize only the pinned scoped client's explicit workspace selector.

    These identifiers are not globally safe CLI arguments. Unknown adapters,
    malformed selectors and additional options retain normal opaque handling.
    The selected branch-specific registration still needs runtime evidence.
    """
    if not isinstance(values, list) or len(values) != 10:
        return None
    if not all(isinstance(value, str) for value in values):
        return None
    valid = (
        values[:3] == ["-I", "-S", "-B"],
        _path_argument(values[3]),
        Path(values[3].replace("\\", "/")).name == "project-memory-scoped-client.py",
        values[4::2] == ["--workspace", "--project", "--policy"],
        _path_argument(values[5]),
        bool(_MEMORY_PROJECT.fullmatch(values[7])),
        values[9] in {"read-only", "read-write"},
    )
    return values[6:] if all(valid) else None


def _service_address(value: object) -> tuple[str | None, bool]:
    if not isinstance(value, str):
        return None, False
    try:
        url = urlsplit(value)
        if url.scheme not in {"http", "https"} or not url.hostname:
            return None, False
        host = "[" + url.hostname + "]" if ":" in url.hostname else url.hostname
        port = ":" + str(url.port) if url.port is not None else ""
        path = url.path if url.path in {"", "/", "/mcp", "/sse"} else "/[path omitted]"
        complete = not (
            url.username
            or url.password
            or url.query
            or url.fragment
            or path != url.path
        )
        return url.scheme + "://" + host + port + path, complete
    except ValueError:
        return None, False


def _transport(entry: Mapping[str, Any]) -> tuple[dict[str, object], bool]:
    projected: dict[str, object] = {}
    complete = True
    command = entry.get("command")
    if isinstance(command, str):
        if _path_argument(command) or command in _BINARY_NAMES:
            projected["command"] = command
        else:
            projected["command"] = "[opaque command]"
            complete = False
        projected["transport"] = "stdio"
        args = entry.get("args", [])
        positional_profile = _positional_profile(entry)
        memory_options = _memory_workspace_options(args)
        if memory_options:
            arguments, args_complete = _arguments(args[:6])
            arguments.extend(memory_options)
        elif positional_profile:
            # Only the registered controllers define this final value as a
            # profile identity. Earlier omitted arguments still make the
            # projection incomplete.
            arguments, args_complete = _arguments(args[:-1])
            arguments.append(positional_profile)
        else:
            arguments, args_complete = _arguments(args)
        projected["args"] = arguments
        complete = complete and args_complete
    elif "url" in entry:
        projected["transport"] = "http"
        projected["url"], complete = _service_address(entry["url"])
    else:
        complete = False
    return projected, complete


def _environment(entry: Mapping[str, Any]) -> dict[str, object]:
    projected: dict[str, object] = {}
    env = entry.get("env", {})
    if isinstance(env, Mapping):
        projected["env_names"] = sorted(env)
        projected["scope_env"] = {
            key: env[key] for key in sorted(env) if key in _SAFE_ENV
        }
    projected["inherited_env_names"] = sorted(entry.get("env_vars", []) or [])
    return projected


def _authorization(entry: Mapping[str, Any]) -> tuple[dict[str, object], bool]:
    projected: dict[str, object] = {}
    headers = entry.get("env_http_headers", {}) or {}
    projected["auth_env_references"] = (
        {
            str(key): value
            for key, value in headers.items()
            if isinstance(value, str) and _VARIABLE.fullmatch(value)
        }
        if isinstance(headers, Mapping)
        else {}
    )
    token_env = entry.get("bearer_token_env_var")
    if isinstance(token_env, str) and _VARIABLE.fullmatch(token_env):
        projected["bearer_env_reference"] = token_env
    inline = entry.get("http_headers", {}) or {}
    projected["inline_header_names"] = (
        sorted(inline) if isinstance(inline, Mapping) else []
    )
    return projected, not (inline or entry.get("http_headers_helper"))


def transport_projection(entry: Mapping[str, Any]) -> tuple[dict[str, object], bool]:
    """Project non-secret selection inputs; flag intentionally omitted arguments."""
    projected, transport_complete = _transport(entry)
    positional_profile = _positional_profile(entry)
    if positional_profile:
        # These registered controller CLIs define the final client argument as
        # an opaque profile identity, not a credential or arbitrary free text.
        projected["adapter_profile_reference"] = positional_profile
    authorization, auth_complete = _authorization(entry)
    projected.update(authorization)
    projected.update(_environment(entry))
    projected.update({key: entry[key] for key in _POLICY_FIELDS if key in entry})
    if isinstance(entry.get("cwd"), str):
        projected["cwd"] = entry["cwd"]
    return projected, transport_complete and auth_complete


def _origins(payload: Mapping[str, Any], name: str) -> dict[str, object]:
    prefix = "mcp_servers." + name + "."
    return {
        key.removeprefix(prefix): _source(value.get("name"))
        for key, value in sorted(payload.get("origins", {}).items())
        if key.startswith(prefix) and isinstance(value, Mapping)
    }


def _positional_profile(entry: Mapping[str, Any]) -> str | None:
    args = entry.get("args", [])
    if not isinstance(args, list) or len(args) < 3:
        return None
    profile = args[-1]
    if (
        args[-2] != "client"
        or not isinstance(profile, str)
        or not _PROFILE.fullmatch(profile)
    ):
        return None
    adapters = {"deja-owner.py", "filesystem-owner.py"}
    names = {
        Path(arg.replace("\\", "/")).name for arg in args[:-2] if isinstance(arg, str)
    }
    return profile if adapters & names else None


def _adapter_profile(entry: Mapping[str, Any]) -> str | None:
    args = entry.get("args", [])
    if not isinstance(args, list):
        return None
    for index, value in enumerate(args[:-1]):
        following = args[index + 1]
        if (
            value == "--profile"
            and isinstance(following, str)
            and _PROFILE.fullmatch(following)
        ):
            return following
    return _positional_profile(entry)


def _declarations(payload: Mapping[str, Any], name: str) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for layer in payload.get("layers", []) or []:
        entry = layer.get("config", {}).get("mcp_servers", {}).get(name)
        if isinstance(entry, Mapping):
            projection, complete = transport_projection(entry)
            result.append(
                {
                    "source": _source(layer.get("name")),
                    "disabled_reason": "native layer disabled"
                    if layer.get("disabledReason")
                    else None,
                    "declaration": projection,
                    "projection_complete": complete,
                }
            )
    return result


def route_snapshot(
    capture: ConfigCapture,
    *,
    expected: Sequence[str],
    project_profile: str,
    auth_references: Mapping[str, str] | None = None,
    instances: Mapping[str, Mapping[str, object]] | None = None,
) -> dict[str, object]:
    """Describe native choices; instance identities never enter selection hashes."""
    servers = capture.payload.get("config", {}).get("mcp_servers", {})
    if not isinstance(servers, Mapping):
        raise ValueError("native mcp_servers must be an object")
    references = auth_references or {}
    instance_records = instances or {}
    routes: dict[str, object] = {}
    for name, entry in sorted(servers.items()):
        if not isinstance(name, str) or not isinstance(entry, Mapping):
            raise ValueError("invalid native MCP server entry")
        projection, complete = transport_projection(entry)
        selection = {
            "resolver_version": RESOLVER_VERSION,
            "native_version": capture.native_version,
            "workspace": str(capture.workspace),
            "expected_project_profile": project_profile,
            "server": name,
            "transport": projection,
            "origins": _origins(capture.payload, name),
            "declarations": _declarations(capture.payload, name),
            "authorization_reference": references.get(name),
            "chain": {
                "client": "native Codex config/read",
                "adapter": projection.get("command") or projection.get("url"),
                "gateway": "NOT_TESTED",
                "backend": "NOT_TESTED",
                "profile": {
                    "expected_project_profile": project_profile,
                    "adapter_profile": _adapter_profile(entry),
                    "native_profiles": sorted(
                        {
                            source.get("profile")
                            for source in _origins(capture.payload, name).values()
                            if isinstance(source, Mapping)
                            and isinstance(source.get("profile"), str)
                        }
                    ),
                },
            },
        }
        instance = instance_records.get(name, {})
        routes[name] = {
            "selection": selection,
            "selection_fingerprint": _digest(selection),
            "projection_complete": complete,
            "runtime_instance": {
                key: instance[key] for key in _INSTANCE_FIELDS if key in instance
            },
            "backend_identity_verified": False,
            "tool_status": "NOT_TESTED",
        }
    names = set(servers)
    expected_names = set(expected)
    return {
        "schema_version": 1,
        "authority": capture.authority,
        "readiness_level": "configuration",
        "session_tool_readiness": "NOT_TESTED",
        "workspace": str(capture.workspace),
        "expected": sorted(expected_names),
        "effective": sorted(names),
        "missing": sorted(expected_names - names),
        "additional": sorted(names - expected_names),
        "disabled": sorted(
            name
            for name, entry in servers.items()
            if entry.get("enabled", True) is False
        ),
        "routes": routes,
    }


def changed_routes(before: ConfigCapture, after: ConfigCapture) -> list[str]:
    """Detect private credential/config changes without publishing their hashes."""
    old = before.payload.get("config", {}).get("mcp_servers", {})
    new = after.payload.get("config", {}).get("mcp_servers", {})
    names = set(old) | set(new)
    if (
        before.workspace != after.workspace
        or before.native_version != after.native_version
    ):
        return sorted(names)
    return sorted(
        name
        for name in names
        if old.get(name) != new.get(name)
        or _origins(before.payload, name) != _origins(after.payload, name)
    )
