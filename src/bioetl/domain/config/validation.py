"""Validation configuration objects.

Defines domain value-object validation ranges and field-level /
cross-field / conditional validation rule descriptors.
"""

from __future__ import annotations

from bioetl.domain.config.validation_config import ValidationConfig
from bioetl.domain.config.validation_rules import (
    ConditionalValidation,
    CrossFieldValidation,
    FieldValidation,
)

__all__ = [
    "DEFAULT_VALIDATION_CONFIG",
    "ConditionalValidation",
    "CrossFieldValidation",
    "FieldValidation",
    "ValidationConfig",
]


# Default singleton instance for use when no custom config is provided
DEFAULT_VALIDATION_CONFIG = ValidationConfig()
