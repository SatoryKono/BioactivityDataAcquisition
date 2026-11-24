"""Synthetic software contracts for bounded reference declarations, not approval."""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from iuphar_target_class.models import ProviderAnnotation, RunProvenance
from iuphar_target_class.matching import CatalogTarget
from iuphar_target_class.pipeline import IndexedSnapshot, classify_batch
from iuphar_target_class.pipeline_acceptance import load_admitted_cohort
from iuphar_target_class.reference_coverage import (
    REQUIRED_REFERENCE_CATEGORIES,
    REQUIRED_REFERENCE_FIELDS,
    validate_executed_reference_coverage,
    validate_reference_coverage_receipt,
    validate_reference_specification,
)
from iuphar_target_class.stage0.io import (
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)
from tests.unit.iuphar_target_class.test_stage0_v2 import _bundle
from tests.unit.iuphar_target_class.test_integration_acceptance import (
    acceptance_inputs as acceptance_inputs,
    _stored_proof,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def reference_inputs(tmp_path: Path):
    manifest, plan, _ = _bundle(tmp_path)
    cohort = load_admitted_cohort(manifest, plan)
    proof = tmp_path / "engineering-proof.txt"
    proof.write_bytes(
        b"Synthetic software expectation only; no real scientific review supplied"
    )
    reference = {"path": proof.name, "sha256": sha256_file(proof)}
    row_id = "chembl.target:CHEMBL1"
    matrix = {
        name: {
            "status": "out_of_scope",
            "case_row_ids": [],
            "rationale": "Excluded by this explicitly synthetic software fixture scope",
            "source_references": [reference],
        }
        for name in REQUIRED_REFERENCE_CATEGORIES
    }
    matrix["direct_type"] = {
        "status": "real_reference",
        "case_row_ids": [row_id],
        "rationale": "Exercises a reviewed-case contract using synthetic bytes only",
        "source_references": [reference],
    }
    provenance = RunProvenance(
        "synthetic-snapshot",
        "bioetl-iuphar-input-v1",
        "plan-v1-r9",
        "3.1.0",
        "2026-11-16T00:00:00Z",
        "2026-11-16T00:01:00Z",
        matching_policy_version="rf002-uniprot-roles-2026-11-23",
    )
    # The synthetic row carries EC 1.1.1.1, so the local catalog now supports
    # Enzyme beside the direct Receptor label and the decision stays in review.
    expected = {
        "match_status": "matched",
        "matched_target_id": "1",
        "iuphar_class": "Receptor",
        "iuphar_annotation_status": "available",
        "decision_status": "requires_review",
    }
    spec = {
        "artifact": "bioetl_iuphar_reference_cases",
        "schema_version": 2,
        "fixture_kind": "synthetic_contract_fixture",
        "reviewer_reference": "synthetic software contract; no scientific reviewer approval",
        "approval_reference": "synthetic software contract only",
        "environment": "unit-test",
        "snapshot_manifest_sha256": "a" * 64,
        "stage0_manifest_sha256": plan.manifest_sha256,
        "selected_source_paths": list(plan.selected_source_paths),
        "expected_rows": 1,
        "source_imports": [
            {
                "source_path": item.source_path,
                "format_version": item.format_version,
                "target_kind": item.target_kind,
            }
            for item in plan.source_imports
        ],
        "cohort_manifest_sha256": cohort.cohort_manifest_sha256,
        "conversion_ledger_sha256": cohort.conversion_ledger_sha256,
        "normalization_version": provenance.normalization_version,
        "rules_version": provenance.rules_version,
        "classification_schema_version": provenance.schema_version,
        "matching_policy_version": provenance.matching_policy_version,
        "taxonomy_scope": ["9606"],
        "scope_declaration": {
            "scope_id": "synthetic-contract-scope",
            "kind": "bounded_reviewed_reference",
            "approval_reference": "synthetic scope fixture only",
            "limitations": [
                "No real biological accuracy or reviewer approval established"
            ],
            "reviewed_row_ids": [row_id],
            "unreviewed_row_ids": [],
        },
        "reference_matrix": matrix,
        "cases": [
            {
                "input_row_id": row_id,
                "categories": ["direct_type"],
                "reference_status": "real_reference",
                "expected": expected,
                "source_references": [reference],
            }
        ],
    }
    return cohort, provenance, spec


def _validate(reference_inputs, root: Path):
    cohort, provenance, spec = reference_inputs
    return validate_reference_specification(
        spec, cohort=cohort, provenance=provenance, root=root
    )


def test_bounded_scope_declares_every_category_without_accepting_accuracy(
    tmp_path: Path, reference_inputs
):
    receipt = _validate(reference_inputs, tmp_path)
    assert receipt["scientific_status"] == "bounded_reference_cases_only"
    assert receipt["biological_accuracy_accepted"] is False
    assert set(receipt["reference_coverage"]["categories"]) == set(
        REQUIRED_REFERENCE_CATEGORIES
    )


@pytest.mark.parametrize("field", sorted(REQUIRED_REFERENCE_FIELDS))
def test_real_case_cannot_omit_required_expected_field(
    tmp_path: Path, reference_inputs, field: str
):
    _, _, spec = reference_inputs
    spec["cases"][0]["expected"].pop(field)
    with pytest.raises(ValueError, match="complete direct/match/annotation/decision"):
        _validate(reference_inputs, tmp_path)


@pytest.mark.parametrize("category", ["local_vs_direct", "non_applicable"])
def test_real_case_requires_category_specific_expected_fields(
    tmp_path: Path, reference_inputs, category: str
):
    _, _, spec = reference_inputs
    matrix = spec["reference_matrix"]
    matrix[category], matrix["direct_type"] = (
        matrix["direct_type"],
        matrix[category],
    )
    spec["cases"][0]["categories"] = [category]
    with pytest.raises(ValueError, match="category-specific expectations"):
        _validate(reference_inputs, tmp_path)


def test_missing_category_cannot_be_silently_covered_by_one_case(
    tmp_path: Path, reference_inputs
):
    _, _, spec = reference_inputs
    spec["reference_matrix"].pop("identity_conflict")
    with pytest.raises(ValueError, match="all mandatory reference categories"):
        _validate(reference_inputs, tmp_path)


def test_engineering_disposition_does_not_become_real_review_coverage(
    tmp_path: Path, reference_inputs
):
    _, _, spec = reference_inputs
    spec["reference_matrix"]["direct_type"]["status"] = "engineering_only"
    spec["cases"][0]["reference_status"] = "engineering_only"
    with pytest.raises(ValueError, match="reviewed reference coverage"):
        _validate(reference_inputs, tmp_path)


@pytest.mark.parametrize(
    "field",
    ["cohort_manifest_sha256", "conversion_ledger_sha256", "normalization_version"],
)
def test_foreign_cohort_conversion_or_profile_is_rejected(
    tmp_path: Path, reference_inputs, field: str
):
    _, _, spec = reference_inputs
    spec[field] = "d" * 64
    with pytest.raises(ValueError, match="another canonical cohort|versions differ"):
        _validate(reference_inputs, tmp_path)


def test_coverage_partition_must_account_for_every_cohort_row(
    tmp_path: Path, reference_inputs
):
    _, _, spec = reference_inputs
    spec["scope_declaration"]["unreviewed_row_ids"] = ["invented-row"]
    with pytest.raises(ValueError, match="scope differs"):
        _validate(reference_inputs, tmp_path)


def test_changed_review_proof_is_rejected_before_execution(
    tmp_path: Path, reference_inputs
):
    (tmp_path / "engineering-proof.txt").write_bytes(b"changed")
    with pytest.raises(ValueError, match="proof digest mismatch"):
        _validate(reference_inputs, tmp_path)


def _full_receipt(reference_inputs, root: Path):
    _, _, spec = reference_inputs
    receipt = _validate(reference_inputs, root)
    bindings = {
        "stage0_manifest": "stage0_manifest_sha256",
        "expected_labels": "expected_labels_sha256",
        "cohort_manifest": "cohort_manifest_sha256",
        "conversion_ledger": "conversion_ledger_sha256",
        "pipeline_proof": "pipeline_proof_sha256",
        "pipeline_report": "pipeline_report_sha256",
    }
    for key in bindings.values():
        receipt.setdefault(key, spec.get(key, "b" * 64))
    outputs = dict.fromkeys(
        (
            "classification.json",
            "evidence.json",
            "candidates.json",
            "components.json",
            "diagnostics.json",
            "metrics.json",
        ),
        "c" * 64,
    )
    receipt["output_sha256"] = outputs
    refs = [
        {
            "kind": kind,
            "immutable_uri": (root / (kind + ".json")).as_uri(),
            "sha256": receipt[key],
        }
        for kind, key in bindings.items()
    ]
    refs.extend(
        {"kind": name, "immutable_uri": (root / name).as_uri(), "sha256": digest}
        for name, digest in outputs.items()
    )
    receipt["artifact_references"] = refs
    return receipt


def test_receipt_is_replayable_only_with_all_bound_reference_identities(
    tmp_path: Path, reference_inputs
):
    receipt = _full_receipt(reference_inputs, tmp_path)
    validate_reference_coverage_receipt(receipt)
    broken = copy.deepcopy(receipt)
    broken["artifact_references"].pop()
    with pytest.raises(ValueError, match="replayable reference"):
        validate_reference_coverage_receipt(broken)


def test_scientific_status_cannot_be_promoted_by_receipt_flag(
    tmp_path: Path, reference_inputs
):
    receipt = _full_receipt(reference_inputs, tmp_path)
    receipt["biological_accuracy_accepted"] = True
    with pytest.raises(ValueError, match="broad biological accuracy"):
        validate_reference_coverage_receipt(receipt)


@pytest.mark.parametrize("suffix", [".env", ".ENV.local", "config.EnV", "config%2EENV"])
def test_receipt_rejects_environment_uris_without_creating_files(
    tmp_path: Path, reference_inputs, suffix: str
):
    receipt = _full_receipt(reference_inputs, tmp_path)
    receipt["artifact_references"][0]["immutable_uri"] = "file:///proof/" + suffix
    with pytest.raises(ValueError, match="environment files"):
        validate_reference_coverage_receipt(receipt)


def test_declared_scenario_must_actually_occur(tmp_path: Path, reference_inputs):
    cohort, provenance, spec = reference_inputs
    _validate(reference_inputs, tmp_path)
    raw = canonical_json_bytes({"targetId": 1, "type": "gpcr"}).decode()
    snapshot = IndexedSnapshot.build(
        snapshot_id="synthetic-snapshot",
        mapping_version="synthetic",
        complete=True,
        catalog=(
            CatalogTarget("1", ("P12345",), None, None, "9606", ("Fixture",), ()),
        ),
        annotations={
            "1": ProviderAnnotation(
                "1", "gpcr", (), sha256_bytes(raw.encode()), "9606", raw
            )
        },
        family_nodes=(),
        type_to_class={"gpcr": "Receptor"},
        family_to_class={},
    )
    batch = classify_batch(
        cohort.rows, snapshot=snapshot, provenance=provenance, run_id="software-fixture"
    )
    validate_executed_reference_coverage(batch, spec)
    row = batch.rows[0]
    changed = replace(
        batch,
        rows=(replace(row, result=replace(row.result, iuphar_mapping_rule_id=None)),),
    )
    with pytest.raises(AssertionError, match="scenario did not execute"):
        validate_executed_reference_coverage(changed, spec)


def test_full_v2_producer_binds_actual_replay_dependencies(
    tmp_path: Path, acceptance_inputs, reference_inputs
):
    from iuphar_target_class.integration_acceptance import run_integration_acceptance

    old_request, snapshot = acceptance_inputs
    cohort, _, spec = reference_inputs
    stage0 = tmp_path / "stage0/manifest.json"
    spec["snapshot_manifest_sha256"] = old_request.snapshot_manifest_sha256
    labels = tmp_path / "labels-v2.json"
    labels.write_bytes(canonical_json_bytes(spec))
    proof = _stored_proof(
        tmp_path / "v2-proof",
        snapshot,
        old_request.provenance,
        row_id=cohort.rows[0].input_row_id,
        rows=cohort.rows,
    )
    report = json.loads(old_request.pipeline_report.read_bytes())
    facts = report["observations"]["Target Classification"]["facts"]
    facts.update(
        evidence_manifest_uri=proof.as_uri(),
        evidence_manifest_sha256=sha256_file(proof),
    )
    report_path = tmp_path / "v2-report.json"
    report_path.write_bytes(canonical_json_bytes(report))
    request = replace(
        old_request,
        stage0_manifest=stage0,
        expected_labels=labels,
        expected_labels_sha256=sha256_file(labels),
        pipeline_proof=proof,
        pipeline_report=report_path,
    )
    output = tmp_path / "reference-v2-output"
    receipt = run_integration_acceptance(request, snapshot=snapshot, output_dir=output)
    assert receipt["status"] == "PASS", receipt
    assert receipt["schema_version"] == 2
    validate_reference_coverage_receipt(receipt)
    from urllib.parse import urlsplit
    from urllib.request import url2pathname

    kinds = {item["kind"] for item in receipt["artifact_references"]}
    assert {
        "stage0_manifest",
        "expected_labels",
        "conversion_ledger",
        "cohort_manifest",
        "pipeline_proof",
        "pipeline_report",
        "stage0_evidence",
    }.issubset(kinds)
    for reference in receipt["artifact_references"]:
        actual = Path(url2pathname(urlsplit(reference["immutable_uri"]).path))
        assert sha256_file(actual) == reference["sha256"]
