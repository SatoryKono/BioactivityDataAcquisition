"""Public API for architecture metric exemptions registry helpers."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, cast

import bioetl.infrastructure.quality.exemptions_registry_policy as _policy_module
import bioetl.infrastructure.quality.exemptions_registry_targets as _targets_module
from bioetl.infrastructure.quality.exemptions_registry_access import (
    get_registry_values,
    load_exemptions_registry,
    resolve_registry_value,
)
from bioetl.infrastructure.quality.exemptions_registry_paths import (
    build_module_path_key,
)
from bioetl.infrastructure.quality.exemptions_registry_paths import (
    project_root as _project_root,
)
from bioetl.infrastructure.quality.exemptions_registry_policy import (
    EXEMPTION_REGISTRIES_ALLOW_EMPTY,
    REQUIRED_EXEMPTION_REGISTRIES,
)
from bioetl.infrastructure.quality.exemptions_registry_policy import (
    validate_exemption_key_normalization as _validate_exemption_key_normalization_impl,
)
from bioetl.infrastructure.quality.exemptions_registry_policy import (
    validate_exemptions_registry as _validate_exemptions_registry_impl,
)
from bioetl.infrastructure.quality.exemptions_registry_targets import (
    validate_exemption_target_references as _validate_exemption_target_references_impl,
)


def validate_exemption_key_normalization(
    path: Path | str | None = None,
) -> list[str]:
    """Compatibility wrapper preserving façade-level `_project_root` patch seam."""
    policy_module = cast(Any, _policy_module)  # Any: dynamic compat patch target
    original = policy_module._project_root
    policy_module._project_root = _project_root
    try:
        return _validate_exemption_key_normalization_impl(path)
    finally:
        policy_module._project_root = original


def validate_exemption_target_references(
    path: Path | str | None = None,
) -> list[str]:
    """Compatibility wrapper preserving façade-level `_project_root` patch seam."""
    targets_module = cast(Any, _targets_module)  # Any: dynamic compat patch target
    original = targets_module._project_root
    targets_module._project_root = _project_root
    try:
        return _validate_exemption_target_references_impl(path)
    finally:
        targets_module._project_root = original


def validate_exemptions_registry(
    path: Path | str | None = None,
    *,
    today: date | None = None,
) -> tuple[list[str], list[str]]:
    """Compatibility wrapper preserving façade-level patch seams."""
    policy_module = cast(Any, _policy_module)  # Any: dynamic compat patch target
    targets_module = cast(Any, _targets_module)  # Any: dynamic compat patch target
    original_policy_root = policy_module._project_root
    original_targets_root = targets_module._project_root
    original_policy_target_validation = (
        policy_module.validate_exemption_target_references
    )
    policy_module._project_root = _project_root
    targets_module._project_root = _project_root
    policy_module.validate_exemption_target_references = (
        validate_exemption_target_references
    )
    try:
        return _validate_exemptions_registry_impl(path, today=today)
    finally:
        policy_module._project_root = original_policy_root
        targets_module._project_root = original_targets_root
        policy_module.validate_exemption_target_references = (
            original_policy_target_validation
        )


__all__ = [
    "EXEMPTION_REGISTRIES_ALLOW_EMPTY",
    "REQUIRED_EXEMPTION_REGISTRIES",
    "build_module_path_key",
    "get_registry_values",
    "load_exemptions_registry",
    "resolve_registry_value",
    "validate_exemption_key_normalization",
    "validate_exemption_target_references",
    "validate_exemptions_registry",
]
