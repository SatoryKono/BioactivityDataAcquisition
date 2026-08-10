#!/usr/bin/env python3
"""Catalog-driven MCP wrapper validation, dispatch, and shim generation."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from scripts.engineering.common.platform import (
    PlatformInfo,
    PlatformKind,
    detect_platform,
    ensure_user_executable,
    script_command,
)
from scripts.engineering.common.repo_paths import (
    ensure_path_within_root,
    ensure_safe_cli_argv,
    resolve_output_path,
)

ROOT: Final[Path] = Path(__file__).resolve().parents[3]
MCP_DIR: Final[Path] = ROOT / "scripts/ai/mcp"
CATALOG_PATH: Final[Path] = ROOT / "scripts/ops/runtime/mcp/shared-servers.json"
SERVER_NAME_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9][a-z0-9-]*$")
WRAPPER_STEM_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_-]*$"
)


@dataclass(frozen=True, slots=True)
class WrapperSpec:
    """One server-to-wrapper binding from the shared MCP catalog."""

    server_name: str
    wrapper_stem: str
    order: int


def load_wrapper_specs(catalog_path: Path = CATALOG_PATH) -> dict[str, WrapperSpec]:
    """Load and validate deterministic server-to-wrapper bindings."""

    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    servers = payload.get("servers")
    if not isinstance(servers, dict) or not servers:
        raise ValueError(f"MCP catalog has no server object: {catalog_path}")

    specs: dict[str, WrapperSpec] = {}
    wrapper_owners: dict[str, str] = {}
    wrapper_orders: dict[int, str] = {}
    ordered_entries: list[tuple[int, str, dict[str, object]]] = []
    for server_name, raw_entry in servers.items():
        if not isinstance(raw_entry, dict):
            raise ValueError(f"MCP server entry must be an object: {server_name}")
        raw_order = raw_entry.get("wrapper_order")
        if (
            not isinstance(raw_order, int)
            or isinstance(raw_order, bool)
            or raw_order < 1
        ):
            raise ValueError(
                f"MCP server {server_name!r} has invalid wrapper_order: {raw_order!r}"
            )
        ordered_entries.append((raw_order, str(server_name), raw_entry))

    for wrapper_order, server_name, entry in sorted(ordered_entries):
        entry = servers[server_name]
        if not isinstance(server_name, str) or not SERVER_NAME_PATTERN.fullmatch(
            server_name
        ):
            raise ValueError(f"unsafe MCP server name: {server_name!r}")
        wrapper_stem = entry.get("wrapper")
        if not isinstance(wrapper_stem, str) or not WRAPPER_STEM_PATTERN.fullmatch(
            wrapper_stem
        ):
            raise ValueError(
                f"MCP server {server_name!r} has unsafe wrapper stem: {wrapper_stem!r}"
            )
        previous_owner = wrapper_owners.get(wrapper_stem)
        if previous_owner is not None:
            raise ValueError(
                f"MCP wrapper {wrapper_stem!r} is shared by "
                f"{previous_owner!r} and {server_name!r}"
            )
        previous_order_owner = wrapper_orders.get(wrapper_order)
        if previous_order_owner is not None:
            raise ValueError(
                f"MCP wrapper_order {wrapper_order} is shared by "
                f"{previous_order_owner!r} and {server_name!r}"
            )
        wrapper_owners[wrapper_stem] = server_name
        wrapper_orders[wrapper_order] = server_name
        specs[server_name] = WrapperSpec(server_name, wrapper_stem, wrapper_order)
    return specs


def wrapper_path(
    spec: WrapperSpec,
    *,
    host: PlatformInfo | None = None,
    mcp_dir: Path = MCP_DIR,
) -> Path:
    """Resolve a platform-specific legacy implementation without path escape."""

    resolved_host = host or detect_platform()
    path = mcp_dir / f"{spec.wrapper_stem}{resolved_host.script_suffix}"
    return ensure_path_within_root(path, mcp_dir)


def wrapper_command(
    server_name: str,
    forwarded_args: list[str] | None = None,
    *,
    host: PlatformInfo | None = None,
    specs: dict[str, WrapperSpec] | None = None,
    require_exists: bool = True,
) -> list[str]:
    """Build the native implementation command for one catalog server."""

    resolved_specs = specs or load_wrapper_specs()
    try:
        spec = resolved_specs[server_name]
    except KeyError as exc:
        raise ValueError(
            f"unknown MCP server {server_name!r}; available: "
            f"{', '.join(sorted(resolved_specs))}"
        ) from exc
    path = wrapper_path(spec, host=host)
    if require_exists and not path.is_file():
        raise FileNotFoundError(f"missing MCP wrapper implementation: {path}")
    return ensure_safe_cli_argv(
        [*script_command(path, host=host), *(forwarded_args or [])]
    )


def validate_wrapper_catalog() -> list[str]:
    """Return bounded validation errors for all configured wrapper pairs."""

    errors: list[str] = []
    try:
        specs = load_wrapper_specs()
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [str(exc)]

    hosts = (
        PlatformInfo(PlatformKind.LINUX, "posix", "linux", "fixture"),
        PlatformInfo(PlatformKind.WINDOWS, "nt", "win32", "fixture"),
    )
    for server_name in sorted(specs):
        for host in hosts:
            path = wrapper_path(specs[server_name], host=host)
            if not path.is_file():
                errors.append(
                    f"{server_name}: missing {host.kind.value} wrapper "
                    f"{path.relative_to(ROOT).as_posix()}"
                )
    return errors


def _posix_shim(server_name: str) -> str:
    root = shlex.quote(str(ROOT))
    return (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"cd -- {root}\n"
        f'exec "${{BIOETL_PYTHON:-python3}}" -m scripts.ai.mcp wrappers run '
        f'{shlex.quote(server_name)} "$@"\n'
    )


def _powershell_shim(server_name: str) -> str:
    root = str(ROOT).replace("'", "''")
    quoted_server = server_name.replace("'", "''")
    return (
        "#!/usr/bin/env pwsh\n"
        "Set-StrictMode -Version Latest\n"
        '$ErrorActionPreference = "Stop"\n'
        f"Set-Location '{root}'\n"
        "$python = if ($env:BIOETL_PYTHON) { $env:BIOETL_PYTHON } "
        "elseif (Test-Path '.venv-win/Scripts/python.exe') { "
        "'.venv-win/Scripts/python.exe' } else { 'python' }\n"
        f"& $python -m scripts.ai.mcp wrappers run '{quoted_server}' @args\n"
        "exit $LASTEXITCODE\n"
    )


def generate_wrapper_shims(output: Path) -> list[Path]:
    """Materialize deterministic compatibility shims from the JSON catalog."""

    destination = resolve_output_path(output, root=ROOT)
    destination.mkdir(parents=True, exist_ok=True)
    specs = load_wrapper_specs()
    written: list[Path] = []
    for server_name in sorted(specs):
        for suffix, content in (
            (".sh", _posix_shim(server_name)),
            (".ps1", _powershell_shim(server_name)),
        ):
            path = ensure_path_within_root(
                destination / f"{server_name}{suffix}", destination
            )
            path.write_text(content, encoding="utf-8", newline="\n")
            if suffix == ".sh":
                ensure_user_executable(path)
            written.append(path)
    manifest = ensure_path_within_root(destination / "manifest.json", destination)
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "catalog": CATALOG_PATH.relative_to(ROOT).as_posix(),
                "servers": sorted(specs),
                "generated_files": [path.name for path in written],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    written.append(manifest)
    return written


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate, run, or generate MCP wrappers from shared-servers.json."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="List catalog wrapper bindings as JSON.")
    commands.add_parser("check", help="Validate every configured .sh/.ps1 pair.")
    run = commands.add_parser("run", help="Run one platform-native wrapper.")
    run.add_argument("server", choices=sorted(load_wrapper_specs()))
    run.add_argument("args", nargs=argparse.REMAINDER)
    generate = commands.add_parser(
        "generate", help="Generate paired compatibility shims on demand."
    )
    generate.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the catalog-driven MCP wrapper CLI."""

    args = _parser().parse_args(argv)
    if args.command == "list":
        print(
            json.dumps(
                {
                    name: spec.wrapper_stem
                    for name, spec in load_wrapper_specs().items()
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "check":
        errors = validate_wrapper_catalog()
        if errors:
            for error in errors:
                print(f"mcp-wrappers: {error}", file=sys.stderr)
            return 1
        print(
            f"mcp-wrappers: ok ({len(load_wrapper_specs())} catalog bindings, "
            "both platforms)"
        )
        return 0
    if args.command == "generate":
        written = generate_wrapper_shims(args.output)
        print(
            json.dumps(
                {
                    "output": str(resolve_output_path(args.output, root=ROOT)),
                    "files": [str(path) for path in written],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    command = wrapper_command(args.server, list(args.args))
    return subprocess.run(command, check=False, env=os.environ.copy()).returncode


if __name__ == "__main__":
    raise SystemExit(main())
