"""Registry loader/validator for architecture metric exemptions.

Exemptions are stored in a YAML registry with mandatory metadata:
- owner
- reason
- due date (`expires_on` or `due_on`)
- removal_step
"""

from __future__ import annotations

__all__ = [
    "build_module_path_key",
    "get_registry_values",
    "load_exemptions_registry",
    "resolve_registry_value",
    "validate_exemption_key_normalization",
    "validate_exemptions_registry",
]


import re
from datetime import date
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_REGISTRY_PATH = Path("configs/quality/architecture_metric_exemptions.yaml")
_DEFAULT_REQUIRED_FIELDS = ("value", "owner", "reason", "expires_on", "removal_step")
_DUE_DATE_FIELDS = ("expires_on", "due_on")
_PLACEHOLDER_NAME_RE = re.compile(
    r"^(todo|tbd|unknown|temp|fixme|example|placeholder)$",
    re.IGNORECASE,
)
_PLACEHOLDER_OWNER_RE = re.compile(
    r"^(todo|tbd|unknown|none|unassigned|team)$",
    re.IGNORECASE,
)
_SRC_ROOT_PREFIX = "src/bioetl/"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _resolve_registry_path(path: Path | str | None = None) -> Path:
    candidate = _DEFAULT_REGISTRY_PATH if path is None else Path(path)

    if candidate.is_absolute():
        return candidate
    return _project_root() / candidate


def _normalize_path_text(value: str) -> str:
    return value.replace("\\", "/").lstrip("./")


def _is_module_path_key(value: str) -> bool:
    normalized = _normalize_path_text(value)
    return normalized.startswith(_SRC_ROOT_PREFIX) and normalized.endswith(".py")


def build_module_path_key(
    module_path: Path | str,
    *,
    src_root: Path | str | None = None,
) -> str:
    """Build canonical registry key for a module path.

    Canonical format is repository-relative POSIX path:
    ``src/bioetl/<layer>/.../<module>.py``.
    """
    text = _normalize_path_text(str(module_path))
    if _is_module_path_key(text):
        return text

    src_root_path = (
        _project_root() / "src" if src_root is None else Path(src_root).resolve()
    )
    path_obj = Path(module_path)
    if not path_obj.is_absolute():
        path_obj = path_obj.resolve()

    if path_obj.is_relative_to(src_root_path):
        rel = path_obj.relative_to(src_root_path).as_posix()
        return f"src/{rel}"

    if text.startswith("bioetl/") and text.endswith(".py"):
        return f"src/{text}"

    raise ValueError(
        f"module_path must resolve under src/ or already be canonical ({module_path!r})"
    )


def load_exemptions_registry(
    path: Path | str | None = None,
) -> dict[str, Any]:  # Any: DQ check values vary by check type
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
) -> dict[str, Any]:  # Any: DQ check values vary by check type
    """Return value-only mapping for a concrete registry section."""
    raw = load_exemptions_registry(path)
    registries = raw.get("registries", {})
    if not isinstance(registries, dict):
        raise ValueError("Invalid exemptions registry: 'registries' must be a mapping")

    entries = registries.get(registry_name, {})
    if not isinstance(entries, dict):
        raise ValueError(f"Invalid registry '{registry_name}': expected mapping")

    values: dict[str, Any] = {}  # Any: DQ check values vary by check type
    for name, entry in entries.items():
        if not isinstance(entry, dict) or "value" not in entry:
            raise ValueError(
                f"Invalid entry for registry '{registry_name}' key '{name}': missing 'value'"
            )
        values[name] = entry["value"]
    return values


def resolve_registry_value(
    values: dict[str, Any],  # Any: check-specific thresholds vary by registry
    *,
    module_path: Path | str,
    symbol_name: str | None = None,
    legacy_name: str | None = None,
) -> Any | None:  # Any: dynamic payload or structural mixin boundary
    """Resolve exemption value using canonical path key with dual-read fallback.

    Lookup priority:
    1) ``src/bioetl/.../module.py::symbol`` (when ``symbol_name`` is provided)
    2) ``src/bioetl/.../module.py``
    3) legacy symbol key (``symbol_name``)
    4) explicit ``legacy_name`` (typically basename)
    5) basename of ``module_path``

    This keeps one-release compatibility during key migration from basename/symbol
    to path-aware identifiers.
    """
    module_key = build_module_path_key(module_path)
    candidates: list[str] = []
    if symbol_name:
        candidates.append(f"{module_key}::{symbol_name}")
    candidates.append(module_key)
    if symbol_name:
        candidates.append(symbol_name)
    if legacy_name:
        candidates.append(legacy_name)
    candidates.append(Path(module_key).name)

    for candidate in candidates:
        if candidate in values:
            return values[candidate]
    return None


