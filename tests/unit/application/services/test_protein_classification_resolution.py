"""Tests for target protein classification resolution use case."""

from __future__ import annotations

import pytest

from bioetl.application.services.protein_classification_resolution import (
    ResolveProteinClassificationUseCase,
)
from bioetl.domain.value_objects.protein_class_hierarchy import (
    ProteinClassHierarchy,
    ProteinClassLevel,
    ProteinClassificationResolutionError,
)


pytestmark = pytest.mark.unit

class _FakeClassificationPort:
    def __init__(
        self,
        mapping: dict[int, tuple[ProteinClassHierarchy, ...]],
        *,
        failing_component_id: int | None = None,
    ) -> None:
        self._mapping = mapping
        self._failing_component_id = failing_component_id

    def get_component_classifications(
        self,
        component_id: int,
    ) -> tuple[ProteinClassHierarchy, ...]:
        if component_id == self._failing_component_id:
            raise ProteinClassificationResolutionError("broken parent chain")
        return self._mapping.get(component_id, ())


def _hierarchy(leaf_id: int) -> ProteinClassHierarchy:
    return ProteinClassHierarchy(
        l1=ProteinClassLevel(id=leaf_id, name=f"Class {leaf_id}", desc=None),
        l2=ProteinClassLevel.empty(),
        l3=ProteinClassLevel.empty(),
        l4=ProteinClassLevel.empty(),
        l5=ProteinClassLevel.empty(),
        leaf_id=leaf_id,
    )


def test_resolver_deduplicates_and_sorts_multiple_classifications() -> None:
    use_case = ResolveProteinClassificationUseCase(
        _FakeClassificationPort(
            {
                20: (_hierarchy(5), _hierarchy(3)),
                10: (_hierarchy(5), _hierarchy(2)),
            }
        )
    )

    result = use_case.resolve_target(
        target_id="CHEMBL_TARGET",
        component_ids=[20, 10, 20],
    )

    assert [row.leaf_id for row in result.rows] == [2, 3, 5]
    assert result.rows[2].component_id == 10
    assert result.has_quarantine is False


def test_resolver_emits_missing_row_when_no_classification_exists() -> None:
    use_case = ResolveProteinClassificationUseCase(_FakeClassificationPort({}))

    result = use_case.resolve_target(target_id="CHEMBL_EMPTY", component_ids=[])

    assert len(result.rows) == 1
    assert result.rows[0].classification_status == "missing_classification"
    assert result.rows[0].leaf_id is None


def test_resolver_emits_quarantine_row_for_invalid_chain() -> None:
    use_case = ResolveProteinClassificationUseCase(
        _FakeClassificationPort({}, failing_component_id=10)
    )

    result = use_case.resolve_target(
        target_id="CHEMBL_BAD",
        component_ids=[10],
    )

    assert result.rows[0].classification_status == "quarantined"
    assert result.dq_issues[0].error_code == "protein_classification_resolution_failed"
    assert "broken parent chain" in result.dq_issues[0].message
