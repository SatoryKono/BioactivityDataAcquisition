"""Synthetic contract fixtures; these tests do not accept biological accuracy."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import url2pathname

import pytest

from bioetl.domain.entities.target_classification_boundary import (
    TargetClassificationArtifact,
    TargetClassificationInput,
)
from bioetl.infrastructure.adapters.iuphar import (
    IupharTargetClassificationAdapter,
    LocalTargetClassificationEvidenceStore,
    load_profile,
    load_snapshot_manifest,
    parse_target_payloads,
    validate_acceptance_receipt,
)
from bioetl.infrastructure.adapters.iuphar.snapshot_loader import (
    OUTPUT_NAMES,
    REQUIRED_ACCEPTANCE_CHECKS,
)
from tests.helpers.iuphar_snapshot import (
    synthetic_export_row,
    synthetic_snapshot_bundle,
    synthetic_reference_receipt,
)

pytestmark = pytest.mark.unit


def _write(root: Path, name: str, value: object) -> dict[str, str]:
    content = json.dumps(value, sort_keys=True).encode()
    (root / name).write_bytes(content)
    return {"path": name, "sha256": hashlib.sha256(content).hexdigest()}


def _receipt(snapshot_hash: str) -> dict[str, object]:
    return {
        "artifact": "bioetl_iuphar_acceptance",
        "schema_version": 1,
        "fixture_kind": "synthetic_contract_fixture",
        "scope": "offline_target_integration",
        "status": "PASS",
        "snapshot_manifest_sha256": snapshot_hash,
        "stage0_manifest_sha256": "a" * 64,
        "expected_labels_sha256": "b" * 64,
        "output_sha256": dict.fromkeys(OUTPUT_NAMES, "c" * 64),
        "checks": dict.fromkeys(REQUIRED_ACCEPTANCE_CHECKS, "PASS"),
        "reference_cases_accepted": True,
        "biological_accuracy_accepted": False,
        "run_id": "contract-run",
        "reviewer_reference": "synthetic-unit-test-expectations",
        "normalization_version": "bioetl-iuphar-input-v1",
        "rules_version": "plan-v1-r9",
        "classification_schema_version": "3.1.0",
        "matching_policy_version": "rf002-uniprot-roles-2026-11-23",
    }


def _profile(
    tmp_path: Path,
    *,
    accepted: bool = False,
    target_changes: dict[str, object] | None = None,
    **snapshot_changes: object,
):
    if accepted:
        root, bundle = synthetic_snapshot_bundle(
            tmp_path / "verified",
            rows=[synthetic_export_row(family_id="471", family_type="enzyme")],
        )
        acceptance = _write(
            root,
            "acceptance.json",
            synthetic_reference_receipt(
                bundle.snapshot_sha256, root=root / "reference-fixture"
            ),
        )
        document = json.loads((root / "profile.json").read_bytes())
        document["acceptance"] = acceptance
        reference = _write(root, "enrich-profile.json", document)
        return load_profile(root / reference["path"], reference["sha256"])
    targets = _write(
        tmp_path,
        "targets.json",
        [
            {
                "targetId": 1,
                "type": "enzyme",
                "familyIds": [],
                "taxonId": "9606",
                "uniprotIds": ["P12345"],
                "name": "known enzyme",
                "synonyms": ["enzyme alias"],
                **(target_changes or {}),
            },
        ],
    )
    snapshot = {
        "artifact": "bioetl_iuphar_snapshot",
        "schema_version": 1,
        "format": "gtopdb_target_payload_v1",
        "snapshot_id": "synthetic-snapshot",
        "provider_release": "2026.3.1",
        "retrieved_at": "2026-11-16T00:00:00Z",
        "targets": targets,
        "species_taxon_ids": ["9606"],
        "required_target_types": ["enzyme"],
        "expected_target_count": 1,
        "provider_versions": "совпали",
        "coverage_approval_reference": "synthetic-fixture-scope",
        "pagination_complete": True,
        **snapshot_changes,
    }
    snapshot_ref = _write(tmp_path, "snapshot.json", snapshot)
    acceptance = (
        _write(tmp_path, "acceptance.json", _receipt(snapshot_ref["sha256"]))
        if accepted
        else None
    )
    profile = {
        "artifact": "bioetl_iuphar_profile",
        "schema_version": 1,
        "snapshot": snapshot_ref,
        "acceptance": acceptance,
        "normalization_version": "bioetl-iuphar-input-v1",
        "rules_version": "plan-v1-r9",
        "classification_schema_version": "3.1.0",
        "matching_policy_version": "rf002-uniprot-roles-2026-11-23",
    }
    ref = _write(tmp_path, "profile.json", profile)
    return load_profile(
        tmp_path / ref["path"], ref["sha256"], require_acceptance=accepted
    )


def _business(**overrides: object) -> dict[str, object]:
    return {
        "target_id": "CHEMBL1",
        "target_type": "SINGLE PROTEIN",
        "taxonomy_id": 9606,
        "organism": "Homo sapiens",
        "component_accessions": '["P12345"]',
        "target_xref_uniprot_ids": "unknown",
        "target_protein_synonyms": "enzyme alias|unknown",
        "target_gene_synonyms": "unknown",
        "target_ec_numbers": "unknown",
        "pref_name": "known enzyme",
        **overrides,
    }


def _classify(adapter, **overrides):
    return adapter.classify_record(
        _business(**overrides),
        input_row_id="target:1",
        run_id="run-a",
        run_started_at="2026-11-16T00:01:00Z",
    )


def _profile_path(profile) -> Path:
    return Path(url2pathname(urlsplit(profile.profile_uri).path))


def test_direct_class_uses_payload_and_preserves_input(tmp_path):
    profile = _profile(tmp_path)
    adapter = IupharTargetClassificationAdapter(profile)
    data = _business()
    before = json.dumps(data, sort_keys=True)
    result = adapter.classify_record(
        data, input_row_id="target:1", run_id="run-a", run_started_at="fixed"
    )
    assert json.dumps(data, sort_keys=True) == before
    assert result.projection["iuphar_class"] == "Enzyme"
    assert result.projection["iuphar_target_id"] == "1"
    assert result.projection["iuphar_match_status"] == "matched"
    assert result.projection["target_class_profile_sha256"] == profile.profile_sha256
    output = json.loads(
        next(a.payload for a in result.artifacts if a.name == "classification.json")
    )[0]
    assert output["raw_fields"]["source_organism"] == "Homo sapiens"
    assert output["normalized_fields"]["organism"] == "9606"
    assert output["raw_fields"]["ec"] is None


def test_enrich_requires_accepted_references_and_publishable_snapshot(tmp_path):
    profile = _profile(tmp_path)
    path = _profile_path(profile)
    with pytest.raises(ValueError, match="source-verified snapshot schema 2"):
        load_profile(path, profile.profile_sha256)


def test_valid_reference_receipt_admits_enrich_contract_fixture(tmp_path):
    profile = _profile(tmp_path, accepted=True)
    assert profile.acceptance_sha256 is not None
    assert profile.snapshot.completeness.publishable


@pytest.mark.parametrize(
    "field",
    [
        "normalization_version",
        "rules_version",
        "classification_schema_version",
        "matching_policy_version",
    ],
)
def test_receipt_from_another_execution_version_cannot_admit_enrich(field):
    receipt = _receipt("a" * 64)
    receipt[field] = "unreviewed-version"
    with pytest.raises(ValueError, match="acceptance versions"):
        validate_acceptance_receipt(receipt, snapshot_manifest_sha256="a" * 64)


def test_pre_rf002_receipt_format_is_rejected_for_new_matching():
    """Real prior receipt shape (schema 2, no matching_policy_version) cannot admit."""
    receipt = _receipt("a" * 64)
    assert "matching_policy_version" in receipt
    del receipt["matching_policy_version"]
    # Prior enrich receipts carried these three pins only.
    assert {
        "normalization_version",
        "rules_version",
        "classification_schema_version",
    }.issubset(receipt)
    with pytest.raises(ValueError, match="acceptance versions"):
        validate_acceptance_receipt(receipt, snapshot_manifest_sha256="a" * 64)


def test_pre_rf002_profile_format_is_rejected_for_new_matching(tmp_path):
    from bioetl.infrastructure.adapters.iuphar._manifest import sha256
    from iuphar_target_class.stage0.io import canonical_json_bytes

    profile = _profile(tmp_path)
    path = _profile_path(profile)
    document = json.loads(path.read_bytes())
    del document["matching_policy_version"]
    path.write_bytes(canonical_json_bytes(document))
    with pytest.raises(
        ValueError, match="matching_policy_version|IUPHAR profile versions"
    ):
        load_profile(path, sha256(path.read_bytes()), require_acceptance=False)


def test_complete_version_unverified_snapshot_is_not_publishable(tmp_path):
    profile = _profile(
        tmp_path,
        provider_versions="недоступны",
        version_limitation_reference="fixture-limitation",
    )
    assert profile.snapshot.completeness.complete
    assert not profile.snapshot.completeness.publishable
    path = _profile_path(profile)
    with pytest.raises(ValueError, match="source-verified snapshot schema 2"):
        load_profile(path, profile.profile_sha256)


def test_incomplete_snapshot_does_not_rewrite_known_match_semantics(tmp_path):
    profile = _profile(tmp_path, pagination_complete=False)
    assert not profile.snapshot.completeness.complete
    assert (
        _classify(IupharTargetClassificationAdapter(profile)).projection[
            "iuphar_match_status"
        ]
        == "matched"
    )


def test_partial_type_proof_keeps_the_direct_class(tmp_path):
    profile = _profile(tmp_path, target_changes={"familyIds": [99999999]})
    result = _classify(IupharTargetClassificationAdapter(profile))
    assert result.projection["iuphar_class"] == "Enzyme"
    assert result.projection["iuphar_annotation_status"] == "partial"


def test_an_ec_input_does_not_replace_direct_iuphar(tmp_path):
    profile = _profile(
        tmp_path, target_changes={"type": "gpcr"}, required_target_types=["gpcr"]
    )
    result = _classify(
        IupharTargetClassificationAdapter(profile), target_ec_numbers="3.4.21.1"
    )
    assert result.projection["iuphar_class"] == "Receptor"
    # EC text alone does not supply the independent rule evidence needed for a
    # supported local class. The adapter must not manufacture a local override.
    assert result.projection["local_class"] is None


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"target_type": "PROTEIN COMPLEX"}, "unsupported_target_type"),
        ({"taxonomy_id": 10116, "organism": "Rattus norvegicus"}, "unsupported_taxon"),
        ({"taxonomy_id": True}, "invalid_taxonomy_id"),
        ({"organism": "Mus musculus"}, "taxonomy_name_conflict"),
        (
            {"taxonomy_id": None, "organism": "Mus musculus"},
            "missing_taxonomy_for_known_organism",
        ),
    ],
)
def test_unsupported_inputs_keep_identity_without_assigning_class(
    tmp_path, changes, reason
):
    result = _classify(IupharTargetClassificationAdapter(_profile(tmp_path)), **changes)
    assert result.input_row_id == "target:1"
    assert result.projection["iuphar_class"] is None
    assert result.diagnostic_codes == (reason,)


def test_chembl_id_does_not_become_explicit_iuphar_id(tmp_path):
    result = _classify(
        IupharTargetClassificationAdapter(_profile(tmp_path)),
        target_id="1",
        component_accessions="unknown",
        pref_name="unknown",
        target_protein_synonyms="unknown",
    )
    assert result.projection["iuphar_target_id"] is None
    assert result.projection["iuphar_class"] is None


def test_batch_results_follow_keys_and_duplicate_identity_is_rejected(tmp_path):
    adapter = IupharTargetClassificationAdapter(_profile(tmp_path))
    rows = (
        TargetClassificationInput("z", _business()),
        TargetClassificationInput("a", _business()),
    )
    batch = adapter.classify_batch(rows, run_id="run", run_started_at="fixed")
    assert tuple(result.input_row_id for result in batch.results) == ("z", "a")
    individual = adapter.classify_record(
        _business(), input_row_id="a", run_id="run", run_started_at="fixed"
    )
    assert batch.results[1].artifacts == individual.artifacts
    with pytest.raises(ValueError, match="duplicate"):
        adapter.classify_batch((rows[0], rows[0]), run_id="run", run_started_at="fixed")


def test_payload_tampering_and_duplicate_json_keys_are_rejected(tmp_path):
    profile = _profile(tmp_path)
    (tmp_path / "targets.json").write_bytes(b"[]")
    with pytest.raises(ValueError, match="digest"):
        load_snapshot_manifest(
            tmp_path / "snapshot.json", profile.snapshot.snapshot_manifest_sha256
        )
    with pytest.raises(ValueError, match="duplicate JSON key"):
        parse_target_payloads(b'[{"targetId":1,"targetId":2}]')


@pytest.mark.parametrize(
    "key,value",
    [
        ("status", "NOT_RUN"),
        ("reference_cases_accepted", False),
        ("snapshot_manifest_sha256", "d" * 64),
    ],
)
def test_receipt_cannot_admit_unexecuted_or_other_snapshot_cases(key, value):
    receipt = {**_receipt("a" * 64), key: value}
    with pytest.raises(ValueError):
        validate_acceptance_receipt(receipt, snapshot_manifest_sha256="a" * 64)


def test_evidence_retries_and_completion_check_expected_rows(tmp_path):
    profile = _profile(tmp_path)
    result = _classify(IupharTargetClassificationAdapter(profile))
    store = LocalTargetClassificationEvidenceStore(
        tmp_path / "evidence",
        snapshot_manifest_sha256=profile.snapshot.snapshot_manifest_sha256,
        profile_sha256=profile.profile_sha256,
    )
    reference = store.publish_result(result, run_id="run-a", batch_id="batch-1")
    assert store.publish_result(result, run_id="run-a", batch_id="batch-1") == reference
    with pytest.raises(ValueError, match="expected rows"):
        store.finalize_run(
            run_id="run-a", expected_row_ids=(result.input_row_id, "missing")
        )
    final = store.finalize_run(run_id="run-a", expected_row_ids=(result.input_row_id,))
    assert (
        store.finalize_run(run_id="run-a", expected_row_ids=(result.input_row_id,))
        == final
    )
    document = json.loads((tmp_path / "evidence/run-a/manifest.json").read_bytes())
    assert document["status"] == "complete" and document["row_count"] == 1
    assert len(document["artifact_sha256"]) == 7
    other = replace(result, input_row_id="new-row")
    with pytest.raises(ValueError, match="already finalized"):
        store.publish_result(other, run_id="run-a", batch_id="batch-1")


def test_evidence_conflicting_retry_is_not_overwritten(tmp_path):
    profile = _profile(tmp_path)
    result = _classify(IupharTargetClassificationAdapter(profile))
    store = LocalTargetClassificationEvidenceStore(
        tmp_path / "evidence",
        snapshot_manifest_sha256=profile.snapshot.snapshot_manifest_sha256,
        profile_sha256=profile.profile_sha256,
    )
    store.publish_result(result, run_id="run-a", batch_id="batch-1")
    changed = replace(
        result,
        artifacts=tuple(
            TargetClassificationArtifact(item.name, b'{"rows":7}')
            if item.name == "metrics.json"
            else item
            for item in result.artifacts
        ),
    )
    with pytest.raises(ValueError, match="conflicting"):
        store.publish_result(changed, run_id="run-a", batch_id="batch-1")


def test_evidence_cannot_be_published_under_another_run(tmp_path):
    profile = _profile(tmp_path)
    result = _classify(IupharTargetClassificationAdapter(profile))
    store = LocalTargetClassificationEvidenceStore(
        tmp_path / "evidence",
        snapshot_manifest_sha256=profile.snapshot.snapshot_manifest_sha256,
        profile_sha256=profile.profile_sha256,
    )
    with pytest.raises(ValueError, match="another run"):
        store.publish_result(result, run_id="run-b", batch_id="batch-1")


def test_profile_cannot_claim_an_unexecuted_normalization_version(tmp_path):
    profile = _profile(tmp_path)
    document = json.loads((tmp_path / "profile.json").read_bytes())
    document["normalization_version"] = "unexecuted-rules"
    reference = _write(tmp_path, "profile.json", document)
    with pytest.raises(ValueError, match="executing adapter"):
        load_profile(
            tmp_path / "profile.json", reference["sha256"], require_acceptance=False
        )
