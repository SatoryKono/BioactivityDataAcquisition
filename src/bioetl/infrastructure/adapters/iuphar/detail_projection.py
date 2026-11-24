"""Project one IUPHAR row result onto the persisted 3.2.0 detail columns."""

from __future__ import annotations

from bioetl.domain.normalization.target_classification_values import (
    project_classification_detail,
)
from iuphar_target_class.pipeline import RowResult


def detail_projection(row: object | None, *, computed: bool) -> dict[str, str | None]:
    """Return canonical detail text, or nulls when the row was not computed."""
    if not computed or row is None:
        return project_classification_detail(
            computed=False,
            iuphar_type_raw=None,
            annotation_status=None,
            family_ids=(),
            subclasses=(),
            paths=(),
            local_status=None,
            local_subclasses=(),
            local_rule_ids=(),
            effective_subclasses=(),
            conflict_codes=(),
            evidence_ids=((), ()),
        )
    if not isinstance(row, RowResult):
        raise TypeError("classification detail requires a row result")
    result = row.result
    annotation = row.annotation
    direct = row.direct
    subclass = result.iuphar_subclass
    return project_classification_detail(
        computed=result.input_validation_status != "invalid_input",
        iuphar_type_raw=result.iuphar_type_raw,
        annotation_status=result.iuphar_annotation_status,
        match_status=result.match_status,
        family_ids=annotation.family_ids if annotation is not None else (),
        subclasses=(subclass,) if subclass else (),
        paths=(
            tuple((item.family_id, item.root_to_leaf) for item in direct.paths)
            if direct is not None
            else ()
        ),
        local_status=result.local_status,
        local_subclasses=result.local_subclasses,
        local_rule_ids=result.local_rule_ids,
        effective_subclasses=result.effective_subclasses,
        conflict_codes=result.conflict_codes,
        evidence_ids=(result.match_evidence_ids, result.local_evidence_ids),
    )
