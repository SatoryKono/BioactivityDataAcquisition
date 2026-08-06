#!/usr/bin/env python3
"""Read-only stability preflight for BioETL optional Docker helper stacks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONTRACT = Path("configs/quality/docker_runtime_contracts.yaml")
_WSL_EXE = "wsl.exe"
_DOCKER_FORMAT_JSON = "{{json .}}"
READ_ONLY_COMMANDS = {
    ("docker", "--version"),
    ("docker", "compose", "version"),
    ("docker", "compose", "ls"),
    ("docker", "image", "inspect"),
    ("docker", "info"),
    ("docker", "inspect"),
    ("docker", "ps"),
    (_WSL_EXE, "--status"),
    (_WSL_EXE, "--version"),
}
ENV_NAME_PATTERN = re.compile(r"\$\{([A-Za-z_]\w*)")
WINDOWS_DRIVE_PATTERN = re.compile(r"^([A-Za-z]):[/\\](.*)$")


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    message: str
    evidence: dict[str, Any]


@dataclass(frozen=True)
class CommandObservation:
    command: list[str]
    available: bool
    returncode: int | None
    stdout: str
    stderr: str


def _repo_root() -> Path:
    configured = os.environ.get("BIOETL_REPO_ROOT")
    if configured:
        return Path(configured).expanduser().absolute()
    cwd = Path.cwd()
    if (cwd / DEFAULT_CONTRACT).is_file():
        return cwd
    return Path(__file__).resolve().parents[4]


def _confined_file_bytes(path: Path, *, root: Path) -> bytes:
    """Read bytes after confining path under root (S8707)."""
    from scripts.engineering.common.repo_paths import resolve_output_path

    safe = resolve_output_path(path, root=root)
    return safe.read_bytes()  # NOSONAR - confined by resolve_output_path


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML mapping; confine under repo when possible."""
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    safe_path = resolve_output_path(path, root=REPO_ROOT)
    payload = yaml.safe_load(
        safe_path.read_text(
            encoding="utf-8"
        )  # NOSONAR - confined by resolve_output_path
    )
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a YAML mapping: {safe_path}")
    return payload


def _json_safe_text(text: str, *, limit: int | None = 4000) -> str:
    """Bound command output and redact values that resemble secret assignments."""
    stripped = text.strip()
    bounded = stripped if limit is None else stripped[:limit]
    return re.sub(
        r"(?i)(token|password|secret|key)=([^\s,;]+)",
        r"\1=<redacted>",
        bounded,
    )


