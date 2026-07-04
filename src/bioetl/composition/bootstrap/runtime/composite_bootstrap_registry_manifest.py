"""Registry manifest for composite bootstrap bundle and builder modules."""

from __future__ import annotations

from collections.abc import Mapping

COMPOSITE_BOOTSTRAP_BUILDER_MODULES: Mapping[str, str] = {
    "control_plane": "bioetl.composition.bootstrap.runtime.composite_control_plane_builder",
    "execution_support": (
        "bioetl.composition.bootstrap.runtime.composite_execution_support_builder"
    ),
    "merge": "bioetl.composition.bootstrap.runtime.composite_merge_service_builder",
    "runtime_management": (
        "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder"
    ),
    "support_services": (
        "bioetl.composition.bootstrap.runtime.composite_support_service_builders"
    ),
}

COMPOSITE_BOOTSTRAP_BUILDER_PACKAGE_EXPORTS: Mapping[str, str] = {
    module_path.rsplit(".", 1)[-1]: module_path
    for module_path in COMPOSITE_BOOTSTRAP_BUILDER_MODULES.values()
}

COMPOSITE_BOOTSTRAP_BUNDLE_MODULES: Mapping[str, str] = {
    "control_plane": "bioetl.composition.bootstrap.runtime.composite_control_plane_bundle",
    "execution_support": (
        "bioetl.composition.bootstrap.runtime.composite_execution_support_bundle"
    ),
    "merge_dependencies": (
        "bioetl.composition.bootstrap.runtime.composite_merge_dependencies_bundle"
    ),
    "runtime_management": (
        "bioetl.composition.bootstrap.runtime.composite_runtime_management_bundle"
    ),
}

__all__ = [
    "COMPOSITE_BOOTSTRAP_BUILDER_MODULES",
    "COMPOSITE_BOOTSTRAP_BUILDER_PACKAGE_EXPORTS",
    "COMPOSITE_BOOTSTRAP_BUNDLE_MODULES",
]
