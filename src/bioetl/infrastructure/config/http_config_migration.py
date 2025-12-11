"""HTTP client configuration migration utilities.

This module centralizes legacy HTTP client field migrations that were previously
scattered across domain models. Moving this logic to infrastructure:

1. Keeps domain models clean (pure data, no migration logic)
2. Makes migrations explicit and testable
3. Allows deprecation warnings at appropriate layer

Migration mappings (legacy -> current):
    timeout -> timeout_sec
    retries -> max_retries
    backoff -> backoff_factor
    rate_limit -> rate_limit_per_sec
    circuit_breaker_recovery_time -> circuit_breaker_recovery_sec
    retry_enabled (False) -> max_retries = 0
"""

from __future__ import annotations

import warnings
from typing import Any


class HttpConfigMigrator:
    """Migrates legacy HTTP client configuration fields.

    This class handles backward compatibility for HTTP client configuration
    by converting old field names to new canonical names.

    Example:
        >>> raw = {"timeout": 30, "retries": 5}
        >>> migrated = HttpConfigMigrator.migrate(raw)
        >>> print(migrated)
        {'timeout_sec': 30.0, 'max_retries': 5}
    """

    # Legacy field name -> (new field name, value converter or None)
    LEGACY_MAPPINGS: dict[str, tuple[str, Any]] = {
        "timeout": ("timeout_sec", float),
        "retries": ("max_retries", int),
        "backoff": ("backoff_factor", None),
        "rate_limit": ("rate_limit_per_sec", None),
        "circuit_breaker_recovery_time": ("circuit_breaker_recovery_sec", None),
    }

    @classmethod
    def migrate(
        cls,
        data: dict[str, Any],
        *,
        warn: bool = True,
        warn_stacklevel: int = 3,
    ) -> dict[str, Any]:
        """Migrate legacy HTTP client config fields to current format.

        Args:
            data: Raw configuration dictionary.
            warn: Whether to emit deprecation warnings for legacy fields.
            warn_stacklevel: Stack level for deprecation warnings.

        Returns:
            Migrated configuration dictionary.
        """
        if not isinstance(data, dict):
            return data

        migrated = dict(data)
        migrated_fields: list[str] = []

        # Apply legacy field mappings
        for old_name, (new_name, converter) in cls.LEGACY_MAPPINGS.items():
            if old_name in migrated and new_name not in migrated:
                value = migrated.pop(old_name)
                if converter is not None:
                    value = converter(value)
                migrated[new_name] = value
                migrated_fields.append(old_name)
            elif old_name in migrated:
                # Remove duplicate legacy field
                migrated.pop(old_name)
                migrated_fields.append(old_name)

        # Handle retry_enabled special case
        if "retry_enabled" in migrated:
            retry_enabled = migrated.pop("retry_enabled")
            if not retry_enabled and "max_retries" not in migrated:
                migrated["max_retries"] = 0
            migrated_fields.append("retry_enabled")

        # Emit deprecation warning if any legacy fields were found
        if warn and migrated_fields:
            fields_str = ", ".join(sorted(migrated_fields))
            warnings.warn(
                f"Legacy HTTP client config fields detected: {fields_str}. "
                "Please update to canonical field names "
                "(timeout_sec, max_retries, backoff_factor, rate_limit_per_sec). "
                "Legacy fields will be removed in v3.0.",
                DeprecationWarning,
                stacklevel=warn_stacklevel,
            )

        return migrated

    @classmethod
    def migrate_nested(
        cls,
        data: dict[str, Any],
        *,
        path: str = "runtime.http",
        warn: bool = True,
    ) -> dict[str, Any]:
        """Migrate HTTP config at a nested path in configuration.

        Args:
            data: Full configuration dictionary.
            path: Dot-separated path to HTTP config section.
            warn: Whether to emit deprecation warnings.

        Returns:
            Configuration with migrated nested HTTP config.
        """
        if not isinstance(data, dict):
            return data

        result = dict(data)
        parts = path.split(".")

        # Navigate to parent of target
        current = result
        for part in parts[:-1]:
            if part not in current or not isinstance(current.get(part), dict):
                return result
            current = current[part]

        # Migrate target if it exists
        target_key = parts[-1]
        if target_key in current and isinstance(current[target_key], dict):
            current[target_key] = cls.migrate(current[target_key], warn=warn)

        return result


__all__ = ["HttpConfigMigrator"]
