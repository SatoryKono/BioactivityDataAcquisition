"""Canonical public entrypoint for publication field-group definitions."""

from __future__ import annotations

from bioetl.domain.value_objects._publication_field_group_config import (
    DEFAULT_FIELD_GROUP_CONFIG,
    FieldGroupConfig,
)
from bioetl.domain.value_objects._publication_field_group_types import (
    FIELD_TO_GROUP_MAPPING,
    PublicationFieldGroup,
)

__all__ = [
    "DEFAULT_FIELD_GROUP_CONFIG",
    "FIELD_TO_GROUP_MAPPING",
    "FieldGroupConfig",
    "PublicationFieldGroup",
]