def validate_exemption_key_normalization(
    path: Path | str | None = None,
) -> list[str]:
    """Validate that file-size exemptions use canonical path keys.

    During transition, other registries may still use symbol-only keys. This
    validator focuses on collision-prone ``file_size_limits`` entries.
    """
    raw = load_exemptions_registry(path)
    registries = raw.get("registries", {})
    if not isinstance(registries, dict):
        return ["registries: expected mapping"]

    file_size = registries.get("file_size_limits", {})
    if not isinstance(file_size, dict):
        return ["registries.file_size_limits: expected mapping"]

    errors: list[str] = []
    src_root = _project_root() / "src"

    for key in sorted(file_size):
        if not isinstance(key, str) or not key.strip():
            errors.append("file_size_limits: key must be non-empty string")
            continue

        normalized = _normalize_path_text(key)
        if not _is_module_path_key(normalized):
            errors.append(
                f"file_size_limits.{key}: expected canonical path key "
                f"'{_SRC_ROOT_PREFIX}.../*.py'"
            )
            continue

        module_path = _project_root() / normalized
        if not module_path.exists():
            errors.append(f"file_size_limits.{key}: target file does not exist")
            continue
        if not module_path.is_relative_to(src_root):
            errors.append(
                f"file_size_limits.{key}: target path must be inside src/ tree"
            )

    return errors


def _validate_required_fields(
    prefix: str,
    entry: dict[str, Any],  # Any: DQ check values vary by check type
    required_fields: tuple[str, ...],
    metadata_errors: list[str],
) -> None:
    """Validate presence and non-empty values for required entry fields."""
    for field_name in required_fields:
        if field_name in _DUE_DATE_FIELDS:
            continue
        value = entry.get(field_name)
        if value is None:
            metadata_errors.append(f"{prefix}: missing required field '{field_name}'")
            continue
        if isinstance(value, str) and not value.strip():
            metadata_errors.append(f"{prefix}: empty required field '{field_name}'")


def _normalize_required_fields(
    raw_fields: object,
    metadata_errors: list[str],
) -> tuple[str, ...]:
    """Normalize policy.required_fields into stable tuple with fallbacks."""
    if not isinstance(raw_fields, list) or not raw_fields:
        metadata_errors.append(
            "policy.required_fields: expected non-empty list, "
            f"falling back to default {list(_DEFAULT_REQUIRED_FIELDS)}"
        )
        return _DEFAULT_REQUIRED_FIELDS

    normalized: list[str] = []
    for item in raw_fields:
        if not isinstance(item, str) or not item.strip():
            metadata_errors.append(
                "policy.required_fields: field names must be non-empty strings"
            )
            continue
        normalized.append(item.strip())

    return tuple(normalized) if normalized else _DEFAULT_REQUIRED_FIELDS


def _get_policy_required_fields(
    raw: dict[str, Any],  # Any: DQ check values vary by check type
    metadata_errors: list[str],
) -> tuple[str, ...]:
    """Read required field policy and enforce owner+due-date governance."""
    required_fields: tuple[str, ...]
    policy = raw.get("policy", {})
    if not isinstance(policy, dict):
        metadata_errors.append("policy: expected mapping, falling back to defaults")
        required_fields = _DEFAULT_REQUIRED_FIELDS
    else:
        required_fields = _normalize_required_fields(
            policy.get("required_fields", list(_DEFAULT_REQUIRED_FIELDS)),
            metadata_errors,
        )

    if "owner" not in required_fields:
        metadata_errors.append("policy.required_fields must include 'owner'")

    if not any(field in required_fields for field in _DUE_DATE_FIELDS):
        metadata_errors.append(
            "policy.required_fields must include due date field "
            "('expires_on' or 'due_on')"
        )

    return required_fields


def _validate_owner(
    prefix: str,
    entry: dict[str, Any],  # Any: DQ check values vary by check type
    metadata_errors: list[str],
) -> None:
    """Validate owner field is not using placeholders."""
    owner = entry.get("owner")
    if isinstance(owner, str) and _PLACEHOLDER_OWNER_RE.match(owner.strip()):
        metadata_errors.append(f"{prefix}: owner placeholder is not allowed")


def _validate_due_date(
    prefix: str,
    entry: dict[str, Any],  # Any: DQ check values vary by check type
    required_fields: tuple[str, ...],
    now: date,
    metadata_errors: list[str],
    expired_entries: list[str],
) -> None:
    """Validate due-date field format and expiration status."""
    due_candidates: list[str] = [
        field for field in required_fields if field in _DUE_DATE_FIELDS
    ]
    for field in _DUE_DATE_FIELDS:
        if field not in due_candidates:
            due_candidates.append(field)

    due_field = next((field for field in due_candidates if field in entry), None)
    selected_field = due_field or due_candidates[0]
    due_value = entry.get(selected_field)

    if not isinstance(due_value, str):
        metadata_errors.append(
            f"{prefix}: due date field '{selected_field}' must be ISO date string (YYYY-MM-DD)"
        )
        return

    try:
        expiry_date = date.fromisoformat(due_value)
    except ValueError:
        metadata_errors.append(
            f"{prefix}: due date field '{selected_field}' must be ISO date (YYYY-MM-DD)"
        )
        return

    if expiry_date < now:
        expired_entries.append(
            f"{prefix} expired on {due_value} (field={selected_field}, owner={entry.get('owner')})"
        )


def _validate_exemption_entry(
    registry_name: str,
    exemption_name: object,
    entry: object,
    required_fields: tuple[str, ...],
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

    _validate_required_fields(prefix, entry, required_fields, metadata_errors)
    _validate_owner(prefix, entry, metadata_errors)
    _validate_due_date(
        prefix,
        entry,
        required_fields,
        now,
        metadata_errors,
        expired_entries,
    )


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
    required_fields = _get_policy_required_fields(raw, metadata_errors)

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
                required_fields,
                now,
                metadata_errors,
                expired_entries,
            )

    metadata_errors.extend(validate_exemption_key_normalization(path))
    return metadata_errors, expired_entries
