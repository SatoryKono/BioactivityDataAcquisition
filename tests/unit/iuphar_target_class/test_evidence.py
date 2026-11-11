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
    require_resolvable,
    rerun_with_new_rules,
)
from iuphar_target_class.models import ClassificationResult, RunProvenance

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
    assert content_equal(first, fresh) is False


def test_broken_class_chain_is_a_defect() -> None:
    provenance = _provenance("t0")
    row = ClassificationResult(
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
    assert "mapping_rule" in class_chain_defects(row)
    complete = replace(
        row,
        iuphar_type_raw="gpcr",
        iuphar_mapping_rule_id="type:gpcr",
        iuphar_mapping_version="plan-v1-r8",
    )
    assert class_chain_defects(complete) == ()
