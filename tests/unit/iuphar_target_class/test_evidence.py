"""TC-09 evidence ids, reference integrity, and rerun stability."""

from __future__ import annotations

from dataclasses import replace

import pytest

from iuphar_target_class.evidence import (
    ContractDefect,
    EvidenceDraft,
    StoredRun,
    build_evidence_table,
    class_chain_defects,
    content_equal,
    require_class_chain,
    require_resolvable,
    rerun_with_new_rules,
    unsupported_class,
)
from iuphar_target_class.models import (
    ClassificationResult,
    ProviderAnnotation,
    RunProvenance,
)

pytestmark = pytest.mark.unit


def _draft(
    evidence_type: str, source_id: str, content: str, list_name: str
) -> EvidenceDraft:
    return EvidenceDraft("row-1", evidence_type, source_id, content, list_name)


def _drafts() -> tuple[EvidenceDraft, ...]:
    return (
        _draft("local_rule", "ec:3", "Hydrolases", "local"),
        _draft("match", "uniprot_xref", "P35372", "match"),
        _draft("match", "uniprot_xref", "P35372", "match"),
        _draft("iuphar_mapping", "family:1", "Receptor", "match"),
    )


def _provenance(started: str) -> RunProvenance:
    return RunProvenance(
        "snap", None, "plan-v1-r8", None, "2026-11-11T00:00:00Z", started
    )


def test_evidence_reference_integrity() -> None:
    forward = build_evidence_table(_drafts(), run_id="run-1")
    reverse = build_evidence_table(tuple(reversed(_drafts())), run_id="run-1")
    require_resolvable(forward)
    assert forward == reverse
    assert len(forward.records) == 3
    assert forward.local_evidence_ids == ("row-1/local_rule/ec:3/0003",)
    assert forward.match_evidence_ids == (
        "row-1/iuphar_mapping/family:1/0002",
        "row-1/match/uniprot_xref/0001",
    )


def test_evidence_unresolvable_reference() -> None:
    table = build_evidence_table(_drafts(), run_id="run-1")
    damaged = replace(
        table,
        match_evidence_ids=(*table.match_evidence_ids, "row-1/match/missing/0099"),
    )
    with pytest.raises(ContractDefect, match="unresolvable evidence reference"):
        require_resolvable(damaged)


def test_rerun_keeps_ids_and_a_new_rules_version_is_separate() -> None:
    table = build_evidence_table(_drafts(), run_id="run-1")
    payload = b'{"rows":1}\n'
    first = StoredRun("plan-v1-r8", _provenance("t0"), table, payload)
    second = StoredRun("plan-v1-r8", _provenance("t1"), table, payload)
    assert content_equal(first, second)
    fresh = rerun_with_new_rules(first, "plan-v1-r9")
    assert first.rules_version == "plan-v1-r8"
    assert first.payload == payload
    assert fresh.rules_version == "plan-v1-r9"
    assert fresh.status == "pending_recomputation"
    assert fresh.previous_run_id == "run-1"
    assert not hasattr(fresh, "payload")
    assert not hasattr(fresh, "table")


def _classified_row() -> ClassificationResult:
    provenance = _provenance("t0")
    return ClassificationResult(
        input_row_id="row-1",
        snapshot_id="snap",
        input_validation_status="valid",
        input_errors=(),
        match_status="matched",
        matched_target_id="1",
        candidate_target_ids=(),
        iuphar_annotation_status="available",
        iuphar_class="Receptor",
        iuphar_subclass=None,
        iuphar_class_candidates=(),
        iuphar_type_raw=None,
        iuphar_mapping_rule_id=None,
        iuphar_mapping_version=None,
        local_status=None,
        local_class=None,
        local_subclasses=(),
        local_rule_ids=(),
        effective_class="Receptor",
        effective_subclasses=(),
        effective_source="iuphar_normalized",
        decision_status="resolved",
        conflict_codes=(),
        match_evidence_ids=(),
        local_evidence_ids=(),
        row_sha256="abc",
        provenance=provenance,
    )


