"""Composition Root for BioETL dependency injection.

This package contains the Composition Root - the single place where
all dependencies are composed and wired together according to the
Ports & Adapters architecture (RULES.md).

Components:
    bootstrap: Pipeline bootstrapping and factory functions.
    registry_api: Public pipeline registry API.
    builders: Builder classes for constructing pipelines.
    types: Type definitions for composition layer.
    observability: Observability setup (tracing, metrics, logging).
    entrypoints: CLI and API entrypoints.

The composition layer is the only layer allowed to import from
infrastructure and wire concrete implementations to domain ports.

See Also:
    docs/02-architecture/decisions/ADR-005-composition-layer-separation.md
"""

from __future__ import annotations

__all__: list[str] = []

_LAZY_MODULE_EXPORTS = {
    "composite_api",
    "control_plane_api",
    "entrypoints",
    "execution_api",
    "health_api",
    "maintenance_api",
    "observability_api",
    "registry_api",
    "resources_api",
    "types",
}