def _run_read_only(command: Sequence[str], *, cwd: Path) -> CommandObservation:
    command_tuple = tuple(command)
    if not any(command_tuple[: len(prefix)] == prefix for prefix in READ_ONLY_COMMANDS):
        raise ValueError(f"Command is not in the read-only allowlist: {command!r}")
    try:
        completed = subprocess.run(  # nosec B603 - fixed read-only command allowlist
            list(command),
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return CommandObservation(
            command=list(command),
            available=False,
            returncode=None,
            stdout="",
            stderr=_json_safe_text(str(exc)),
        )
    return CommandObservation(
        command=list(command),
        available=True,
        returncode=completed.returncode,
        stdout=_json_safe_text(completed.stdout, limit=None),
        stderr=_json_safe_text(completed.stderr),
    )


def _command_evidence(observation: CommandObservation) -> dict[str, Any]:
    """Serialize bounded evidence after structured consumers parse full stdout."""
    return {
        "command": observation.command,
        "available": observation.available,
        "returncode": observation.returncode,
        "stdout": _json_safe_text(observation.stdout),
        "stderr": observation.stderr,
    }


def _volume_target(volume: Any) -> str | None:
    if isinstance(volume, str):
        parts = volume.split(":")
        return parts[1] if len(parts) >= 2 else None
    if isinstance(volume, dict):
        target = volume.get("target")
        return str(target) if target else None
    return None


def _is_bind_mount(volume: Any) -> bool:
    if isinstance(volume, dict):
        return volume.get("type") == "bind"
    if not isinstance(volume, str):
        return False
    source = volume.split(":", maxsplit=1)[0]
    return (
        source.startswith((".", "/", "~"))
        or re.match(r"^[A-Za-z]:[/\\]", source) is not None
    )


def _container_environment_names(service: Mapping[str, Any]) -> set[str]:
    names: set[str] = set()
    environment = service.get("environment", {})
    if isinstance(environment, dict):
        names.update(str(name) for name in environment)
    elif isinstance(environment, list):
        for item in environment:
            if isinstance(item, str):
                names.add(item.split("=", maxsplit=1)[0])
    return names


def _environment_names(service: Mapping[str, Any]) -> set[str]:
    names = _container_environment_names(service)
    environment = service.get("environment", {})
    if isinstance(environment, dict):
        values: Iterable[Any] = environment.values()
    elif isinstance(environment, list):
        values = environment
    else:
        values = []
    for value in values:
        if isinstance(value, str):
            names.update(ENV_NAME_PATTERN.findall(value))
    return names


def _path_origin(path: str) -> str:
    """Classify a path without reading the referenced filesystem."""
    if WINDOWS_DRIVE_PATTERN.match(path):
        return "windows-drive"
    normalized = path.replace("\\", "/").lower()
    if re.match(
        r"^(?:/mnt/[a-z]|/run/desktop/mnt/host/[a-z]|/host_mnt/[a-z])(?:/|$)",
        normalized,
    ):
        return "wsl-mounted-windows"
    return "linux"


def _normalise_path(path: str, *, root: Path) -> str:
    value = path.strip().strip('"').replace("\\", "/")
    drive_match = WINDOWS_DRIVE_PATTERN.match(value)
    if drive_match:
        drive, suffix = drive_match.groups()
        value = f"/mnt/{drive.lower()}/{suffix}"
    docker_desktop_match = re.match(
        r"^/(?:run/desktop/mnt/host|host_mnt)/([A-Za-z])(?:/(.*))?$",
        value,
        flags=re.IGNORECASE,
    )
    if docker_desktop_match:
        drive, suffix = docker_desktop_match.groups()
        value = f"/mnt/{drive.lower()}"
        if suffix:
            value = f"{value}/{suffix}"
    wsl_unc_match = re.match(
        r"^//(?:wsl\$|wsl\.localhost)/[^/]+(/.*)$",
        value,
        flags=re.IGNORECASE,
    )
    if wsl_unc_match:
        value = wsl_unc_match.group(1)
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    normalized = os.path.normcase(os.path.normpath(str(candidate)))
    if re.match(r"^/mnt/[a-z](?:/|$)", normalized, flags=re.IGNORECASE):
        return normalized.casefold()
    return normalized


def dashboard_source_environment(
    root: Path,
    contract: Mapping[str, Any],
) -> dict[str, str]:
    """Build the explicit bind-root and opaque source-identity environment."""
    data_plane = contract.get("dashboard_data_plane")
    if not isinstance(data_plane, Mapping):
        return {}
    mount_contract = data_plane.get("required_bind_mounts")
    identity_contract = data_plane.get("source_identity")
    if not isinstance(mount_contract, Mapping) or not isinstance(
        identity_contract, Mapping
    ):
        return {}

    environment: dict[str, str] = {}
    identity_mounts: dict[str, str] = {}
    for target, raw_spec in sorted(mount_contract.items(), key=lambda item: str(item[0])):
        if not isinstance(raw_spec, Mapping):
            continue
        relative_source = str(raw_spec.get("relative_source") or "").strip()
        environment_name = str(raw_spec.get("environment_name") or "").strip()
        if not relative_source or not environment_name:
            continue
        normalized_source = _normalise_path(relative_source, root=root)
        environment[environment_name] = normalized_source
        identity_mounts[str(target)] = normalized_source

    identity_environment = str(
        identity_contract.get("environment_name") or ""
    ).strip()
    schema_version = str(identity_contract.get("schema_version") or "").strip()
    if identity_environment and schema_version and identity_mounts:
        identity_payload = {
            "schema_version": schema_version,
            "repository_root": _normalise_path(str(root), root=root),
            "mounts": identity_mounts,
        }
        canonical_payload = json.dumps(
            identity_payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        environment[identity_environment] = hashlib.sha256(canonical_payload).hexdigest()
    return environment


def _is_discouraged_bind_source(path: str, discouraged: Sequence[str]) -> bool:
    normalized = path.replace("\\", "/").lower()
    return _path_origin(path) != "linux" or any(
        normalized.startswith(prefix.lower()) for prefix in discouraged
    )


def _json_rows(text: str) -> list[dict[str, Any]]:
    """Decode either a JSON array or newline-delimited JSON objects."""
    if not text.strip():
        return []
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        return [payload]
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _config_files(row: Mapping[str, Any]) -> list[str]:
    value = row.get("ConfigFiles") or row.get("ConfigFile") or []
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _project_origin_findings(
    root: Path,
    project_rows: Sequence[Mapping[str, Any]],
    contract: Mapping[str, Any],
) -> list[Finding]:
    findings: list[Finding] = []
    project_to_stack = {
        stack["project_name"]: stack_name
        for stack_name, stack in contract.get("stacks", {}).items()
    }
    legacy_names = {
        migration.get("legacy_project_name")
        for stack in contract.get("stacks", {}).values()
        if isinstance((migration := stack.get("migration")), dict)
    }
    discouraged = tuple(contract.get("path_policy", {}).get("discouraged_origins", []))
    for row in project_rows:
        project_name = str(row.get("Name") or row.get("name") or "")
        config_files = _config_files(row)
        if project_name in legacy_names:
            findings.append(
                Finding(
                    "PROJECT_ORIGIN",
                    "error",
                    "Legacy merged Compose project is still active",
                    {"project": project_name, "config_files": config_files},
                )
            )
        stack_name = project_to_stack.get(project_name)
        if not stack_name:
            continue
        expected_path = _normalise_path(
            contract["stacks"][stack_name]["compose_file"], root=root
        )
        normalized_files = {_normalise_path(path, root=root) for path in config_files}
        if normalized_files and expected_path not in normalized_files:
            findings.append(
                Finding(
                    "PROJECT_ORIGIN",
                    "error",
                    "Live Compose project originates from an unexpected config path",
                    {
                        "project": project_name,
                        "expected": expected_path,
                        "actual": sorted(normalized_files),
                    },
                )
            )
        origins = {_path_origin(path) for path in config_files}
        if len(origins) > 1:
            findings.append(
                Finding(
                    "PROJECT_ORIGIN",
                    "error",
                    "Live Compose project mixes Windows and WSL/Linux path origins",
                    {"project": project_name, "origins": sorted(origins)},
                )
            )
        bad_config_files = [
            path
            for path in config_files
            if _is_discouraged_bind_source(path, discouraged)
        ]
        if bad_config_files:
            findings.append(
                Finding(
                    "PROJECT_ORIGIN",
                    "error",
                    "Live Compose project uses a discouraged Windows-backed config path",
                    {"project": project_name, "config_files": bad_config_files},
                )
            )
    return findings


def _host_port_findings(
    listened_ports: set[int],
    port_owners: Mapping[int, tuple[str | None, str | None]],
    contract: Mapping[str, Any],
) -> list[Finding]:
    findings: list[Finding] = []
    host_port_contract = contract.get("host_ports", {})
    for raw_port, expected in host_port_contract.items():
        port = int(raw_port)
        if port not in listened_ports:
            continue
        expected_owner = (
            (expected.get("stack"), expected.get("service"))
            if isinstance(expected, dict)
            else (None, None)
        )
        actual_owner = port_owners.get(port)
        if actual_owner != expected_owner:
            findings.append(
                Finding(
                    "HOST_PORT_COLLISION",
                    "error",
                    "Contracted host port is occupied by an unknown or foreign owner",
                    {
                        "port": port,
                        "expected_owner": expected_owner,
                        "actual_owner": actual_owner,
                    },
                )
            )
    return findings


def _published_ports(service: Mapping[str, Any]) -> list[tuple[str, int, int]]:
    result: list[tuple[str, int, int]] = []
    for entry in service.get("ports", []) or []:
        if isinstance(entry, dict):
            published = entry.get("published")
            target = entry.get("target")
            if published is not None and target is not None:
                result.append(
                    (str(entry.get("host_ip", "0.0.0.0")), int(published), int(target))
                )
            continue
        if not isinstance(entry, str):
            continue
        value = entry.split("/", maxsplit=1)[0]
        parts = value.split(":")
        if len(parts) == 2:
            host, published, target = "0.0.0.0", parts[0], parts[1]
        elif len(parts) == 3:
            host, published, target = parts
        else:
            continue
        result.append((host, int(published), int(target)))
    return result


def _findings_stack_compose_shape(
    stack_name: str,
    stack_contract: Mapping[str, Any],
    services: Mapping[str, Any],
    actual_project: object,
) -> list[Finding]:
    findings: list[Finding] = []
    expected_project = stack_contract["project_name"]
    if actual_project != expected_project:
        findings.append(
            Finding(
                "F003",
                "error",
                "Compose project name differs from the runtime contract",
                {
                    "stack": stack_name,
                    "expected": expected_project,
                    "actual": actual_project,
                },
            )
        )
    expected_services = set(stack_contract.get("required_services", [])) | set(
        stack_contract.get("optional_services", [])
    )
    actual_services = set(services)
    if expected_services != actual_services:
        findings.append(
            Finding(
                "F003",
                "error",
                "Compose service set differs from its single-owner contract",
                {
                    "stack": stack_name,
                    "missing": sorted(expected_services - actual_services),
                    "unexpected": sorted(actual_services - expected_services),
                },
            )
        )
    return findings


def _findings_service_ownership(
    service_name: str,
    stack_name: str,
    *,
    declared_owners: Mapping[str, Any],
    seen_services: dict[str, str],
) -> list[Finding]:
    findings: list[Finding] = []
    owner = declared_owners.get(service_name)
    if owner != stack_name:
        findings.append(
            Finding(
                "F003",
                "error",
                "Service is declared outside its contracted owner stack",
                {"service": service_name, "stack": stack_name, "owner": owner},
            )
        )
    previous_stack = seen_services.get(service_name)
    if previous_stack and previous_stack != stack_name:
        findings.append(
            Finding(
                "F003",
                "error",
                "Service has multiple Compose owners",
                {
                    "service": service_name,
                    "stacks": sorted({previous_stack, stack_name}),
                },
            )
        )
    seen_services[service_name] = stack_name
    return findings


def _findings_container_name(
    service: Mapping[str, Any],
    service_name: str,
    stack_name: str,
    seen_container_names: dict[str, str],
) -> list[Finding]:
    container_name = service.get("container_name")
    if not container_name:
        return []
    owner_key = f"{stack_name}/{service_name}"
    previous_owner = seen_container_names.get(str(container_name))
    findings: list[Finding] = []
    if previous_owner and previous_owner != owner_key:
        findings.append(
            Finding(
                "F003",
                "error",
                "Explicit container name has multiple owners",
                {
                    "container_name": container_name,
                    "owners": [previous_owner, owner_key],
                },
            )
        )
    seen_container_names[str(container_name)] = owner_key
    return findings


def _bind_mount_source(volume: object) -> str:
    if isinstance(volume, str):
        return volume.split(":", maxsplit=1)[0]
    if isinstance(volume, Mapping):
        return str(volume.get("source", ""))
    return ""


def _findings_published_port(
    *,
    bind: str,
    published: int,
    stack_name: str,
    service_name: str,
    host_port_contract: Mapping[str, Any],
    seen_ports: dict[int, str],
) -> list[Finding]:
    findings: list[Finding] = []
    expected = host_port_contract.get(str(published))
    expected_owner = (
        f"{expected.get('stack')}/{expected.get('service')}"
        if isinstance(expected, dict)
        else None
    )
    actual_owner = f"{stack_name}/{service_name}"
    if expected_owner != actual_owner or bind != "127.0.0.1":
        findings.append(
            Finding(
                "F003",
                "error",
                "Published port differs from its localhost ownership contract",
                {
                    "port": published,
                    "actual_owner": actual_owner,
                    "expected_owner": expected_owner,
                    "bind": bind,
                },
            )
        )
    prior_port_owner = seen_ports.get(published)
    if prior_port_owner and prior_port_owner != actual_owner:
        findings.append(
            Finding(
                "F003",
                "error",
                "Published host port has multiple owners",
                {
                    "port": published,
                    "owners": [prior_port_owner, actual_owner],
                },
            )
        )
    seen_ports[published] = actual_owner
    return findings


def _observe_stack_service(
    service: Mapping[str, Any],
    *,
    service_name: str,
    stack_name: str,
    forbidden_environment_names: set[str],
    host_port_contract: Mapping[str, Any],
    seen_ports: dict[int, str],
    stack_env_names: set[str],
    stack_images: list[str],
    stack_mount_sources: list[dict[str, str]],
    stack_ports: list[dict[str, Any]],
) -> list[Finding]:
    findings: list[Finding] = []
    container_environment_names = _container_environment_names(service)
    stack_env_names.update(_environment_names(service))
    for environment_name in sorted(
        forbidden_environment_names & container_environment_names
    ):
        findings.append(
            Finding(
                "F004",
                "error",
                "Container environment variable uses an image-owned name",
                {
                    "stack": stack_name,
                    "service": service_name,
                    "name": environment_name,
                },
            )
        )
    image = service.get("image")
    if image:
        stack_images.append(str(image))
    for volume in service.get("volumes", []) or []:
        if not _is_bind_mount(volume):
            continue
        stack_mount_sources.append(
            {"service": service_name, "source": _bind_mount_source(volume)}
        )
    for bind, published, target in _published_ports(service):
        stack_ports.append(
            {
                "service": service_name,
                "bind": bind,
                "published": published,
                "target": target,
            }
        )
        findings.extend(
            _findings_published_port(
                bind=bind,
                published=published,
                stack_name=stack_name,
                service_name=service_name,
                host_port_contract=host_port_contract,
                seen_ports=seen_ports,
            )
        )
    return findings


def _findings_required_environment(
    stack_name: str,
    stack_contract: Mapping[str, Any],
    *,
    selected_stack: str | None,
    environment: Mapping[str, str],
) -> list[Finding]:
    if selected_stack not in {None, stack_name}:
        return []
    findings: list[Finding] = []
    required_values = stack_contract.get("required_non_secret_environment_values", {})
    for environment_name, expected_value in required_values.items():
        actual_value = environment.get(str(environment_name))
        evidence = {
            "stack": stack_name,
            "name": str(environment_name),
            "expected": str(expected_value),
        }
        if actual_value is None:
            findings.append(
                Finding(
                    "ENVIRONMENT_MISSING",
                    "error",
                    "Required non-secret environment variable is absent",
                    evidence,
                )
            )
        elif actual_value != str(expected_value):
            findings.append(
                Finding(
                    "ENVIRONMENT_VALUE_UNSUPPORTED",
                    "error",
                    "Environment variable has an unsupported value",
                    evidence,
                )
            )
    for secret_name in stack_contract.get("required_secret_environment_names", []):
        if secret_name not in environment:
            findings.append(
                Finding(
                    "SECRET_MISSING",
                    "error",
                    "Required secret environment variable is absent",
                    {"stack": stack_name, "name": secret_name},
                )
            )
    return findings


def _findings_shared_networks(root: Path, contract: Mapping[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    for logical_name, network_contract in contract.get("shared_networks", {}).items():
        expected_name = network_contract["name"]
        for stack_name in network_contract.get("consumers", []):
            stack_contract = contract["stacks"].get(stack_name)
            if not stack_contract:
                findings.append(
                    Finding(
                        "F003",
                        "error",
                        "Shared network references an unknown consumer stack",
                        {"network": logical_name, "stack": stack_name},
                    )
                )
                continue
            compose = _load_yaml(root / stack_contract["compose_file"])
            actual = (compose.get("networks") or {}).get(logical_name)
            if not isinstance(actual, dict):
                actual = {}
            if (
                actual.get("external") is not True
                or actual.get("name") != expected_name
            ):
                findings.append(
                    Finding(
                        "F003",
                        "error",
                        "Shared network does not resolve to its contracted external name",
                        {
                            "network": logical_name,
                            "stack": stack_name,
                            "expected_name": expected_name,
                            "actual": actual,
                        },
                    )
                )
    return findings


def _findings_codex_filesystem(
    root: Path,
    contract: Mapping[str, Any],
    compose_observations: Mapping[str, Any],
) -> list[Finding]:
    codex_contract = contract["stacks"].get("codex")
    if not codex_contract:
        return []
    codex = compose_observations.get("codex", {})
    codex_compose = _load_yaml(root / codex_contract["compose_file"])
    filesystem_service = codex_compose.get("services", {}).get("mcp-filesystem", {})
    obscuring_targets = [
        target
        for volume in filesystem_service.get("volumes", [])
        if _is_bind_mount(volume) and (target := _volume_target(volume)) == "/app"
    ]
    if not obscuring_targets:
        return []
    return [
        Finding(
            "F001",
            "error",
            "mcp-filesystem bind mount obscures /app and image-installed node_modules",
            {
                "stack": "codex",
                "service": "mcp-filesystem",
                "targets": obscuring_targets,
                "project": codex.get("project_name"),
            },
        )
    ]


def _findings_warp_dockerfile(root: Path, contract: Mapping[str, Any]) -> list[Finding]:
    main_compose = _load_yaml(root / contract["stacks"]["main"]["compose_file"])
    warp_service = main_compose.get("services", {}).get("warp", {})
    dockerfile = (
        warp_service.get("build", {}).get("dockerfile")
        if isinstance(warp_service.get("build"), dict)
        else None
    )
    if not dockerfile:
        return []
    dockerfile_text = (root / str(dockerfile)).read_text(encoding="utf-8")
    starts_cli = "warp-cli" in dockerfile_text
    starts_service = (
        re.search(r"(?:CMD|ENTRYPOINT).*warp-svc", dockerfile_text) is not None
    )
    if not (starts_cli and not starts_service):
        return []
    return [
        Finding(
            "F002",
            "error",
            "Warp image invokes warp-cli without starting warp-svc",
            {"stack": "main", "service": "warp", "dockerfile": str(dockerfile)},
        )
    ]


def _observe_one_stack(
    root: Path,
    stack_name: str,
    stack_contract: Mapping[str, Any],
    *,
    selected_stack: str | None,
    declared_owners: Mapping[str, Any],
    host_port_contract: Mapping[str, Any],
    seen_services: dict[str, str],
    seen_container_names: dict[str, str],
    seen_ports: dict[int, str],
    environment: Mapping[str, str],
) -> tuple[list[Finding], dict[str, Any] | None]:
    compose_path = root / stack_contract["compose_file"]
    if not compose_path.exists():
        return (
            [
                Finding(
                    "F003",
                    "error",
                    "Contracted Compose file is missing",
                    {"stack": stack_name, "path": str(compose_path)},
                )
            ],
            None,
        )
    compose = _load_yaml(compose_path)
    services = compose.get("services", {})
    if not isinstance(services, dict):
        services = {}
    actual_project = compose.get("name")
    findings = _findings_stack_compose_shape(
        stack_name, stack_contract, services, actual_project
    )
    stack_env_names: set[str] = set()
    forbidden_environment_names = {
        str(name)
        for name in stack_contract.get("forbidden_container_environment_names", [])
    }
    stack_ports: list[dict[str, Any]] = []
    stack_images: list[str] = []
    stack_mount_sources: list[dict[str, str]] = []
    for service_name, raw_service in services.items():
        service = raw_service if isinstance(raw_service, dict) else {}
        findings.extend(
            _findings_service_ownership(
                service_name,
                stack_name,
                declared_owners=declared_owners,
                seen_services=seen_services,
            )
        )
        findings.extend(
            _findings_container_name(
                service, service_name, stack_name, seen_container_names
            )
        )
        findings.extend(
            _observe_stack_service(
                service,
                service_name=service_name,
                stack_name=stack_name,
                forbidden_environment_names=forbidden_environment_names,
                host_port_contract=host_port_contract,
                seen_ports=seen_ports,
                stack_env_names=stack_env_names,
                stack_images=stack_images,
                stack_mount_sources=stack_mount_sources,
                stack_ports=stack_ports,
            )
        )
    findings.extend(
        _findings_required_environment(
            stack_name,
            stack_contract,
            selected_stack=selected_stack,
            environment=environment,
        )
    )
    observation = {
        "compose_file": stack_contract["compose_file"],
        "project_name": actual_project,
        "services": sorted(services),
        "environment_names": sorted(stack_env_names),
        "published_ports": stack_ports,
        "images": sorted(stack_images),
        "bind_mount_sources": stack_mount_sources,
    }
    return findings, observation


def _static_observations(
    root: Path,
    contract: Mapping[str, Any],
    *,
    selected_stack: str | None = None,
) -> tuple[list[Finding], dict[str, Any]]:
    findings: list[Finding] = []
    compose_observations: dict[str, Any] = {}
    seen_services: dict[str, str] = {}
    seen_container_names: dict[str, str] = {}
    seen_ports: dict[int, str] = {}
    declared_owners = contract.get("service_ownership", {})
    host_port_contract = contract.get("host_ports", {})
    environment = os.environ

    for stack_name, stack_contract in contract["stacks"].items():
        stack_findings, observation = _observe_one_stack(
            root,
            stack_name,
            stack_contract,
            selected_stack=selected_stack,
            declared_owners=declared_owners,
            host_port_contract=host_port_contract,
            seen_services=seen_services,
            seen_container_names=seen_container_names,
            seen_ports=seen_ports,
            environment=environment,
        )
        findings.extend(stack_findings)
        if observation is not None:
            compose_observations[stack_name] = observation

    findings.extend(_findings_shared_networks(root, contract))
    findings.extend(_findings_codex_filesystem(root, contract, compose_observations))
    findings.extend(_findings_warp_dockerfile(root, contract))
    return findings, compose_observations


def _docker_root_and_disk(
    root: Path,
) -> tuple[str | None, Any | None, list[Finding]]:
    docker_info = _run_read_only(
        ["docker", "info", "--format", _DOCKER_FORMAT_JSON], cwd=root
    )
    docker_root: str | None = None
    findings: list[Finding] = []
    if docker_info.returncode == 0:
        try:
            info_payload = json.loads(docker_info.stdout)
        except json.JSONDecodeError:
            info_payload = {}
        if isinstance(info_payload, dict):
            candidate = info_payload.get("DockerRootDir")
            docker_root = str(candidate) if candidate else None
    if not docker_root:
        findings.append(
            Finding(
                "CAPACITY_DOCKER_ROOT",
                "error",
                "Docker data root is unavailable; capacity gate fails closed",
                {"error": docker_info.stderr or "DockerRootDir missing"},
            )
        )
        return None, None, findings
    try:
        return docker_root, shutil.disk_usage(docker_root), findings
    except OSError as exc:
        findings.append(
            Finding(
                "CAPACITY_DOCKER_ROOT",
                "error",
                "Docker data root capacity cannot be measured from this host",
                {
                    "docker_root_dir": docker_root,
                    "error": _json_safe_text(str(exc)),
                },
            )
        )
        return docker_root, None, findings


def _available_memory_bytes() -> int | None:
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        return None
    match = re.search(
        r"^MemAvailable:\s+(\d+)\s+kB$",
        meminfo.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    if match:
        return int(match.group(1)) * 1024
    return None


def _capacity_threshold_findings(
    *,
    docker_root: str | None,
    docker_disk: Any | None,
    memory_bytes: int | None,
    minimum_disk: int,
    absolute_minimum: int,
    percentage_minimum: int,
    minimum_memory: int,
) -> list[Finding]:
    findings: list[Finding] = []
    if docker_disk is not None and docker_disk.free < minimum_disk:
        findings.append(
            Finding(
                "CAPACITY_DISK",
                "error",
                "Docker data root free space is below the stability threshold",
                {
                    "docker_root_dir": docker_root,
                    "free_bytes": docker_disk.free,
                    "minimum_bytes": minimum_disk,
                    "absolute_minimum_bytes": absolute_minimum,
                    "percentage_minimum_bytes": percentage_minimum,
                },
            )
        )
    if memory_bytes is not None and memory_bytes < minimum_memory:
        findings.append(
            Finding(
                "CAPACITY_MEMORY",
                "error",
                "Available memory is below the contract threshold",
                {"available_bytes": memory_bytes, "minimum_bytes": minimum_memory},
            )
        )
    return findings


def _capacity_observation(
    root: Path, contract: Mapping[str, Any]
) -> tuple[dict[str, Any], list[Finding]]:
    capacity_contract = contract.get("capacity", {})
    docker_root, docker_disk, findings = _docker_root_and_disk(root)
    memory_bytes = _available_memory_bytes()
    observation = {
        "cpus": os.cpu_count(),
        "docker_root_dir": docker_root,
        "docker_total_bytes": docker_disk.total if docker_disk else None,
        "docker_free_bytes": docker_disk.free if docker_disk else None,
        "available_memory_bytes": memory_bytes,
        "thresholds": capacity_contract,
    }
    absolute_minimum = int(capacity_contract.get("minimum_free_disk_gib", 0)) * 1024**3
    percent = int(capacity_contract.get("minimum_free_disk_percent", 0))
    percentage_minimum = (
        docker_disk.total * percent // 100 if docker_disk is not None else 0
    )
    minimum_disk = max(absolute_minimum, percentage_minimum)
    observation["required_free_disk_bytes"] = minimum_disk
    minimum_memory = int(capacity_contract.get("minimum_free_memory_gib", 0)) * 1024**3
    minimum_cpus = int(capacity_contract.get("minimum_cpus", 0))
    findings.extend(
        _capacity_threshold_findings(
            docker_root=docker_root,
            docker_disk=docker_disk,
            memory_bytes=memory_bytes,
            minimum_disk=minimum_disk,
            absolute_minimum=absolute_minimum,
            percentage_minimum=percentage_minimum,
            minimum_memory=minimum_memory,
        )
    )
    if (os.cpu_count() or 0) < minimum_cpus:
        findings.append(
            Finding(
                "CAPACITY_CPU",
                "error",
                "CPU count is below the contract threshold",
                {"cpus": os.cpu_count(), "minimum": minimum_cpus},
            )
        )
    return observation, findings


def _probe_docker_commands(root: Path) -> list[Any]:
    """Run the fixed docker/wsl read-only probe command matrix."""
    commands = [
        ["docker", "--version"],
        ["docker", "compose", "version"],
        ["docker", "info", "--format", _DOCKER_FORMAT_JSON],
        ["docker", "compose", "ls", "--all", "--format", "json"],
        ["docker", "ps", "--all", "--format", _DOCKER_FORMAT_JSON],
        [_WSL_EXE, "--version"],
        [_WSL_EXE, "--status"],
    ]
    return [_run_read_only(command, cwd=root) for command in commands]


def _daemon_unavailable_findings(info_result: Any) -> list[Finding]:
    if info_result.available and info_result.returncode == 0:
        return []
    return [
        Finding(
            "DOCKER_DAEMON",
            "warning",
            "Docker daemon is unavailable; static contract checks still ran",
            {"error": info_result.stderr or "docker command unavailable"},
        )
    ]


def _compose_image_refs(compose: Mapping[str, Any]) -> list[str]:
    return sorted(
        {image for stack in compose.values() for image in stack.get("images", [])}
    )


def _inspect_image_results(root: Path, image_refs: list[str]) -> list[Any]:
    return [
        _run_read_only(
            ["docker", "image", "inspect", "--format", "{{.Id}}", image], cwd=root
        )
        for image in image_refs
    ]


def _container_ids_from_ps_stdout(stdout: str) -> list[str]:
    container_ids: list[str] = []
    for line in stdout.splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        container_id = row.get("ID")
        if container_id:
            container_ids.append(str(container_id))
    return container_ids


_CONTAINER_INSPECT_FORMAT = (
    '{"name":{{json .Name}},"state":{{json .State.Status}},'
    '"exit_code":{{json .State.ExitCode}},"oom_killed":{{json .State.OOMKilled}},'
    '"restart_count":{{json .RestartCount}},'
    '"health":{{if .State.Health}}{{json .State.Health.Status}}{{else}}"none"{{end}},'
    '"project":{{json (index .Config.Labels "com.docker.compose.project")}},'
    '"service":{{json (index .Config.Labels "com.docker.compose.service")}},'
    '"dashboard_source_id":{{json (index .Config.Labels "io.bioetl.dashboard-source-id")}},'
    '"ports":{{json .NetworkSettings.Ports}},"mounts":{{json .Mounts}}}'
)


def _container_health_findings(observation: Mapping[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if observation.get("oom_killed"):
        findings.append(
            Finding(
                "CONTAINER_OOM",
                "error",
                "Container was OOM-killed",
                {"name": observation.get("name")},
            )
        )
    if int(observation.get("restart_count", 0)) > 0:
        findings.append(
            Finding(
                "CONTAINER_RESTART",
                "warning",
                "Container restart count is non-zero",
                {
                    "name": observation.get("name"),
                    "restart_count": observation.get("restart_count"),
                },
            )
        )
    if observation.get("health") == "unhealthy":
        findings.append(
            Finding(
                "CONTAINER_HEALTH",
                "error",
                "Container is unhealthy",
                {"name": observation.get("name")},
            )
        )
    return findings


def _inspect_running_containers(
    root: Path, container_ids: list[str]
) -> tuple[list[dict[str, Any]], list[Finding]]:
    findings: list[Finding] = []
    containers: list[dict[str, Any]] = []
    for container_id in container_ids:
        result = _run_read_only(
            ["docker", "inspect", "--format", _CONTAINER_INSPECT_FORMAT, container_id],
            cwd=root,
        )
        if result.returncode != 0:
            continue
        try:
            observation = json.loads(result.stdout)
        except json.JSONDecodeError:
            continue
        containers.append(observation)
        findings.extend(_container_health_findings(observation))
    return containers, findings


def _listened_host_ports() -> set[int]:
    listened_ports: set[int] = set()
    for proc_path in (Path("/proc/net/tcp"), Path("/proc/net/tcp6")):
        if not proc_path.exists():
            continue
        for line in proc_path.read_text(encoding="utf-8").splitlines()[1:]:
            columns = line.split()
            if len(columns) >= 4 and columns[3] == "0A":
                listened_ports.add(int(columns[1].split(":", maxsplit=1)[1], 16))
    return listened_ports


def _contracted_published_ports(compose: Mapping[str, Any]) -> list[int]:
    return sorted(
        int(item["published"])
        for stack in compose.values()
        for item in stack.get("published_ports", [])
    )


def _project_to_stack_map(contract: Mapping[str, Any]) -> dict[Any, Any]:
    return {
        stack["project_name"]: stack_name
        for stack_name, stack in contract.get("stacks", {}).items()
    }


def _port_owners_from_containers(
    containers: list[dict[str, Any]],
    project_to_stack: Mapping[Any, Any],
) -> dict[int, tuple[str | None, str | None]]:
    port_owners: dict[int, tuple[str | None, str | None]] = {}
    for container in containers:
        if container.get("state") != "running":
            continue
        for bindings in (container.get("ports") or {}).values():
            for binding in bindings or []:
                try:
                    port = int(binding["HostPort"])
                except (KeyError, TypeError, ValueError):
                    continue
                port_owners[port] = (
                    project_to_stack.get(container.get("project")),
                    container.get("service"),
                )
    return port_owners


def _mount_origin_findings(
    containers: list[dict[str, Any]],
    *,
    project_to_stack: Mapping[Any, Any],
    discouraged: tuple[Any, ...],
) -> list[Finding]:
    findings: list[Finding] = []
    for container in containers:
        stack_name = project_to_stack.get(container.get("project"))
        if not stack_name:
            continue
        mount_sources = [
            str(mount.get("Source", ""))
            for mount in container.get("mounts", [])
            if isinstance(mount, dict) and mount.get("Type") == "bind"
        ]
        origins = {_path_origin(path) for path in mount_sources if path}
        if len(origins) > 1:
            findings.append(
                Finding(
                    "MOUNT_ORIGIN",
                    "error",
                    "Contracted project mixes bind-mount path origins",
                    {"stack": stack_name, "origins": sorted(origins)},
                )
            )
        bad_sources = [
            path
            for path in mount_sources
            if _is_discouraged_bind_source(path, discouraged)
        ]
        if bad_sources:
            findings.append(
                Finding(
                    "MOUNT_ORIGIN",
                    "error",
                    "Contracted project uses a discouraged Windows-backed bind source",
                    {"stack": stack_name, "sources": sorted(bad_sources)},
                )
            )
    return findings


def _dashboard_source_findings(
    root: Path,
    containers: list[dict[str, Any]],
    *,
    contract: Mapping[str, Any],
    project_to_stack: Mapping[Any, Any],
) -> list[Finding]:
    """Reject a healthy producer when it serves another checkout's artifacts."""
    data_plane = contract.get("dashboard_data_plane")
    if not isinstance(data_plane, Mapping):
        return []
    producer_stack = str(data_plane.get("producer_stack") or "")
    producer_service = str(data_plane.get("producer_service") or "")
    required_mounts = data_plane.get("required_bind_mounts")
    identity_contract = data_plane.get("source_identity")
    if not isinstance(required_mounts, Mapping) or not isinstance(
        identity_contract, Mapping
    ):
        return []

    expected_environment = dashboard_source_environment(root, contract)
    identity_environment = str(
        identity_contract.get("environment_name") or ""
    ).strip()
    expected_identity = expected_environment.get(identity_environment)
    unmanaged_value = str(identity_contract.get("unmanaged_value") or "unmanaged")
    findings: list[Finding] = []
    for container in containers:
        stack_name = project_to_stack.get(container.get("project"))
        if stack_name != producer_stack or container.get("service") != producer_service:
            continue
        mounts_by_target = {
            str(mount.get("Destination") or ""): str(mount.get("Source") or "")
            for mount in container.get("mounts", [])
            if isinstance(mount, Mapping) and mount.get("Type") == "bind"
        }
        for target, raw_spec in required_mounts.items():
            if not isinstance(raw_spec, Mapping):
                continue
            relative_source = str(raw_spec.get("relative_source") or "").strip()
            if not relative_source:
                continue
            target_text = str(target)
            expected_source = _normalise_path(relative_source, root=root)
            actual_source = mounts_by_target.get(target_text)
            normalized_actual = (
                _normalise_path(actual_source, root=root) if actual_source else None
            )
            if normalized_actual != expected_source:
                findings.append(
                    Finding(
                        "DASHBOARD_SOURCE_MOUNT",
                        "error",
                        "Dashboard producer bind mount originates from another runtime root",
                        {
                            "stack": producer_stack,
                            "service": producer_service,
                            "target": target_text,
                            "expected": expected_source,
                            "actual": normalized_actual,
                        },
                    )
                )
        actual_identity = str(container.get("dashboard_source_id") or "")
        if not expected_identity or actual_identity in {"", unmanaged_value}:
            findings.append(
                Finding(
                    "DASHBOARD_SOURCE_IDENTITY",
                    "error",
                    "Dashboard producer does not expose a managed source identity",
                    {
                        "stack": producer_stack,
                        "service": producer_service,
                        "expected": expected_identity,
                        "actual": actual_identity or None,
                    },
                )
            )
        elif actual_identity != expected_identity:
            findings.append(
                Finding(
                    "DASHBOARD_SOURCE_IDENTITY",
                    "error",
                    "Dashboard producer source identity does not match this runtime root",
                    {
                        "stack": producer_stack,
                        "service": producer_service,
                        "expected": expected_identity,
                        "actual": actual_identity,
                    },
                )
            )
    return findings


def _live_observations(
    root: Path, compose: Mapping[str, Any], contract: Mapping[str, Any]
) -> tuple[dict[str, Any], list[Finding]]:
    command_results = _probe_docker_commands(root)
    findings: list[Finding] = []
    findings.extend(_daemon_unavailable_findings(command_results[2]))

    image_refs = _compose_image_refs(compose)
    image_results = _inspect_image_results(root, image_refs)
    container_ids = _container_ids_from_ps_stdout(command_results[4].stdout)
    containers, container_findings = _inspect_running_containers(root, container_ids)
    findings.extend(container_findings)

    listened_ports = _listened_host_ports()
    contracted_ports = _contracted_published_ports(compose)
    project_to_stack = _project_to_stack_map(contract)
    port_owners = _port_owners_from_containers(containers, project_to_stack)
    findings.extend(_host_port_findings(listened_ports, port_owners, contract))

    project_rows = _json_rows(command_results[3].stdout)
    findings.extend(_project_origin_findings(root, project_rows, contract))

    discouraged = tuple(contract.get("path_policy", {}).get("discouraged_origins", []))
    findings.extend(
        _mount_origin_findings(
            containers,
            project_to_stack=project_to_stack,
            discouraged=discouraged,
        )
    )
    findings.extend(
        _dashboard_source_findings(
            root,
            containers,
            contract=contract,
            project_to_stack=project_to_stack,
        )
    )
    return {
        "commands": [_command_evidence(result) for result in command_results],
        "images": [
            {
                "reference": image,
                "available": result.returncode == 0,
                "image_id": result.stdout,
            }
            for image, result in zip(image_refs, image_results, strict=True)
        ],
        "containers": containers,
        "compose_projects": project_rows,
        "host_ports": [
            {"port": port, "listening": port in listened_ports}
            for port in contracted_ports
        ],
    }, findings


def build_report(
    root: Path,
    contract_path: Path,
    *,
    static_only: bool,
    selected_stack: str | None = None,
) -> dict[str, Any]:
    contract = _load_yaml(contract_path)
    if selected_stack is not None and selected_stack not in contract["stacks"]:
        raise ValueError(f"Unknown contracted Docker stack: {selected_stack}")
    findings, compose = _static_observations(
        root, contract, selected_stack=selected_stack
    )
    capacity, capacity_findings = _capacity_observation(root, contract)
    findings.extend(capacity_findings)
    live: dict[str, Any] = {"skipped": True}
    if not static_only:
        live, live_findings = _live_observations(root, compose, contract)
        findings.extend(live_findings)
    errors = sum(finding.severity == "error" for finding in findings)
    warnings = sum(finding.severity == "warning" for finding in findings)
    return {
        "schema_version": "docker-stability-baseline-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "repository": str(root),
        "contract": {
            "path": str(contract_path.relative_to(root)),
            "sha256": hashlib.sha256(
                _confined_file_bytes(contract_path, root=root)
            ).hexdigest(),
            "canonical_runtime": contract["policy"]["canonical_runtime"],
            "selected_stack": selected_stack,
        },
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "wsl": "microsoft" in platform.release().lower(),
        },
        "capacity": capacity,
        "compose": compose,
        "live": live,
        "findings": [asdict(finding) for finding in findings],
        "summary": {"errors": errors, "warnings": warnings, "ok": errors == 0},
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--repo-root", type=Path, help="Override repository root")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--stack",
        help="Require secrets only for this stack while retaining global contract checks",
    )
    parser.add_argument(
        "--static-only",
        action="store_true",
        help="Skip project/container/image observations; Docker data-root capacity still runs",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    root = args.repo_root.absolute() if args.repo_root else _repo_root()
    contract_path = (
        args.contract if args.contract.is_absolute() else root / args.contract
    )
    try:
        report = build_report(
            root,
            contract_path,
            static_only=args.static_only,
            selected_stack=args.stack,
        )
    except (KeyError, OSError, ValueError, yaml.YAMLError) as exc:
        print(f"docker runtime preflight: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        output_path = args.output if args.output.is_absolute() else root / args.output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0 if report["summary"]["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
