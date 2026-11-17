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
    from bioetl.infrastructure.control_plane import _evidence_location_publish as atomic

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
