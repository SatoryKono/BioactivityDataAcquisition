"""Tests for public application-core runtime API re-export seams."""

from __future__ import annotations

import importlib
import sys

import pytest


@pytest.mark.unit
@pytest.mark.parametrize(
    ("removed_module_name", "canonical_module_name"),
    (
        (
            "bioetl.application.core.batch_execution_lifecycle",
            "bioetl.application.core.batch_execution.lifecycle",
        ),
        (
            "bioetl.application.core.batch_execution_run_service",
            "bioetl.application.core.batch_execution.run_service",
        ),
        (
            "bioetl.application.core.batch_execution_state_service",
            "bioetl.application.core.batch_execution.state_service",
        ),
    ),
)
def test_batch_execution_flat_facades_stay_removed(
    removed_module_name: str,
    canonical_module_name: str,
) -> None:
    """Batch-execution callers must use the canonical package modules."""
    sys.modules.pop(removed_module_name, None)

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(removed_module_name)

    assert importlib.import_module(canonical_module_name)


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
    # publication_aliases.py removed as sunset date (2026-03-29) passed
    # LEGACY_PUBLICATION_ALIASES_CUTOFF_DATE check removed
