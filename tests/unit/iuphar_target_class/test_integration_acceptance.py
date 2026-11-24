"""Reference acceptance must execute real logic and reject unbound receipts."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from iuphar_target_class.integration_acceptance import (
    CHECKS,
    IntegrationAcceptanceRequest,
    run_integration_acceptance,
    verify_pipeline_proof,
    _check_reference_case,
    _verified_labels,
)
from iuphar_target_class.matching import CatalogTarget
from iuphar_target_class.models import ProviderAnnotation, RawTargetRow, RunProvenance
from iuphar_target_class.pipeline import IndexedSnapshot, classify_batch
from iuphar_target_class.pipeline_io import (
    read_bioetl_target_kernel_csv_v1,
    render_batch,
)
from iuphar_target_class.pipeline_proof import (
    PipelineExecutionBinding,
    _classification_input_projection,
    execution_semantics,
)
from iuphar_target_class.policy import LOCAL_CATALOG_VERSION
from iuphar_target_class.stage0.io import (
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)

pytestmark = pytest.mark.unit


def _write(path, document):
    path.write_bytes(canonical_json_bytes(document))
    return sha256_file(path)


@pytest.mark.parametrize("codes", [[], ["conflicting_sources"]])
def test_reference_conflict_codes_compare_json_collections(
    tmp_path, acceptance_inputs, codes
):
    request, snapshot = acceptance_inputs
    batch = classify_batch(
        (
            RawTargetRow(
                "r1",
                {"target_id": "1", "uniprot": "P12345", "organism": "9606"},
                "protein",
            ),
        ),
        snapshot=snapshot,
        provenance=request.provenance,
        run_id="reference-fixture",
    )
    source = tmp_path / "reviewed-source.json"
    source.write_bytes(b"reviewed source")
    case = {
        "input_row_id": "r1",
        "source_references": [{"path": source.name, "sha256": sha256_file(source)}],
        "expected": {"conflict_codes": codes},
    }
    actual = replace(batch.rows[0].result, conflict_codes=tuple(codes))
    assert actual.conflict_codes == tuple(codes)
    _check_reference_case(case, actual, tmp_path, frozenset({"conflict_codes"}))


def test_classification_input_projection_ignores_csv_transport_metadata():
    csv_side = {
        "target_id": "1",
        "uniprot": "",
        "organism": "9606",
        "import_profile": "bioetl_target_kernel_csv_v1",
        "source_path": "source.csv",
        "source_sha256": "a" * 64,
        "source_record": "1",
    }
    runtime_side = {"target_id": "1", "uniprot": None, "organism": "9606"}
    assert _classification_input_projection(
        csv_side
    ) == _classification_input_projection(runtime_side)
    assert "import_profile" not in _classification_input_projection(csv_side)


def test_classification_input_projection_equates_null_and_absent_business_fields():
    silver_side = {
        "target_id": "1",
        "organism": "9606",
        "source_business_data": json.dumps(
            {"target_id": "CHEMBL1", "protein_classifications": None},
            separators=(",", ":"),
            sort_keys=True,
        ),
    }
    runtime_side = {
        "target_id": "1",
        "organism": "9606",
        "source_business_data": json.dumps(
            {"target_id": "CHEMBL1"},
            separators=(",", ":"),
            sort_keys=True,
        ),
    }
    assert _classification_input_projection(
        silver_side
    ) == _classification_input_projection(runtime_side)
    projected = _classification_input_projection(silver_side)
    assert "protein_classifications" not in json.loads(
        projected["source_business_data"]
    )


def test_stale_pipeline_proof_rejects_changed_cohort_semantics(acceptance_inputs):
    request, snapshot = acceptance_inputs
    changed = RawTargetRow(
        "r1",
        {"target_id": "1", "uniprot": "P00000", "organism": "9606"},
        "protein",
    )
    batch = classify_batch(
        (changed,),
        snapshot=snapshot,
        provenance=request.provenance,
        run_id="reference-fixture",
    )
    assert batch.rows[0].result.iuphar_class is None
    with pytest.raises(ValueError, match="admitted"):
        verify_pipeline_proof(
            request.pipeline_proof,
            request.snapshot_manifest_sha256,
            request.pipeline_report,
            provenance=request.provenance,
            expected_execution=(
                PipelineExecutionBinding(
                    changed.input_row_id,
                    changed.fields,
                    execution_semantics(batch.rows[0].result),
                ),
            ),
        )


def test_pipeline_proof_for_another_cohort_is_rejected(acceptance_inputs):
    request, _ = acceptance_inputs
    with pytest.raises(ValueError, match="another admitted cohort"):
        verify_pipeline_proof(
            request.pipeline_proof,
            request.snapshot_manifest_sha256,
            request.pipeline_report,
            provenance=request.provenance,
            expected_row_ids=("another-row",),
        )


@pytest.fixture
def acceptance_inputs(tmp_path):
    """Explicitly synthetic contract inputs, never a biological reference set."""
    raw = canonical_json_bytes({"targetId": 1, "type": "gpcr"}).decode()
    snapshot = IndexedSnapshot.build(
        snapshot_id="synthetic-fixture",
        mapping_version="synthetic-mapping",
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
    content = b"input_row_id,target_kind,target_chembl_id,target_id,uniprot,organism,name\nr1,protein,CHEMBL1,1,P12345,9606,Fixture\n"
    (tmp_path / "frozen.csv").write_bytes(content)
    names = (
        "content_checks.csv",
        "m_code_versions.csv",
        "provenance_map.csv",
        "stage_report.json",
    )
    hashes = {}
    for name in names:
        (tmp_path / name).write_bytes(b"synthetic test artifact")
        hashes[name] = sha256_file(tmp_path / name)
    stage0 = tmp_path / "stage0.json"
    stage0_hash = _write(
        stage0,
        {
            "artifact": "stage0_manifest",
            "stage": "0",
            "artifact_sha256": hashes,
            "copies": [
                {
                    "source_path": "source.csv",
                    "copy_path": "frozen.csv",
                    "sha256": sha256_bytes(content),
                    "byte_count": len(content),
                }
            ],
        },
    )
    (tmp_path / "review.txt").write_text(
        "Synthetic test expected Receptor", encoding="utf-8"
    )
    labels = tmp_path / "labels.json"
    labels_hash = _write(
        labels,
        {
            "artifact": "bioetl_iuphar_reference_cases",
            "schema_version": 1,
            "reviewer_reference": "synthetic contract test only",
            "approval_reference": "synthetic contract test only",
            "environment": "unit-test",
            "snapshot_manifest_sha256": "a" * 64,
            "stage0_manifest_sha256": stage0_hash,
            "selected_source_paths": ["source.csv"],
            "expected_rows": 1,
            "source_imports": [
                {
                    "source_path": "source.csv",
                    "format_version": "bioetl_target_kernel_csv_v1",
                    "target_kind": "protein",
                }
            ],
            "cases": [
                {
                    "input_row_id": "r1",
                    "expected": {"iuphar_class": "Receptor", "matched_target_id": "1"},
                    "source_references": [
                        {
                            "path": "review.txt",
                            "sha256": sha256_file(tmp_path / "review.txt"),
                        }
                    ],
                }
            ],
        },
    )
    provenance = RunProvenance(
        "synthetic-fixture",
        "bioetl-iuphar-input-v1",
        LOCAL_CATALOG_VERSION,
        "3.1.0",
        "frozen",
        "frozen",
        matching_policy_version="rf002-uniprot-roles-2026-11-23",
    )
    proof = _stored_proof(tmp_path, snapshot, provenance)
    report = tmp_path / "pipeline-report.json"
    proof_document = json.loads(proof.read_bytes())
    _write(
        report,
        {
            "schema_version": "pipeline_run_report_v2",
            "identity": {
                "pipeline": "chembl_target",
                "run_id": "pipeline-fixture",
                "status": "success",
            },
            "observations": {
                "Target Classification": {
                    "verdict": "OK",
                    "reason": "verified_target_classification_evidence",
                    "facts": {
                        **{
                            key: value
                            for key, value in proof_document.items()
                            if key
                            in {
                                "run_id",
                                "mode",
                                "snapshot_manifest_sha256",
                                "profile_sha256",
                                "normalization_version",
                                "rules_version",
                                "classification_schema_version",
                                "matching_policy_version",
                                "row_count",
                            }
                        },
                        "evidence_manifest_uri": proof.as_uri(),
                        "evidence_manifest_sha256": sha256_file(proof),
                    },
                }
            },
        },
    )
    request = IntegrationAcceptanceRequest(
        stage0,
        labels,
        labels_hash,
        "a" * 64,
        provenance,
        "reference-fixture",
        proof,
        report,
        species_taxon_ids=frozenset({"9606"}),
    )
    return request, snapshot


def _stored_proof(tmp_path, snapshot, provenance, row_id="r1", *, rows=None):
    """Use actual kernel outputs and the actual persistence/finalization path."""
    from bioetl.domain.entities.target_classification_boundary import (
        TargetClassificationArtifact,
        TargetClassificationResult,
    )
    from bioetl.infrastructure.adapters.iuphar import (
        LocalTargetClassificationEvidenceStore,
    )

    run_id = "pipeline-fixture"
    if rows is None:
        rows = read_bioetl_target_kernel_csv_v1(
            (tmp_path / "frozen.csv").read_bytes(),
            source_path="source.csv",
            target_kind="protein",
        )
    assert tuple(row.input_row_id for row in rows) == (row_id,)
    batch = classify_batch(
        rows,
        snapshot=snapshot,
        provenance=provenance,
        run_id=run_id,
    )
    store = LocalTargetClassificationEvidenceStore(
        tmp_path / "actual-store",
        mode="shadow",
        snapshot_manifest_sha256="a" * 64,
        profile_sha256="b" * 64,
        versions={
            "normalization_version": provenance.normalization_version,
            "rules_version": provenance.rules_version,
            "classification_schema_version": provenance.schema_version,
            "matching_policy_version": provenance.matching_policy_version,
        },
    )
    result = TargetClassificationResult(
        row_id,
        {"target_class_profile_sha256": "b" * 64},
        tuple(
            TargetClassificationArtifact(name, raw)
            for name, raw in render_batch(batch).items()
        ),
    )
    store.publish_result(result, run_id=run_id, batch_id="batch-0")
    store.finalize_run(run_id=run_id, expected_row_ids=(row_id,))
    return tmp_path / "actual-store" / run_id / "manifest.json"


def test_acceptance_executes_references_and_keeps_accuracy_unaccepted(
    tmp_path, acceptance_inputs
):
    request, snapshot = acceptance_inputs
    report = run_integration_acceptance(
        request, snapshot=snapshot, output_dir=tmp_path / "result"
    )
    assert report["status"] == "PASS"
    assert report["checks"] == dict.fromkeys(CHECKS, "PASS")
    assert report["biological_accuracy_accepted"] is False
    assert report["reference_cases_accepted"] is True
    assert len(report["output_sha256"]) == 6
    assert (tmp_path / "result/execution-config.json").exists()
    from bioetl.infrastructure.adapters.iuphar import validate_acceptance_receipt

    validate_acceptance_receipt(
        report, snapshot_manifest_sha256=request.snapshot_manifest_sha256
    )


def test_unversioned_species_names_cannot_enter_reference_acceptance(
    tmp_path, acceptance_inputs
):
    request, snapshot = acceptance_inputs
    labels = json.loads(request.expected_labels.read_bytes())
    labels.pop("source_imports")
    request = replace(
        request, expected_labels_sha256=_write(request.expected_labels, labels)
    )
    report = run_integration_acceptance(
        request, snapshot=snapshot, output_dir=tmp_path / "result"
    )
    assert report["status"] == "BLOCKED_INPUT"
    assert "canonical TaxID" in report["reason"]


def test_reference_mismatch_is_fail_not_an_invented_pass(tmp_path, acceptance_inputs):
    request, snapshot = acceptance_inputs
    labels = json.loads(request.expected_labels.read_bytes())
    labels["cases"][0]["expected"]["iuphar_class"] = "Enzyme"
    request = replace(
        request, expected_labels_sha256=_write(request.expected_labels, labels)
    )
    report = run_integration_acceptance(
        request, snapshot=snapshot, output_dir=tmp_path / "result"
    )
    assert report["status"] == "FAIL"
    assert report["reference_cases_accepted"] is False
    assert report["checks"]["reference_cases"] == "FAIL"
    assert report["checks"]["evidence_integrity"] == "NOT_RUN"
    assert report["checks"]["semantic_determinism"] == "NOT_RUN"


def test_missing_real_pipeline_proof_blocks_acceptance(tmp_path, acceptance_inputs):
    request, snapshot = acceptance_inputs
    report = run_integration_acceptance(
        replace(request, pipeline_proof=None),
        snapshot=snapshot,
        output_dir=tmp_path / "result",
    )
    assert report["status"] == "BLOCKED_INPUT"
    assert report["checks"]["pipeline_integration"] == "NOT_RUN"


def test_empty_canonical_stage0_is_not_replaced_by_fixture(tmp_path, acceptance_inputs):
    request, snapshot = acceptance_inputs
    document = json.loads(request.stage0_manifest.read_bytes())
    document["copies"] = []
    stage0_hash = _write(request.stage0_manifest, document)
    labels = json.loads(request.expected_labels.read_bytes())
    labels["stage0_manifest_sha256"] = stage0_hash
    request = replace(
        request, expected_labels_sha256=_write(request.expected_labels, labels)
    )
    report = run_integration_acceptance(
        request, snapshot=snapshot, output_dir=tmp_path / "result"
    )
    assert report["status"] == "BLOCKED_INPUT"
    assert report["checks"]["stage0_admission"] == "NOT_RUN"


def test_changed_pipeline_bytes_cannot_qualify(tmp_path, acceptance_inputs):
    request, snapshot = acceptance_inputs
    proof = json.loads(request.pipeline_proof.read_bytes())
    evidence = next(
        name for name in proof["artifact_sha256"] if name.endswith("/evidence.json")
    )
    (request.pipeline_proof.parent / evidence).write_bytes(b"changed")
    report = run_integration_acceptance(
        request, snapshot=snapshot, output_dir=tmp_path / "result"
    )
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


def _rewrite_stored_artifact(request, name, update):
    """Rehash the full bundle so tests exercise semantic binding, not stale hashes."""
    proof_path = request.pipeline_proof
    proof = json.loads(proof_path.read_bytes())
    relative = next(key for key in proof["artifact_sha256"] if key.endswith("/" + name))
    path = proof_path.parent / relative
    document = json.loads(path.read_bytes())
    update(document)
    proof["artifact_sha256"][relative] = _write(path, document)
    if name != "row-manifest.json":
        row_path = path.with_name("row-manifest.json")
        row = json.loads(row_path.read_bytes())
        row["artifact_sha256"][name] = sha256_file(path)
        proof["artifact_sha256"][row_path.relative_to(proof_path.parent).as_posix()] = (
            _write(row_path, row)
        )
    _write(proof_path, proof)
    report = json.loads(request.pipeline_report.read_bytes())
    report["observations"]["Target Classification"]["facts"][
        "evidence_manifest_sha256"
    ] = sha256_file(proof_path)
    _write(request.pipeline_report, report)


def test_actual_store_proof_requires_expected_execution_versions(acceptance_inputs):
    request, _ = acceptance_inputs
    with pytest.raises(ValueError, match="expected executed version identities"):
        verify_pipeline_proof(
            request.pipeline_proof,
            request.snapshot_manifest_sha256,
            request.pipeline_report,
        )


def test_arbitrary_empty_artifact_cannot_prove_a_pipeline_occurrence(
    tmp_path, acceptance_inputs
):
    request, _ = acceptance_inputs
    proof = json.loads(request.pipeline_proof.read_bytes())
    junk = request.pipeline_proof.parent / "junk.json"
    junk.write_bytes(b"[]\n")
    proof["artifact_sha256"] = {junk.name: sha256_file(junk)}
    _write(request.pipeline_proof, proof)
    with pytest.raises(ValueError, match="cover exactly"):
        verify_pipeline_proof(
            request.pipeline_proof,
            request.snapshot_manifest_sha256,
            request.pipeline_report,
            provenance=request.provenance,
        )


@pytest.mark.parametrize("count", [1000, True])
def test_claimed_row_count_must_equal_real_unique_store_rows(count, acceptance_inputs):
    request, _ = acceptance_inputs
    proof = json.loads(request.pipeline_proof.read_bytes())
    proof["row_count"] = count
    _write(request.pipeline_proof, proof)
    with pytest.raises(ValueError, match="row count"):
        verify_pipeline_proof(
            request.pipeline_proof,
            request.snapshot_manifest_sha256,
            request.pipeline_report,
            provenance=request.provenance,
        )


@pytest.mark.parametrize(
    "field,value", [("run_id", "another-run"), ("profile_sha256", "c" * 64)]
)
def test_rehashed_row_manifest_cannot_change_run_or_profile(
    field, value, acceptance_inputs
):
    request, _ = acceptance_inputs
    _rewrite_stored_artifact(
        request, "row-manifest.json", lambda row: row.update({field: value})
    )
    with pytest.raises(ValueError, match="identity or version mismatch"):
        verify_pipeline_proof(
            request.pipeline_proof,
            request.snapshot_manifest_sha256,
            request.pipeline_report,
            provenance=request.provenance,
        )


@pytest.mark.parametrize(
    "field,value", [("run_id", "another-run"), ("input_row_id", "another-row")]
)
def test_rehashed_evidence_cannot_change_run_or_row(field, value, acceptance_inputs):
    request, _ = acceptance_inputs
    _rewrite_stored_artifact(
        request, "evidence.json", lambda items: items[0].update({field: value})
    )
    with pytest.raises(ValueError, match="identity or version mismatch"):
        verify_pipeline_proof(
            request.pipeline_proof,
            request.snapshot_manifest_sha256,
            request.pipeline_report,
            provenance=request.provenance,
        )


def test_rehashed_classification_requires_resolvable_evidence(acceptance_inputs):
    request, _ = acceptance_inputs
    _rewrite_stored_artifact(
        request,
        "classification.json",
        lambda items: items[0].update(match_evidence_ids=["missing"]),
    )
    with pytest.raises(ValueError, match="unresolvable pipeline classification"):
        verify_pipeline_proof(
            request.pipeline_proof,
            request.snapshot_manifest_sha256,
            request.pipeline_report,
            provenance=request.provenance,
        )


def test_rehashed_classification_requires_same_executed_versions(acceptance_inputs):
    request, _ = acceptance_inputs
    _rewrite_stored_artifact(
        request,
        "classification.json",
        lambda items: items[0]["provenance"].update(rules_version="stale"),
    )
    with pytest.raises(ValueError, match="identity or version mismatch"):
        verify_pipeline_proof(
            request.pipeline_proof,
            request.snapshot_manifest_sha256,
            request.pipeline_report,
            provenance=request.provenance,
        )


def test_rehashed_classification_requires_the_complete_kernel_schema(acceptance_inputs):
    request, _ = acceptance_inputs
    _rewrite_stored_artifact(
        request, "classification.json", lambda items: items[0].pop("row_sha256")
    )
    with pytest.raises(ValueError, match="incomplete pipeline classification"):
        verify_pipeline_proof(
            request.pipeline_proof,
            request.snapshot_manifest_sha256,
            request.pipeline_report,
            provenance=request.provenance,
        )


def test_rehashed_direct_class_requires_actual_provider_payload(acceptance_inputs):
    request, _ = acceptance_inputs
    _rewrite_stored_artifact(
        request,
        "classification.json",
        lambda items: items[0].update(payload_sha256="0" * 64),
    )
    with pytest.raises(ValueError, match="direct pipeline class lacks"):
        verify_pipeline_proof(
            request.pipeline_proof,
            request.snapshot_manifest_sha256,
            request.pipeline_report,
            provenance=request.provenance,
        )


def test_store_proof_cannot_omit_one_of_six_outputs(acceptance_inputs):
    request, _ = acceptance_inputs
    proof = json.loads(request.pipeline_proof.read_bytes())
    relative = next(
        name for name in proof["artifact_sha256"] if name.endswith("/components.json")
    )
    proof["artifact_sha256"].pop(relative)
    _write(request.pipeline_proof, proof)
    with pytest.raises(ValueError, match="pipeline row output is missing"):
        verify_pipeline_proof(
            request.pipeline_proof,
            request.snapshot_manifest_sha256,
            request.pipeline_report,
            provenance=request.provenance,
        )


def test_successful_report_without_executed_classification_observation_is_insufficient(
    acceptance_inputs,
):
    request, _ = acceptance_inputs
    report = json.loads(request.pipeline_report.read_bytes())
    report.pop("observations")
    _write(request.pipeline_report, report)
    with pytest.raises(ValueError, match="proof JSON object required"):
        verify_pipeline_proof(
            request.pipeline_proof,
            request.snapshot_manifest_sha256,
            request.pipeline_report,
            provenance=request.provenance,
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("snapshot_manifest_sha256", "c" * 64),
        ("rules_version", "stale"),
        ("evidence_manifest_sha256", "c" * 64),
        ("row_count", 1000),
    ],
)
def test_report_must_bind_actual_snapshot_versions_rows_and_proof(
    field, value, acceptance_inputs
):
    request, _ = acceptance_inputs
    report = json.loads(request.pipeline_report.read_bytes())
    report["observations"]["Target Classification"]["facts"][field] = value
    _write(request.pipeline_report, report)
    with pytest.raises(ValueError, match="identity or version mismatch"):
        verify_pipeline_proof(
            request.pipeline_proof,
            request.snapshot_manifest_sha256,
            request.pipeline_report,
            provenance=request.provenance,
        )


def test_reference_specification_must_be_a_json_object(tmp_path):
    labels = tmp_path / "labels.json"
    raw = b"[]"
    labels.write_bytes(raw)
    request = IntegrationAcceptanceRequest(
        stage0_manifest=labels,
        expected_labels=labels,
        expected_labels_sha256=sha256_bytes(raw),
        snapshot_manifest_sha256="a" * 64,
        provenance=RunProvenance("snapshot", None, None, None, "t", "t"),
        run_id="blocked",
    )
    with pytest.raises(ValueError, match="JSON object"):
        _verified_labels(request)
