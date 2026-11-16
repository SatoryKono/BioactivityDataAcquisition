"""Reference acceptance must execute real logic and reject unbound receipts."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from iuphar_target_class.integration_acceptance import (
    CHECKS,
    IntegrationAcceptanceRequest,
    run_integration_acceptance,
)
from iuphar_target_class.matching import CatalogTarget
from iuphar_target_class.models import ProviderAnnotation, RunProvenance
from iuphar_target_class.pipeline import IndexedSnapshot
from iuphar_target_class.stage0.io import canonical_json_bytes, sha256_bytes, sha256_file


def _write(path, document):
    path.write_bytes(canonical_json_bytes(document))
    return sha256_file(path)


@pytest.fixture
def acceptance_inputs(tmp_path):
    """Explicitly synthetic contract inputs, never a biological reference set."""
    raw = canonical_json_bytes({"targetId": 1, "type": "gpcr"}).decode()
    snapshot = IndexedSnapshot.build(
        snapshot_id="synthetic-fixture", mapping_version="synthetic-mapping",
        complete=True,
        catalog=(CatalogTarget("1", ("P12345",), None, None, "9606", ("Fixture",), ()),),
        annotations={"1": ProviderAnnotation("1", "gpcr", (), sha256_bytes(raw.encode()), "9606", raw)},
        family_nodes=(), type_to_class={"gpcr": "Receptor"}, family_to_class={},
    )
    content = b"input_row_id,target_kind,target_chembl_id,target_id,uniprot,organism,name\nr1,protein,CHEMBL1,1,P12345,9606,Fixture\n"
    (tmp_path / "frozen.csv").write_bytes(content)
    names = ("content_checks.csv", "m_code_versions.csv", "provenance_map.csv", "stage_report.json")
    hashes = {}
    for name in names:
        (tmp_path / name).write_bytes(b"synthetic test artifact")
        hashes[name] = sha256_file(tmp_path / name)
    stage0 = tmp_path / "stage0.json"
    stage0_hash = _write(stage0, {
        "artifact": "stage0_manifest", "stage": "0", "artifact_sha256": hashes,
        "copies": [{"source_path": "source.csv", "copy_path": "frozen.csv",
                    "sha256": sha256_bytes(content), "byte_count": len(content)}],
    })
    (tmp_path / "review.txt").write_text("Synthetic test expected Receptor", encoding="utf-8")
    labels = tmp_path / "labels.json"
    labels_hash = _write(labels, {
        "artifact": "bioetl_iuphar_reference_cases", "schema_version": 1,
        "reviewer_reference": "synthetic contract test only",
        "approval_reference": "synthetic contract test only", "environment": "unit-test",
        "snapshot_manifest_sha256": "a" * 64, "stage0_manifest_sha256": stage0_hash,
        "selected_source_paths": ["source.csv"], "expected_rows": 1,
        "source_imports": [{"source_path": "source.csv", "format_version": "bioetl_target_kernel_csv_v1", "target_kind": "protein"}],
        "cases": [{"input_row_id": "r1", "expected": {"iuphar_class": "Receptor", "matched_target_id": "1"},
                   "source_references": [{"path": "review.txt", "sha256": sha256_file(tmp_path / "review.txt")}]}],
    })
    report = tmp_path / "pipeline-report.json"
    _write(report, {"identity": {"pipeline": "chembl_target", "run_id": "pipeline-fixture", "status": "success"}})
    (tmp_path / "evidence.json").write_bytes(b"[]\n")
    proof = tmp_path / "pipeline-proof.json"
    _write(proof, {
        "artifact": "bioetl_iuphar_pipeline_evidence", "pipeline_name": "chembl_target",
        "run_id": "pipeline-fixture", "mode": "shadow", "status": "complete", "row_count": 1,
        "snapshot_manifest_sha256": "a" * 64,
        "artifact_sha256": {"evidence.json": sha256_file(tmp_path / "evidence.json")},
    })
    provenance = RunProvenance("synthetic-fixture", "bioetl-iuphar-input-v1", "plan-v1-r8", "3.1.0", "frozen", "frozen")
    request = IntegrationAcceptanceRequest(stage0, labels, labels_hash, "a" * 64,
                                           provenance, "reference-fixture", proof, report)
    return request, snapshot


def test_acceptance_executes_references_and_keeps_accuracy_unaccepted(tmp_path, acceptance_inputs):
    request, snapshot = acceptance_inputs
    report = run_integration_acceptance(request, snapshot=snapshot, output_dir=tmp_path / "result")
    assert report["status"] == "PASS"
    assert report["checks"] == dict.fromkeys(CHECKS, "PASS")
    assert report["biological_accuracy_accepted"] is False
    assert report["reference_cases_accepted"] is True
    assert len(report["output_sha256"]) == 6
    assert (tmp_path / "result/execution-config.json").exists()
    from bioetl.infrastructure.adapters.iuphar import validate_acceptance_receipt

    validate_acceptance_receipt(report, snapshot_manifest_sha256=request.snapshot_manifest_sha256)


def test_unversioned_species_names_cannot_enter_reference_acceptance(tmp_path, acceptance_inputs):
    request, snapshot = acceptance_inputs
    labels = json.loads(request.expected_labels.read_bytes())
    labels.pop("source_imports")
    request = replace(request, expected_labels_sha256=_write(request.expected_labels, labels))
    report = run_integration_acceptance(request, snapshot=snapshot, output_dir=tmp_path / "result")
    assert report["status"] == "BLOCKED_INPUT"
    assert "canonical TaxID" in report["reason"]


def test_reference_mismatch_is_fail_not_an_invented_pass(tmp_path, acceptance_inputs):
    request, snapshot = acceptance_inputs
    labels = json.loads(request.expected_labels.read_bytes())
    labels["cases"][0]["expected"]["iuphar_class"] = "Enzyme"
    request = replace(request, expected_labels_sha256=_write(request.expected_labels, labels))
    report = run_integration_acceptance(request, snapshot=snapshot, output_dir=tmp_path / "result")
    assert report["status"] == "FAIL"
    assert report["reference_cases_accepted"] is False


def test_missing_real_pipeline_proof_blocks_acceptance(tmp_path, acceptance_inputs):
    request, snapshot = acceptance_inputs
    report = run_integration_acceptance(replace(request, pipeline_proof=None), snapshot=snapshot,
                                        output_dir=tmp_path / "result")
    assert report["status"] == "BLOCKED_INPUT"
    assert report["checks"]["pipeline_integration"] == "NOT_RUN"


def test_empty_canonical_stage0_is_not_replaced_by_fixture(tmp_path, acceptance_inputs):
    request, snapshot = acceptance_inputs
    document = json.loads(request.stage0_manifest.read_bytes())
    document["copies"] = []
    stage0_hash = _write(request.stage0_manifest, document)
    labels = json.loads(request.expected_labels.read_bytes())
    labels["stage0_manifest_sha256"] = stage0_hash
    request = replace(request, expected_labels_sha256=_write(request.expected_labels, labels))
    report = run_integration_acceptance(request, snapshot=snapshot, output_dir=tmp_path / "result")
    assert report["status"] == "BLOCKED_INPUT"
    assert report["checks"]["stage0_admission"] == "NOT_RUN"


def test_changed_pipeline_bytes_cannot_qualify(tmp_path, acceptance_inputs):
    request, snapshot = acceptance_inputs
    (tmp_path / "evidence.json").write_bytes(b"changed")
    report = run_integration_acceptance(request, snapshot=snapshot, output_dir=tmp_path / "result")
    assert report["status"] == "BLOCKED_INPUT"
    assert "digest mismatch" in report["reason"]


def test_previous_acceptance_occurrence_is_immutable(tmp_path, acceptance_inputs):
    request, snapshot = acceptance_inputs
    output = tmp_path / "result"
    run_integration_acceptance(request, snapshot=snapshot, output_dir=output)
    before = (output / "acceptance.json").read_bytes()
    with pytest.raises(FileExistsError):
        run_integration_acceptance(request, snapshot=snapshot, output_dir=output)
    assert (output / "acceptance.json").read_bytes() == before
