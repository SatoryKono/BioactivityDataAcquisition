"""The 3.2.0 detail cells stay canonical JSON, including an absent direct layer."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from iuphar_target_class.hierarchy import FamilyPath
from iuphar_target_class.pipeline import RowResult

from bioetl.infrastructure.adapters.iuphar.detail_projection import detail_projection

pytestmark = pytest.mark.unit


def _result() -> SimpleNamespace:
    return SimpleNamespace(
        input_validation_status="valid",
        iuphar_subclass="GPCR",
        iuphar_type_raw="gpcr",
        iuphar_annotation_status="available",
        match_status="matched",
        local_status="supported",
        local_subclasses=("GPCR",),
        local_rule_ids=(),
        effective_subclasses=(),
        conflict_codes=(),
        match_evidence_ids=("m",),
        local_evidence_ids=("l",),
    )


def _row(
    result: SimpleNamespace,
    direct: SimpleNamespace | None,
    annotation: SimpleNamespace | None,
) -> RowResult:
    row = MagicMock(spec=RowResult)
    row.result = result
    row.direct = direct
    row.annotation = annotation
    return row


def test_detail_projection_renders_paths_as_canonical_json() -> None:
    projected = detail_projection(
        _row(
            _result(),
            SimpleNamespace(
                paths=(FamilyPath("f", ("root", "leaf"), "leaf>root"),),
            ),
            SimpleNamespace(family_ids=("f",)),
        ),
        computed=True,
    )

    assert projected["iuphar_type_raw"] == "gpcr"
    assert projected["iuphar_subclasses"] == '["GPCR"]'
    assert projected["iuphar_source_completeness"] == "typed"
    assert projected["iuphar_family_paths"] == (
        '[{"family_id":"f","root_to_leaf":["root","leaf"]}]'
    )
    assert projected["classification_evidence_refs"] == (
        '{"local_evidence_ids":["l"],"match_evidence_ids":["m"]}'
    )
    assert projected["local_rule_ids"] == "[]"


def test_detail_projection_without_a_direct_layer_keeps_empty_collections() -> None:
    projected = detail_projection(
        _row(_result(), None, None),
        computed=True,
    )

    assert projected["iuphar_source_completeness"] == "typed"
    assert projected["iuphar_family_ids"] == "[]"
    assert projected["iuphar_subclasses"] == '["GPCR"]'
    assert projected["iuphar_family_paths"] == "[]"
    assert projected["classification_evidence_refs"] == (
        '{"local_evidence_ids":["l"],"match_evidence_ids":["m"]}'
    )


def test_detail_projection_without_computation_stays_null() -> None:
    projected = detail_projection(None, computed=False)

    assert projected["iuphar_type_raw"] is None
    assert projected["iuphar_family_paths"] is None
    assert projected["classification_evidence_refs"] is None
