"""Tests for public application-core runtime API re-export seams."""

from __future__ import annotations

import importlib
import sys

import pytest


@pytest.mark.unit
@pytest.mark.parametrize(
    ("compat_module_name", "target_module_name", "export_name"),
    (
        (
            "bioetl.application.core.batch_execution_run_service",
            "bioetl.application.core.batch_execution.run_service",
            "BatchExecutionRunService",
        ),
        (
            "bioetl.application.core.batch_execution_state_service",
            "bioetl.application.core.batch_execution.state_service",
            "BatchExecutionStateService",
        ),
    ),
)
def test_batch_execution_service_shims_reexport_canonical_types(
    compat_module_name: str,
    target_module_name: str,
    export_name: str,
) -> None:
    """Thin public shims should expose the canonical batch-execution services."""
    sys.modules.pop(compat_module_name, None)

    compat_module = importlib.import_module(compat_module_name)
    target_module = importlib.import_module(target_module_name)

    assert getattr(compat_module, export_name) is getattr(target_module, export_name)


@pytest.mark.unit
def test_batch_execution_lifecycle_shim_reexports_canonical_surface() -> None:
    """Lifecycle shim should mirror the canonical lifecycle module surface."""
    sys.modules.pop("bioetl.application.core.batch_execution_lifecycle", None)

    compat_module = importlib.import_module(
        "bioetl.application.core.batch_execution_lifecycle"
    )
    target_module = importlib.import_module(
        "bioetl.application.core.batch_execution.lifecycle"
    )

    assert compat_module.__all__ == target_module.__all__
    for export_name in target_module.__all__:
        assert getattr(compat_module, export_name) is getattr(
            target_module, export_name
        )


@pytest.mark.unit
def test_field_transforms_package_exposes_canonical_transform_primitives() -> None:
    """field_transforms package should expose transform helpers from its owner modules."""
    sys.modules.pop("bioetl.application.core.field_transforms", None)

    compat_module = importlib.import_module("bioetl.application.core.field_transforms")

    assert (
        compat_module.flatten_nested_dict
        is importlib.import_module(
            "bioetl.application.core.dict_transformers"
        ).flatten_nested_dict
    )
    assert (
        compat_module.compute_publication_term_entity_id
        is importlib.import_module(
            "bioetl.application.core.entity_id"
        ).compute_publication_term_entity_id
    )
    assert (
        compat_module.FieldSpec
        is importlib.import_module("bioetl.application.core.field_specs").FieldSpec
    )
    assert (
        compat_module.LEGACY_PUBLICATION_ALIASES_CUTOFF_DATE
        == importlib.import_module(
            "bioetl.application.core.publication_aliases"
        ).LEGACY_PUBLICATION_ALIASES_CUTOFF_DATE
    )
