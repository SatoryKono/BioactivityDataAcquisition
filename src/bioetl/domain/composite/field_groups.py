"""Field-group facade for composite publication pipelines."""

from __future__ import annotations

from bioetl.domain.composite.field_groups_models import (
    DEFAULT_PROVIDER_ORDER,
    FieldGroupDefinition,
    FieldGroupId,
    FieldMapping,
)
from bioetl.domain.composite.field_groups_registry import (
    FieldGroupRegistry,
    build_field_group_registry,
)

__all__ = [
    "DEFAULT_PROVIDER_ORDER",
    "FieldGroupDefinition",
    "FieldGroupId",
    "FieldGroupRegistry",
    "FieldMapping",
    "build_field_group_registry",
]
