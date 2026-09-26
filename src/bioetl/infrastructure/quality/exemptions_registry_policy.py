"""Validation/orchestration policy for architecture metric exemptions registry."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from bioetl.infrastructure.quality.exemptions_registry_access import (
    load_exemptions_registry,
)
from bioetl.infrastructure.quality.exemptions_registry_paths import (
    _SRC_ROOT_PREFIX,
)
from bioetl.infrastructure.quality.exemptions_registry_paths import (
    is_module_path_key as _is_module_path_key,
)
from bioetl.infrastructure.quality.exemptions_registry_paths import (
    normalize_path_text as _normalize_path_text,
)
from bioetl.infrastructure.quality.exemptions_registry_paths import (
    project_root as _project_root,
)
from bioetl.infrastructure.quality.exemptions_registry_targets import (
    validate_exemption_target_references,
)
from bioetl.infrastructure.quality.exemptions_registry_validation import (
    get_policy_required_fields as _get_policy_required_fields,
)
from bioetl.infrastructure.quality.exemptions_registry_validation import (
    validate_exemption_entry as _validate_exemption_entry,
)

REQUIRED_EXEMPTION_REGISTRIES = (
    "file_size_limits",
    "function_complexity",
    "function_length",
    "class_size",
    "class_method_count",
    "god_object",
    "domain_complexity",
)
EXEMPTION_REGISTRIES_ALLOW_EMPTY = frozenset(
    {
        "file_size_limits",
        "function_length",
        "class_size",
        "class_method_count",
        "god_object",
        "function_complexity",
        "domain_complexity",
    }
)


def validate_exemption_key_normalization(
    path: Path | str | None = None,
) -> list[str]:
    """Validate that file-size exemptions use canonical path keys."""
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


def _validate_required_registries(
    registries: dict[str, object],
    errors: list[str],
) -> None:
    """Check that all required registries exist and have valid types."""
    missing = sorted(set(REQUIRED_EXEMPTION_REGISTRIES) - set(registries))
    if missing:
        errors.append("Missing required exemption registries: " + ", ".join(missing))

    for name in REQUIRED_EXEMPTION_REGISTRIES:
        if name in missing:
            continue
        entries = registries.get(name)
        if not isinstance(entries, dict):
            errors.append(
                f"{name}: expected mapping of exemptions, got {type(entries).__name__}"
            )
            continue
        if not entries and name not in EXEMPTION_REGISTRIES_ALLOW_EMPTY:
            errors.append(f"{name}: registry must not be empty")


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

    _validate_required_registries(registries, metadata_errors)

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
    metadata_errors.extend(validate_exemption_target_references(path))
    return metadata_errors, expired_entries


__all__ = [
    "EXEMPTION_REGISTRIES_ALLOW_EMPTY",
    "REQUIRED_EXEMPTION_REGISTRIES",
    "validate_exemption_key_normalization",
    "validate_exemptions_registry",
]