def test_broken_class_chain_is_a_defect() -> None:
    row = _classified_row()
    assert "mapping_rule" in class_chain_defects(row)
    complete = replace(
        row,
        iuphar_type_raw="gpcr",
        iuphar_mapping_rule_id="type:gpcr",
        iuphar_mapping_version="plan-v1-r8",
        match_evidence_ids=("row-1/iuphar_mapping/family:1/0002",),
    )
    assert class_chain_defects(complete) == ()


def test_evidence_deduplication_keeps_each_input_row() -> None:
    first = _draft("match", "uniprot_xref", "P35372", "match")
    second = replace(first, input_row_id="row-2")
    forward = build_evidence_table((first, second, first), run_id="run-1")
    reverse = build_evidence_table((second, first, second), run_id="run-1")
    assert forward == reverse
    assert len(forward.records) == 2
    assert {r.input_row_id for r in forward.records} == {"row-1", "row-2"}
    assert len(forward.match_evidence_ids) == 2
    require_resolvable(forward)


def test_content_equal_ignores_a_different_run_id() -> None:
    payload = b'{"rows":1}\n'
    left = StoredRun(
        "plan-v1-r8",
        _provenance("t0"),
        build_evidence_table(_drafts(), run_id="run-1"),
        payload,
    )
    right = StoredRun(
        "plan-v1-r8",
        _provenance("t1"),
        build_evidence_table(_drafts(), run_id="run-2"),
        payload,
    )
    assert left.table.run_id != right.table.run_id
    assert content_equal(left, right)
    changed = replace(right, payload=b'{"rows":2}\n')
    assert not content_equal(left, changed)


def test_unsupported_iuphar_class_without_effective_class() -> None:
    row = replace(
        _classified_row(),
        effective_class=None,
        effective_source=None,
        iuphar_mapping_rule_id=None,
        match_evidence_ids=(),
    )
    assert row.iuphar_class
    assert row.effective_class is None
    assert unsupported_class(row)
    supported = replace(
        row,
        iuphar_mapping_rule_id="type:gpcr",
        match_evidence_ids=("row-1/match/uniprot_xref/0001",),
    )
    assert not unsupported_class(supported)


def test_new_rules_request_does_not_relabel_finished_payload() -> None:
    table = build_evidence_table(_drafts(), run_id="run-1")
    previous = StoredRun(
        "plan-v1-r8", _provenance("t0"), table, b'{"class":"Receptor"}'
    )
    request = rerun_with_new_rules(previous, "plan-v1-r9")
    assert not isinstance(request, StoredRun)
    assert previous.provenance.rules_version == "plan-v1-r8"
    assert previous.table.run_id == "run-1"


@pytest.mark.parametrize("annotation_target", ["1", "wrong"])
def test_family_mapping_chain_uses_matching_provider_annotation(
    annotation_target: str,
) -> None:
    row = replace(
        _classified_row(),
        iuphar_annotation_status="partial",
        iuphar_mapping_rule_id="class:Receptor",
        iuphar_mapping_version="plan-v1-r8",
        match_evidence_ids=("row-1/iuphar_mapping/family:1/0002",),
    )
    annotation = ProviderAnnotation(
        annotation_target, None, ("family-1",), None, "human", None
    )
    defects = class_chain_defects(row, annotation=annotation)
    assert ("raw_annotation" in defects) is (annotation_target != "1")
    assert "raw_annotation" in class_chain_defects(row)
    if annotation_target == "1":
        require_class_chain(
            row,
            annotation=annotation,
            table=build_evidence_table(_drafts(), run_id="run-1"),
        )
        assert "raw_annotation" in class_chain_defects(
            row, annotation=replace(annotation, family_ids=())
        )
        assert "mapping_rule" in class_chain_defects(
            replace(row, iuphar_mapping_rule_id=None), annotation=annotation
        )


