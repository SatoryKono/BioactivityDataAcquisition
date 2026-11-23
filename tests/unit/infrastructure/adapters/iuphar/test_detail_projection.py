"""The 3.2.0 detail cells stay canonical JSON, including an absent direct layer."""

from __future__ import annotations

from types import SimpleNamespace

from iuphar_target_class.hierarchy import FamilyPath

from bioetl.infrastructure.adapters.iuphar.detail_projection import detail_projection


def _result() -> SimpleNamespace:
    return SimpleNamespace(
        iuphar_type_raw="gpcr",
        local_status="supported",
        local_subclasses=("GPCR",),
        local_rule_ids=(),
        effective_subclasses=(),
        conflict_codes=(),
        match_evidence_ids=("m",),
        local_evidence_ids=("l",),
    )


def test_detail_projection_renders_paths_as_canonical_json() -> None:
    projected = detail_projection(
        SimpleNamespace(
            result=_result(),
            direct=SimpleNamespace(
                annotation_capability="family_only",
                iuphar_subclasses=("GPCR",),
                paths=(FamilyPath("f", ("root", "leaf"), "leaf>root"),),
            ),
            annotation=SimpleNamespace(family_ids=("f",)),
        )
    )

    assert projected["iuphar_type_raw"] == "gpcr"
    assert projected["iuphar_annotation_capability"] == "family_only"
    assert projected["iuphar_paths"] == (
        '[{"family_id":"f","leaf_to_root":"leaf>root","root_to_leaf":["root","leaf"]}]'
    )
    assert projected["classification_evidence_ids"] == '["l","m"]'
    assert projected["local_rule_ids"] == "[]"


def test_detail_projection_without_a_direct_layer_keeps_empty_collections() -> None:
    projected = detail_projection(
        SimpleNamespace(result=_result(), direct=None, annotation=None)
    )

    assert projected["iuphar_annotation_capability"] is None
    assert projected["iuphar_family_ids"] == "[]"
    assert projected["iuphar_subclasses"] == "[]"
    assert projected["iuphar_paths"] == "[]"
