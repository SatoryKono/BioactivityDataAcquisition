"""Canonical validated loader for configs/base/contract_registry.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml

from bioetl.domain.types import JsonDict

DEFAULT_CONTRACT_REGISTRY_PATH = Path("configs/base/contract_registry.yaml")

__all__ = [
    "DEFAULT_CONTRACT_REGISTRY_PATH",
    "load_contract_registry_entries",
    "load_contract_registry_entry",
    "load_contract_registry_payload",
    "try_load_contract_registry_entries",
    "try_load_contract_registry_payload",
]


def _resolve_registry_path(registry_path: Path | None) -> Path:
    return registry_path or DEFAULT_CONTRACT_REGISTRY_PATH


def load_contract_registry_payload(registry_path: Path | None = None) -> JsonDict:
    """Load the raw contract-registry payload as a mapping."""
    path = _resolve_registry_path(registry_path)
    if not path.exists():
        raise FileNotFoundError(f"Contract registry not found: {path}")
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise OSError(f"Failed to read contract registry: {path}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"Malformed contract registry YAML: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Malformed contract registry: expected mapping root in {path}")
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
    path = _resolve_registry_path(registry_path)
    payload = load_contract_registry_payload(path)
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        raise ValueError(f"Malformed contract registry: entries must be a mapping in {path}")
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
