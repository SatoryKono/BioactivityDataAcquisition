"""Canonical composition-layer assembly manifest for runtime builder lazy exports."""

from __future__ import annotations

from typing import NamedTuple

from bioetl.composition.lazy_exports import LazyExportTarget

__all__ = [
    "PUBLIC_LAZY_EXPORTS",
    "RUNTIME_BUILDER_EXPORTS",
    "RuntimeBuilderExportEntry",
]


class RuntimeBuilderExportEntry(NamedTuple):
    """Value object describing one runtime-builder lazy export registration."""

    export_name: str
    builder_module: str
    target_attr: str


RUNTIME_BUILDER_EXPORTS: tuple[RuntimeBuilderExportEntry, ...] = (
    RuntimeBuilderExportEntry(
        "build_pipeline_runner",
        "bioetl.composition.runtime_builders.runner_builder",
        "build_pipeline_runner",
    ),
    RuntimeBuilderExportEntry(
        "control_plane_root",
        "bioetl.composition.runtime_builders._run_manifest_data_roots",
        "control_plane_root",
    ),
)

PUBLIC_LAZY_EXPORTS: dict[str, LazyExportTarget] = {
    entry.export_name: (entry.builder_module, entry.target_attr)
    for entry in RUNTIME_BUILDER_EXPORTS
}
