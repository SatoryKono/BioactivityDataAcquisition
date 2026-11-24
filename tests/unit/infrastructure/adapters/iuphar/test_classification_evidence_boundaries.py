"""Public evidence contracts with synthetic, source-verified provider fixtures."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from bioetl.domain import ports
from bioetl.domain.ports import (
    TargetClassificationEvidencePort,
    TargetClassificationPort,
)
from bioetl.domain.entities.target_classification_boundary import (
    TargetClassificationArtifact,
    TargetClassificationInput,
)
from bioetl.infrastructure.adapters.iuphar import (
    IupharTargetClassificationAdapter,
    LocalTargetClassificationEvidenceStore,
    load_profile,
)
from iuphar_target_class.stage0.io import canonical_json_bytes
from tests.helpers.iuphar_snapshot import synthetic_snapshot_bundle

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "taxon,organism,reason",
    [
        (9606, "Homo sapiens", None),
        (10116, "Rattus norvegicus", "unsupported_taxon"),
        (9606, "Mus musculus", "taxonomy_name_conflict"),
    ],
)
def test_canonical_cohort_roundtrip_uses_runtime_eligibility(
    tmp_path,
    classification_boundary,
    taxon,
    organism,
    reason,
):
    import pyarrow as pa
    from bioetl.infrastructure.adapters.iuphar.cohort_projection import (
        ARROW_SOURCE_FORMAT,
        NORMALIZED_TARGET_SCHEMA,
        CohortExportRequest,
        export_canonical_cohort,
    )
    from iuphar_target_class.integration_acceptance import _execution_bindings
    from iuphar_target_class.models import RunProvenance
    from iuphar_target_class.pipeline import classify_batch
    from iuphar_target_class.pipeline_acceptance import AdmittedCohort
    from iuphar_target_class.pipeline_io import read_bioetl_target_kernel_csv_v1
    from iuphar_target_class.pipeline_proof import verify_stored_pipeline_proof
    from iuphar_target_class.stage0.io import sha256_file

    classifier, store, _, business, root = classification_boundary
    business.update(taxonomy_id=taxon, organism=organism, pref_name="Fixture")
    source = tmp_path / "source.arrow"
    table = pa.Table.from_pylist([business])
    with pa.ipc.new_stream(source, table.schema) as writer:
        writer.write_table(table)
    exported = export_canonical_cohort(
        CohortExportRequest(
            source,
            sha256_file(source),
            ARROW_SOURCE_FORMAT,
            NORMALIZED_TARGET_SCHEMA,
            "synthetic-mapping",
            "test",
        ),
        output_dir=tmp_path / "cohort",
    )
    rows = read_bioetl_target_kernel_csv_v1(
        exported.canonical_path.read_bytes(),
        source_path="source.arrow",
        target_kind="protein",
    )
    profile = classifier._profile
    store = LocalTargetClassificationEvidenceStore(
        root,
        mode="shadow",
        snapshot_manifest_sha256=classifier.snapshot_manifest_sha256,
        profile_sha256=classifier.profile_sha256,
        versions={
            "normalization_version": profile.normalization_version,
            "rules_version": profile.rules_version,
            "classification_schema_version": profile.classification_schema_version,
            "matching_policy_version": profile.matching_policy_version,
        },
    )
    provenance = RunProvenance(
        classifier.snapshot_id,
        profile.normalization_version,
        profile.rules_version,
        profile.classification_schema_version,
        profile.snapshot.retrieved_at,
        "fixed",
        matching_policy_version=profile.matching_policy_version,
    )
    batch = classify_batch(
        rows,
        snapshot=profile.snapshot.snapshot,
        provenance=provenance,
        run_id="reference",
    )
    cohort = AdmittedCohort("a" * 64, (), rows)
    with pytest.raises(ValueError, match="profile species scope"):
        _execution_bindings(cohort, batch)
    bindings = _execution_bindings(cohort, batch, profile.snapshot.species_taxon_ids)
    result = classifier.classify_record(
        business,
        input_row_id=rows[0].input_row_id,
        run_id="run-a",
        run_started_at="fixed",
    )
    if reason:
        assert result.diagnostic_codes == (reason,)
    else:
        assert "unsupported_taxon" not in result.diagnostic_codes
    store.publish_result(result, run_id="run-a", batch_id="batch-1")
    store.finalize_run(run_id="run-a", expected_row_ids=(rows[0].input_row_id,))
    proof = root / "run-a/manifest.json"
    document = json.loads(proof.read_bytes())
    report = tmp_path / "report.json"
    facts = {
        key: document[key]
        for key in (
            "run_id",
            "mode",
            "snapshot_manifest_sha256",
            "profile_sha256",
            "normalization_version",
            "rules_version",
            "classification_schema_version",
            "matching_policy_version",
            "row_count",
        )
    }
    facts.update(
        evidence_manifest_uri=proof.as_uri(),
        evidence_manifest_sha256=sha256_file(proof),
    )
    report.write_bytes(
        canonical_json_bytes(
            {
                "schema_version": "pipeline_run_report_v2",
                "identity": {
                    "pipeline": "chembl_target",
                    "run_id": "run-a",
                    "status": "success",
                },
                "observations": {
                    "Target Classification": {
                        "verdict": "OK",
                        "reason": "verified_target_classification_evidence",
                        "facts": facts,
                    }
                },
            }
        )
    )
    assert verify_stored_pipeline_proof(
        proof,
        classifier.snapshot_manifest_sha256,
        report,
        provenance,
        expected_execution=bindings,
    ) == sha256_file(proof)
    altered_input = dict(bindings[0].raw_fields)
    altered_input["target_id"] = "another-target"
    with pytest.raises(ValueError, match="input differs"):
        verify_stored_pipeline_proof(
            proof,
            classifier.snapshot_manifest_sha256,
            report,
            provenance,
            expected_execution=(replace(bindings[0], raw_fields=altered_input),),
        )
    changed = dict(bindings[0].semantic)
    changed["reason"] = "wrong-policy-result"
    with pytest.raises(ValueError, match="eligibility differs"):
        verify_stored_pipeline_proof(
            proof,
            classifier.snapshot_manifest_sha256,
            report,
            provenance,
            expected_execution=(replace(bindings[0], semantic=changed),),
        )


@pytest.fixture
def classification_boundary(tmp_path):
    root, bundle = synthetic_snapshot_bundle(tmp_path / "synthetic-provider")
    profile = load_profile(
        root / "profile.json", bundle.profile_sha256, require_acceptance=False
    )
    classifier = IupharTargetClassificationAdapter(profile)
    evidence_root = tmp_path / "evidence"
    store = LocalTargetClassificationEvidenceStore(
        evidence_root,
        snapshot_manifest_sha256=classifier.snapshot_manifest_sha256,
        profile_sha256=classifier.profile_sha256,
    )
    business = {
        "target_id": "CHEMBL1",
        "target_type": "SINGLE PROTEIN",
        "taxonomy_id": 9606,
        "organism": "Homo sapiens",
        "component_accessions": '["P12345"]',
    }
    result = classifier.classify_record(
        business,
        input_row_id="target:1",
        run_id="run-a",
        run_started_at="2026-11-16T00:01:00Z",
    )
    return classifier, store, result, business, evidence_root


def test_public_ports_support_real_classification_and_evidence_roundtrip(
    classification_boundary,
):
    classifier, store, single, business, root = classification_boundary
    assert ports.TargetClassificationPort is TargetClassificationPort
    assert ports.TargetClassificationEvidencePort is TargetClassificationEvidencePort
    assert {"TargetClassificationPort", "TargetClassificationEvidencePort"} <= set(
        dir(ports)
    )
    assert isinstance(classifier, TargetClassificationPort)
    assert isinstance(store, TargetClassificationEvidencePort)
    assert not isinstance(store, TargetClassificationPort)
    assert not isinstance(classifier, TargetClassificationEvidencePort)
    batch = classifier.classify_batch(
        (TargetClassificationInput("target:1", business),),
        run_id="run-a",
        run_started_at="2026-11-16T00:01:00Z",
    )
    assert batch.results[0].projection == single.projection
    reference = store.publish_result(single, run_id="run-a", batch_id="batch-1")
    assert reference.sha256
    completed = store.finalize_run(run_id="run-a", expected_row_ids=("target:1",))
    document = json.loads((root / "run-a/manifest.json").read_bytes())
    assert document["status"] == "complete"
    assert document["input_row_ids"] == ["target:1"]
    assert document["profile_sha256"] == classifier.profile_sha256
    assert document["snapshot_manifest_sha256"] == classifier.snapshot_manifest_sha256
    assert completed.uri == (root / "run-a/manifest.json").as_uri()


@pytest.mark.parametrize(
    ("artifact_name", "value", "message"),
    [
        ("classification.json", {}, "exactly one"),
        ("classification.json", [], "exactly one"),
        ("classification.json", [None], "exactly one"),
        (
            "classification.json",
            [{"input_row_id": "another-row"}],
            "another source row",
        ),
        ("evidence.json", {}, "JSON array"),
        ("evidence.json", [None], "invalid classification evidence record"),
        (
            "evidence.json",
            [{"run_id": "run-a", "input_row_id": "target:1"}],
            "evidence identity",
        ),
        (
            "evidence.json",
            [
                {"run_id": "run-a", "input_row_id": "target:1", "evidence_id": "e"},
                {"run_id": "run-a", "input_row_id": "target:1", "evidence_id": "e"},
            ],
            "evidence identity",
        ),
        (
            "classification.json",
            [{"input_row_id": "target:1", "match_evidence_ids": ["missing"]}],
            "unresolvable",
        ),
        (
            "classification.json",
            [{"input_row_id": "target:1", "local_evidence_ids": "not-a-list"}],
            "unresolvable",
        ),
    ],
)
def test_store_refuses_malformed_row_evidence_before_publishing(
    classification_boundary, artifact_name, value, message
):
    _, store, result, _, root = classification_boundary
    changed = replace(
        result,
        artifacts=tuple(
            TargetClassificationArtifact(item.name, canonical_json_bytes(value))
            if item.name == artifact_name
            else item
            for item in result.artifacts
        ),
    )
    with pytest.raises(ValueError, match=message):
        store.publish_result(changed, run_id="run-a", batch_id="batch-1")
    assert not root.exists()


def test_store_refuses_a_projection_from_another_profile_before_publishing(
    classification_boundary,
):
    _, store, result, _, root = classification_boundary
    changed = replace(
        result,
        projection={**result.projection, "target_class_profile_sha256": "0" * 64},
    )
    with pytest.raises(ValueError, match="another profile"):
        store.publish_result(changed, run_id="run-a", batch_id="batch-1")
    assert not root.exists()


def test_interrupted_artifact_publication_leaves_no_final_partial_file(
    classification_boundary, monkeypatch
):
    from bioetl.infrastructure.control_plane import evidence_location_publish as atomic

    _, store, result, _, root = classification_boundary
    publish = atomic._publish_new_file_exclusive
    seen = []

    def interrupted(source, target):
        seen.append(target)
        assert source.read_bytes()
        assert not target.exists()
        raise OSError("interrupted publication")

    with monkeypatch.context() as patch:
        patch.setattr(atomic, "_publish_new_file_exclusive", interrupted)
        with pytest.raises(OSError, match="interrupted publication"):
            store.publish_result(result, run_id="run-a", batch_id="batch-1")
    assert seen and all(not path.exists() for path in seen)
    monkeypatch.setattr(atomic, "_publish_new_file_exclusive", publish)
    store.publish_result(result, run_id="run-a", batch_id="batch-1")
    assert list(root.rglob("row-manifest.json"))
