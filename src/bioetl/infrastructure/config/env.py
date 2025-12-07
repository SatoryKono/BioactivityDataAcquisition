"""Helpers for environment placeholder substitution in configs."""

from __future__ import annotations

import os
import re
from typing import Any


ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)(:-([^}]*))?\}")


def resolve_env_placeholders(value: Any) -> Any:
    """Recursively resolve ${ENV[:-default]} placeholders in mappings and sequences."""

    if isinstance(value, dict):
        return {key: resolve_env_placeholders(item) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve_env_placeholders(item) for item in value]
    if isinstance(value, str):
        return _substitute_env(value)
    return value


def _substitute_env(raw: str) -> str:
    """Replace env placeholders with OS values, falling back to defaults."""

    def _replace_env_placeholder(match: re.Match[str]) -> str:
        """Resolve one ${ENV[:-default]} placeholder using env or default."""

        var_name = match.group(1)
        default_value = match.group(3)
        env_value = os.environ.get(var_name)
        if env_value is not None:
            return env_value
        if default_value is not None:
            return default_value
        return match.group(0)

    return ENV_PATTERN.sub(_replace_env_placeholder, raw)


__all__ = ["ENV_PATTERN", "resolve_env_placeholders"]
