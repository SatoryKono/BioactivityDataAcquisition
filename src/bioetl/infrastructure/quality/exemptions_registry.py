"""Registry loader/validator for architecture metric exemptions.

Exemptions are stored in a YAML registry with mandatory ownership metadata:
- owner
- reason
- expires_on
- removal_step
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_REGISTRY_PATH = Path("configs/quality/architecture_metric_exemptions.yaml")
_REQUIRED_FIELDS = ("value", "owner", "reason", "expires_on", "removal_step")
_PLACEHOLDER_NAME_RE = re.compile(
    r"^(todo|tbd|unknown|temp|fixme|example|placeholder)$",
    re.IGNORECASE,
)
_PLACEHOLDER_OWNER_RE = re.compile(
    r"^(todo|tbd|unknown|none|unassigned|team)$",
    re.IGNORECASE,
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _resolve_registry_path(path: Path | str | None = None) -> Path:
    candidate = _DEFAULT_REGISTRY_PATH if path is None else Path(path)

    if candidate.is_absolute():
        return candidate
    return _project_root() / candidate


def load_exemptions_registry(path: Path | str | None = None) -> dict[str, Any]:
    """Load YAML exemptions registry as dictionary."""
    registry_path = _resolve_registry_path(path)
    if not registry_path.exists():
        raise FileNotFoundError(f"Exemptions registry not found: {registry_path}")

    raw = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Exemptions registry must be a mapping: {registry_path}")
    return raw


def get_registry_values(
    registry_name: str,
    path: Path | str | None = None,
) -> dict[str, Any]:
    """Return value-only mapping for a concrete registry section."""
    raw = load_exemptions_registry(path)
    registries = raw.get("registries", {})
    if not isinstance(registries, dict):
        raise ValueError("Invalid exemptions registry: 'registries' must be a mapping")

    entries = registries.get(registry_name, {})
    if not isinstance(entries, dict):
        raise ValueError(f"Invalid registry '{registry_name}': expected mapping")

    values: dict[str, Any] = {}
    for name, entry in entries.items():
        if not isinstance(entry, dict) or "value" not in entry:
            raise ValueError(
                f"Invalid entry for registry '{registry_name}' key '{name}': missing 'value'"
            )
        values[name] = entry["value"]
    return values


def _validate_required_fields(
    prefix: str,
    entry: dict[str, Any],
    metadata_errors: list[str],
) -> None:
    """Validate presence and non-empty values for required entry fields."""
    for field_name in _REQUIRED_FIELDS:
        value = entry.get(field_name)
        if value is None:
            metadata_errors.append(f"{prefix}: missing required field '{field_name}'")
            continue
        if isinstance(value, str) and not value.strip():
            metadata_errors.append(f"{prefix}: empty required field '{field_name}'")


def _validate_owner(
    prefix: str,
    entry: dict[str, Any],
    metadata_errors: list[str],
) -> None:
    """Validate owner field is not using placeholders."""
    owner = entry.get("owner")
    if isinstance(owner, str) and _PLACEHOLDER_OWNER_RE.match(owner.strip()):
        metadata_errors.append(f"{prefix}: owner placeholder is not allowed")


def _validate_expiry(
    prefix: str,
    entry: dict[str, Any],
    now: date,
    metadata_errors: list[str],
    expired_entries: list[str],
) -> None:
    """Validate expires_on field format and expiration status."""
    expires_on = entry.get("expires_on")
    if not isinstance(expires_on, str):
        metadata_errors.append(
            f"{prefix}: expires_on must be ISO date string (YYYY-MM-DD)"
        )
        return

    try:
        expiry_date = date.fromisoformat(expires_on)
    except ValueError:
        metadata_errors.append(f"{prefix}: expires_on must be ISO date (YYYY-MM-DD)")
        return

    if expiry_date < now:
        expired_entries.append(
            f"{prefix} expired on {expires_on} (owner={entry.get('owner')})"
        )


def _validate_exemption_entry(
    registry_name: str,
    exemption_name: object,
    entry: object,
    now: date,
    metadata_errors: list[str],
    expired_entries: list[str],
) -> None:
    """Validate one exemption entry and append issues into result lists."""
    prefix = f"{registry_name}.{exemption_name}"

    if not isinstance(exemption_name, str) or not exemption_name.strip():
        metadata_errors.append(f"{prefix}: exemption key must be non-empty string")
        return

    if _PLACEHOLDER_NAME_RE.match(exemption_name.strip()):
        metadata_errors.append(f"{prefix}: placeholder exemption name is not allowed")

    if not isinstance(entry, dict):
        metadata_errors.append(f"{prefix}: entry must be mapping")
        return

    _validate_required_fields(prefix, entry, metadata_errors)
    _validate_owner(prefix, entry, metadata_errors)
    _validate_expiry(prefix, entry, now, metadata_errors, expired_entries)


def validate_exemptions_registry(
    path: Path | str | None = None,
    *,
    today: date | None = None,
) -> tuple[list[str], list[str]]:
    """Validate registry metadata and return (metadata_errors, expired_entries)."""
    raw = load_exemptions_registry(path)
    now = today or date.today()
    metadata_errors: list[str] = []
    expired_entries: list[str] = []

    registries = raw.get("registries")
    if not isinstance(registries, dict):
        return (["Missing or invalid top-level 'registries' mapping"], [])

    for registry_name, entries in sorted(registries.items()):
        if not isinstance(entries, dict):
            metadata_errors.append(
                f"{registry_name}: expected mapping of exemptions, got {type(entries).__name__}"
            )
            continue

        for exemption_name, entry in sorted(entries.items()):
            _validate_exemption_entry(
                registry_name,
                exemption_name,
                entry,
                now,
                metadata_errors,
                expired_entries,
            )

    return metadata_errors, expired_entries