def test_content_equality_ignores_execution_ids_but_not_evidence_content() -> None:
    first = StoredRun(
        "plan-v1-r8",
        _provenance("t0"),
        build_evidence_table(_drafts(), run_id="run-1"),
        b"same",
    )
    second = StoredRun(
        "plan-v1-r8",
        _provenance("t1"),
        build_evidence_table(_drafts(), run_id="run-2"),
        b"same",
    )
    assert content_equal(first, second)
    changed = replace(second.table.records[0], content="different")
    assert not content_equal(
        first,
        replace(
            second,
            table=replace(second.table, records=(changed, *second.table.records[1:])),
        ),
    )


@pytest.mark.parametrize("missing", ["evidence", "rule"])
def test_direct_class_requires_support_even_when_effective_class_is_empty(
    missing: str,
) -> None:
    row = replace(
        _classified_row(),
        effective_class=None,
        effective_source="none",
        iuphar_mapping_rule_id=None if missing == "rule" else "class:Receptor",
        iuphar_mapping_version="plan-v1-r8",
        match_evidence_ids=() if missing == "evidence" else ("mapping-1",),
    )
    assert unsupported_class(row)


def test_class_chain_requires_mapping_evidence() -> None:
    row = replace(
        _classified_row(),
        iuphar_type_raw="gpcr",
        iuphar_mapping_rule_id="class:Receptor",
        iuphar_mapping_version="plan-v1-r8",
    )
    assert "mapping_evidence" in class_chain_defects(row)


def _supported_direct_row() -> ClassificationResult:
    return replace(
        _classified_row(),
        iuphar_type_raw="gpcr",
        iuphar_mapping_rule_id="class:Receptor",
        iuphar_mapping_version="plan-v1-r8",
        match_evidence_ids=build_evidence_table(
            _drafts(), run_id="run-1"
        ).match_evidence_ids,
    )


def test_duplicate_record_ids_are_rejected_before_reference_resolution() -> None:
    table = build_evidence_table(_drafts(), run_id="run-1")
    duplicate = replace(table.records[0], content="contradictory content")
    with pytest.raises(ContractDefect, match="duplicate.*record"):
        require_resolvable(replace(table, records=(*table.records, duplicate)))


def test_type_chain_rejects_annotation_for_another_target() -> None:
    annotation = ProviderAnnotation("other-target", "gpcr", (), None, "human", None)
    assert "raw_annotation" in class_chain_defects(
        _supported_direct_row(), annotation=annotation
    )


@pytest.mark.parametrize("references", ["other-row", "missing"])
def test_class_chain_rejects_foreign_or_missing_row_references(references: str) -> None:
    drafts = tuple(replace(draft, input_row_id="row-2") for draft in _drafts())
    table = build_evidence_table(drafts, run_id="run-1")
    row = replace(
        _supported_direct_row(),
        match_evidence_ids=table.match_evidence_ids
        if references == "other-row"
        else ("missing",),
    )
    with pytest.raises(ContractDefect, match="row evidence"):
        require_class_chain(row, table=table)


def test_class_chain_requires_a_table_and_accepts_own_row_references() -> None:
    row = _supported_direct_row()
    with pytest.raises(ContractDefect, match="evidence table"):
        require_class_chain(row)
    require_class_chain(row, table=build_evidence_table(_drafts(), run_id="run-1"))


@pytest.mark.parametrize("evidence_type", ["local_rule", "iuphar_mapping"])
def test_local_evidence_list_cannot_substitute_for_iuphar_mapping(
    evidence_type: str,
) -> None:
    table = build_evidence_table(
        (_draft(evidence_type, "rule-1", "Receptor", "local"),), run_id="run-1"
    )
    row = replace(_supported_direct_row(), match_evidence_ids=table.local_evidence_ids)
    with pytest.raises(ContractDefect, match="IUPHAR mapping"):
        require_class_chain(row, table=table)
