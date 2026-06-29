"""Canonical validated loader for configs/base/contract_registry.yaml."""

from __future__ import annotations

import os
import threading
from pathlib import Path

import yaml

from bioetl.domain.types import JsonDict

DEFAULT_CONTRACT_REGISTRY_PATH = Path("configs/base/contract_registry.yaml")
_CONTRACT_REGISTRY_PATH_FROM_CONFIGS_ROOT = DEFAULT_CONTRACT_REGISTRY_PATH.relative_to(
    "configs"
)

_YAML_LOAD_TIMEOUT_SECONDS = 30.0


def _is_likely_network_drive(path: Path) -> bool:
    """Detect if a path is likely on a network drive (Windows only)."""
    if os.name != "nt":
        return False
    try:
        # Check if the drive root is a network drive
        drive = path.drive if path.drive else os.path.splitdrive(str(path))[0]
        if not drive:
            return False
        # UNC paths (\\server\share) are network paths
        if str(path).startswith("\\\\"):
            return True
        # Check drive type using Windows API
        import ctypes
        from ctypes import wintypes

        DRIVE_REMOTE = 4
        kernel32 = ctypes.windll.kernel32
        kernel32.GetDriveTypeW.argtypes = [wintypes.LPCWSTR]
        kernel32.GetDriveTypeW.restype = wintypes.DWORD

        drive_type = kernel32.GetDriveTypeW(drive + "\\")
        return drive_type == DRIVE_REMOTE
    except (OSError, AttributeError, TypeError):
        # If detection fails, assume local to avoid false positives
        return False


def _load_yaml_with_timeout(path: Path, timeout: float = _YAML_LOAD_TIMEOUT_SECONDS) -> JsonDict:
    """Load YAML file with timeout protection for network drives."""
    if not _is_likely_network_drive(path):
        # Direct read for local drives
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    # Timeout-protected read for network drives
    result: JsonDict | None = None
    exception: Exception | None = None

    def _target() -> None:
        nonlocal result, exception
        try:
            result = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError, ValueError) as e:
            exception = e

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        raise TimeoutError(f"YAML load did not complete within {timeout} seconds: {path}")

    if exception is not None:
        raise exception

    if result is None:
        raise ValueError(f"YAML load returned None: {path}")

    return result

__all__ = [
    "DEFAULT_CONTRACT_REGISTRY_PATH",
    "load_contract_registry_entries",
    "load_contract_registry_entry",
    "load_contract_registry_payload",
    "resolve_contract_registry_path",
    "try_load_contract_registry_entries",
    "try_load_contract_registry_payload",
]


def resolve_contract_registry_path(
    registry_path: Path | None = None,
    *,
    repo_root: Path | None = None,
    configs_root: Path | None = None,
) -> Path:
    """Resolve the canonical contract-registry path from one explicit root."""
    if registry_path is not None:
        return registry_path
    if repo_root is not None and configs_root is not None:
        raise ValueError("Pass either repo_root or configs_root, not both")
    if repo_root is not None:
        return repo_root / DEFAULT_CONTRACT_REGISTRY_PATH
    if configs_root is not None:
        return configs_root / _CONTRACT_REGISTRY_PATH_FROM_CONFIGS_ROOT
    return DEFAULT_CONTRACT_REGISTRY_PATH


def load_contract_registry_payload(registry_path: Path | None = None) -> JsonDict:
    """Load the raw contract-registry payload as a mapping."""
    path = resolve_contract_registry_path(registry_path)
    if not path.exists():
        raise FileNotFoundError(f"Contract registry not found: {path}")
    try:
        payload = _load_yaml_with_timeout(path)
    except TimeoutError as exc:
        raise TimeoutError(f"Contract registry load timeout: {path}") from exc
    except OSError as exc:
        raise OSError(f"Failed to read contract registry: {path}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"Malformed contract registry YAML: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(
            f"Malformed contract registry: expected mapping root in {path}"
        )
    return payload


def try_load_contract_registry_payload(
    registry_path: Path | None = None,
) -> JsonDict | None:
    """Best-effort contract-registry payload loader for optional governance checks."""
    try:
        return load_contract_registry_payload(registry_path)
    except (FileNotFoundError, OSError, ValueError):
        return None


def load_contract_registry_entries(
    registry_path: Path | None = None,
) -> dict[str, dict[str, object]]:
    """Load validated top-level contract-registry entries mapping."""
    path = resolve_contract_registry_path(registry_path)
    payload = load_contract_registry_payload(path)
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        raise ValueError(
            f"Malformed contract registry: entries must be a mapping in {path}"
        )
    normalized_entries: dict[str, dict[str, object]] = {}
    for contract_ref, entry in entries.items():
        if not isinstance(entry, dict):
            raise ValueError(
                "Malformed contract registry entry for "
                f"{contract_ref}: entry must be a mapping"
            )
        normalized_entries[str(contract_ref)] = dict(entry)
    return normalized_entries


def try_load_contract_registry_entries(
    registry_path: Path | None = None,
) -> dict[str, dict[str, object]]:
    """Best-effort entries loader used by optional validation flows."""
    try:
        return load_contract_registry_entries(registry_path)
    except (FileNotFoundError, OSError, ValueError):
        return {}


def load_contract_registry_entry(
    contract_ref: str,
    *,
    registry_path: Path | None = None,
) -> dict[str, object]:
    """Load one validated registry entry by contract_ref."""
    entries = load_contract_registry_entries(registry_path)
    entry = entries.get(contract_ref)
    if entry is None:
        raise KeyError(
            f"Contract registry entry not found for contract_ref: {contract_ref}"
        )
    return entry
