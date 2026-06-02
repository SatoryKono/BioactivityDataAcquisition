"""Facade exports for composite runtime support service builders."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig

from bioetl.composition.bootstrap.runtime.composite_execution_support_builder import (
    build_execution_support_services,
)
from bioetl.composition.bootstrap.runtime.composite_merge_dependency_builder import (
    build_merge_dependencies,
)
from bioetl.composition.bootstrap.runtime.composite_runtime_management_builder import (
    build_runtime_management_services,
)

_RUNTIME_CONFIG_FACADE: type[CompositeRuntimeConfig] | None = None

__all__ = [
    "build_execution_support_services",
    "build_merge_dependencies",
    "build_runtime_management_services",
]
