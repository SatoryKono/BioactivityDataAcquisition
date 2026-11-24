"""The migration backup contains actual pinned bytes, never guessed paths."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from bioetl.infrastructure.storage.target_migration_dependencies import (
    _DependencyCollector,
    backup_target_dependencies,
    collect_target_dependencies,
    verify_target_dependencies,
)
from tests.helpers.iuphar_snapshot import (
    synthetic_reference_receipt,
    synthetic_snapshot_bundle,
    write_fixture_json,
)

pytestmark = pytest.mark.unit


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _config(path, profile=None, mode="off"):
    classification = {"mode": mode}
    if profile is not None:
        classification.update(
            snapshot_manifest=str(profile), snapshot_manifest_sha256=_sha(profile)
        )
    path.write_text(
        yaml.safe_dump({"pipeline": {"target_classification": classification}})
    )
    return path


def _refresh_reference(receipt, kind, path):
    reference = next(
        item for item in receipt["artifact_references"] if item["kind"] == kind
    )
    reference["sha256"] = _sha(path)
    receipt[kind + "_sha256"] = reference["sha256"]


@pytest.fixture
def deployment(tmp_path):
    """Fully linked synthetic bytes only; no scientific acceptance claim."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    output, bundle = synthetic_snapshot_bundle(workspace / "inputs")
    artifacts = output / "reference-fixture"
    receipt = synthetic_reference_receipt(bundle.snapshot_sha256, root=artifacts)
    raw = artifacts / "copied-source.bin"
    raw.write_bytes(b"preserved Stage0 source bytes\x00\xff")
    labels = artifacts / "expected_labels.json"
    write_fixture_json(
        labels,
        {
            "artifact": "bioetl_iuphar_reference_cases",
            "schema_version": 2,
            "cases": [{"source_references": [{"path": raw.name, "sha256": _sha(raw)}]}],
            "reference_matrix": {},
        },
    )
    _refresh_reference(receipt, "expected_labels", labels)
    stage0 = artifacts / "stage0_manifest.json"
    write_fixture_json(
        stage0,
        {
            "artifact": "stage0_manifest",
            "schema_version": 2,
            "artifact_sha256": {
                "copied-source.bin": _sha(raw),
                "cohort_manifest.json": _sha(artifacts / "cohort_manifest.json"),
                "conversion_ledger.json": _sha(artifacts / "conversion_ledger.json"),
            },
        },
    )
    _refresh_reference(receipt, "stage0_manifest", stage0)
    row_root = artifacts / "batches/batch/rows" / hashlib.sha256(b"row").hexdigest()
    row_root.mkdir(parents=True)
    output_names = tuple(receipt["output_sha256"])
    hashes = {
        name: write_fixture_json(
            row_root / name,
            {"fixture_kind": "synthetic_contract_fixture", "name": name},
        )
        for name in output_names
    }
    row_manifest = row_root / "row-manifest.json"
    write_fixture_json(
        row_manifest,
        {"input_row_id": "row", "run_id": "synthetic-run", "artifact_sha256": hashes},
    )
    proof = artifacts / "pipeline_proof.json"
    proof_hashes = {
        (row_root / name).relative_to(artifacts).as_posix(): digest
        for name, digest in hashes.items()
    }
    proof_hashes[row_manifest.relative_to(artifacts).as_posix()] = _sha(row_manifest)
    write_fixture_json(
        proof,
        {
            "artifact": "bioetl_iuphar_pipeline_evidence",
            "schema_version": 1,
            "artifact_sha256": proof_hashes,
            "pipeline_report": {
                "path": "pipeline_report.json",
                "sha256": _sha(artifacts / "pipeline_report.json"),
            },
        },
    )
    _refresh_reference(receipt, "pipeline_proof", proof)
    acceptance = output / "acceptance.json"
    write_fixture_json(acceptance, receipt)
    profile = json.loads((output / "profile.json").read_bytes())
    profile["acceptance"] = {"path": "acceptance.json", "sha256": _sha(acceptance)}
    selected = output / "enrich-profile.json"
    write_fixture_json(selected, profile)
    configs = (
        _config(workspace / "old.yaml"),
        _config(workspace / "new.yaml", selected, "enrich"),
    )
    return workspace, configs, output, row_manifest


def test_collects_complete_typed_closure_and_preserves_raw_bytes(deployment):
    workspace, configs, output, row_manifest = deployment
    dependencies = collect_target_dependencies(workspace=workspace, configs=configs)
    required = [
        *configs,
        output / "enrich-profile.json",
        output / "snapshot.json",
        output / "targets.json",
        output / "projection-audit.json",
        output / "sources/acquisition/acquisition.json",
        output / "sources/acquisition/official-fixture.csv",
        output / "sources/coverage/coverage.json",
        output / "sources/coverage/scope-review.json",
        output / "acceptance.json",
        row_manifest,
        row_manifest.parent / "classification.json",
        output / "reference-fixture/copied-source.bin",
        output / "reference-fixture/pipeline_report.json",
    ]
    for path in required:
        assert dependencies[path.relative_to(workspace).as_posix()] == _sha(path)
    assert (output / "profile.json").relative_to(
        workspace
    ).as_posix() not in dependencies
    backup = workspace / "backup"
    copied = backup_target_dependencies(
        workspace=workspace, dependencies=dependencies, destination=backup
    )
    assert len(copied) == len(dependencies)
    for name, digest in dependencies.items():
        assert (backup / name).read_bytes() == (workspace / name).read_bytes()
        assert copied["backup/" + name] == digest
    verify_target_dependencies(workspace, copied)
    assert (
        backup_target_dependencies(
            workspace=workspace, dependencies=dependencies, destination=backup
        )
        == copied
    )


def test_independent_expected_case_proofs_enter_backup_closure(tmp_path):
    proof = tmp_path / "independent-review.txt"
    proof.write_bytes(b"Synthetic frozen expected-case evidence")
    labels = tmp_path / "expected.json"
    write_fixture_json(
        labels,
        {
            "artifact": "bioetl_iuphar_reference_cases",
            "schema_version": 2,
            "cases": [
                {"source_references": [{"path": proof.name, "sha256": _sha(proof)}]}
            ],
            "reference_matrix": {},
        },
    )
    collector = _DependencyCollector(tmp_path)
    collector.document(labels, "expected_labels")
    assert collector.dependencies[proof.name] == _sha(proof)
    proof.write_bytes(b"Changed after independent review")
    with pytest.raises(ValueError, match="digest mismatch"):
        _DependencyCollector(tmp_path).document(labels, "expected_labels")


@pytest.mark.parametrize("kind", ["stage0_cohort", "stage0_evidence"])
def test_actual_stage0_material_roles_are_collected(deployment, kind):
    workspace, configs, output, _ = deployment
    extra = output / "additional-material.bin"
    extra.write_bytes(b"Synthetic copied Stage0 material")
    receipt_path = output / "acceptance.json"
    receipt = json.loads(receipt_path.read_bytes())
    receipt["artifact_references"].append(
        {"kind": kind, "immutable_uri": extra.as_uri(), "sha256": _sha(extra)}
    )
    digest = write_fixture_json(receipt_path, receipt)
    profile_path = output / "enrich-profile.json"
    profile = json.loads(profile_path.read_bytes())
    profile["acceptance"]["sha256"] = digest
    write_fixture_json(profile_path, profile)
    _config(configs[1], profile_path, "enrich")
    dependencies = collect_target_dependencies(workspace=workspace, configs=configs)
    assert dependencies[extra.relative_to(workspace).as_posix()] == _sha(extra)


def test_collects_both_old_shadow_and_new_enrich_profiles(deployment):
    workspace, configs, output, _ = deployment
    old, _ = synthetic_snapshot_bundle(workspace / "old-inputs")
    _config(configs[0], old / "profile.json", "shadow")
    dependencies = collect_target_dependencies(workspace=workspace, configs=configs)
    assert (old / "profile.json").relative_to(workspace).as_posix() in dependencies
    assert (output / "enrich-profile.json").relative_to(
        workspace
    ).as_posix() in dependencies


@pytest.mark.parametrize("mode", ["shadow", "enrich"])
def test_legacy_receipt_is_preserved_only_for_shadow(deployment, mode):
    workspace, configs, output, _ = deployment
    old, bundle = synthetic_snapshot_bundle(workspace / "old-inputs")
    receipt = synthetic_reference_receipt(
        bundle.snapshot_sha256, root=old / "legacy-artifacts"
    )
    receipt["schema_version"] = 1
    del receipt["artifact_references"]
    receipt_path = old / "legacy-acceptance.json"
    write_fixture_json(receipt_path, receipt)
    profile_path = old / "profile.json"
    profile = json.loads(profile_path.read_bytes())
    profile["acceptance"] = {"path": receipt_path.name, "sha256": _sha(receipt_path)}
    write_fixture_json(profile_path, profile)
    _config(configs[0], profile_path, mode)
    if mode == "enrich":
        with pytest.raises(ValueError, match="acceptance schema 2"):
            collect_target_dependencies(workspace=workspace, configs=configs)
        return
    dependencies = collect_target_dependencies(workspace=workspace, configs=configs)
    assert dependencies[receipt_path.relative_to(workspace).as_posix()] == _sha(
        receipt_path
    )
    assert (output / "enrich-profile.json").relative_to(
        workspace
    ).as_posix() in dependencies
    backup = workspace / "backup"
    copied = backup_target_dependencies(
        workspace=workspace, dependencies=dependencies, destination=backup
    )
    verify_target_dependencies(workspace, copied)
    assert (
        backup / receipt_path.relative_to(workspace)
    ).read_bytes() == receipt_path.read_bytes()


def test_off_or_absent_classification_requires_no_profile(tmp_path):
    config = tmp_path / "legacy.yaml"
    config.write_text("pipeline: {}\n")
    assert collect_target_dependencies(workspace=tmp_path, configs=(config,)) == {
        "legacy.yaml": _sha(config)
    }


@pytest.mark.parametrize(
    "relative",
    [
        "targets.json",
        "sources/acquisition/official-fixture.csv",
        "sources/coverage/scope-review.json",
        "reference-fixture/pipeline_report.json",
    ],
)
def test_tamper_or_missing_dependencies_refuses_before_backup(deployment, relative):
    workspace, configs, output, _ = deployment
    dependencies = collect_target_dependencies(workspace=workspace, configs=configs)
    source = output / relative
    source.write_bytes(source.read_bytes() + b"changed")
    destination = workspace / "uncreated-backup"
    with pytest.raises(ValueError, match="digest mismatch"):
        backup_target_dependencies(
            workspace=workspace, dependencies=dependencies, destination=destination
        )
    assert not destination.exists()
    source.unlink()
    with pytest.raises(FileNotFoundError):
        verify_target_dependencies(workspace, dependencies)


def test_pipeline_row_outputs_are_followed_even_if_top_map_omits_them(deployment):
    workspace, configs, output, row_manifest = deployment
    proof = output / "reference-fixture/pipeline_proof.json"
    document = json.loads(proof.read_bytes())
    document["artifact_sha256"] = {
        row_manifest.relative_to(proof.parent).as_posix(): _sha(row_manifest)
    }
    write_fixture_json(proof, document)
    _rebind_profile(output, configs[1], "pipeline_proof", proof)
    dependencies = collect_target_dependencies(workspace=workspace, configs=configs)
    assert all(
        (row_manifest.parent / name).relative_to(workspace).as_posix() in dependencies
        for name in json.loads(row_manifest.read_bytes())["artifact_sha256"]
    )


def test_missing_pipeline_row_output_is_never_omitted(deployment):
    workspace, configs, _, row_manifest = deployment
    (row_manifest.parent / "metrics.json").unlink()
    with pytest.raises(FileNotFoundError):
        collect_target_dependencies(workspace=workspace, configs=configs)


def test_incomplete_typed_pipeline_row_manifest_is_refused(deployment):
    workspace, configs, output, row_manifest = deployment
    document = json.loads(row_manifest.read_bytes())
    del document["artifact_sha256"]["metrics.json"]
    write_fixture_json(row_manifest, document)
    proof = output / "reference-fixture/pipeline_proof.json"
    payload = json.loads(proof.read_bytes())
    payload["artifact_sha256"][row_manifest.relative_to(proof.parent).as_posix()] = (
        _sha(row_manifest)
    )
    write_fixture_json(proof, payload)
    _rebind_profile(output, configs[1], "pipeline_proof", proof)
    with pytest.raises(ValueError, match="all six"):
        collect_target_dependencies(workspace=workspace, configs=configs)


def _rebind_profile(output, config, kind, path):
    receipt_path = output / "acceptance.json"
    receipt = json.loads(receipt_path.read_bytes())
    _refresh_reference(receipt, kind, path)
    write_fixture_json(receipt_path, receipt)
    profile_path = output / "enrich-profile.json"
    profile = json.loads(profile_path.read_bytes())
    profile["acceptance"]["sha256"] = _sha(receipt_path)
    write_fixture_json(profile_path, profile)
    _config(config, profile_path, "enrich")


@pytest.mark.parametrize("name", [".env", ".env.example", "archive/x.env", "x.ENV"])
def test_environment_paths_are_rejected_without_creating_env_files(tmp_path, name):
    with pytest.raises(ValueError, match="environment files"):
        verify_target_dependencies(tmp_path, {name: "a" * 64})
    assert not (tmp_path / name).exists()


@pytest.mark.parametrize(
    "reference",
    ["https://example.invalid/proof.json", "file://remote-share/proof.json"],
)
def test_unknown_network_uri_is_refused(tmp_path, reference):
    with pytest.raises(ValueError, match="local file URI"):
        verify_target_dependencies(tmp_path, {reference: "a" * 64})


def test_external_file_uri_is_refused_before_read(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    external = tmp_path / "outside.bin"
    external.write_bytes(b"outside approved migration root")
    with pytest.raises(ValueError, match="escapes"):
        verify_target_dependencies(workspace, {external.as_uri(): _sha(external)})


@pytest.mark.parametrize("method", ["is_symlink", "is_junction"])
def test_redirected_ancestor_is_refused(tmp_path, monkeypatch, method):
    redirected = tmp_path / "redirected"
    monkeypatch.setattr(Path, method, lambda self: self == redirected)
    with pytest.raises(ValueError, match="symlink/junction"):
        verify_target_dependencies(tmp_path, {"redirected/artifact.json": "a" * 64})


def test_changed_existing_backup_is_not_overwritten(deployment):
    workspace, configs, _, _ = deployment
    dependencies = collect_target_dependencies(workspace=workspace, configs=configs)
    target = workspace / "backup"
    backup_target_dependencies(
        workspace=workspace, dependencies=dependencies, destination=target
    )
    existing = target / "old.yaml"
    existing.write_bytes(b"preserve conflicting backup")
    with pytest.raises(ValueError, match="already contains different bytes"):
        backup_target_dependencies(
            workspace=workspace, dependencies=dependencies, destination=target
        )
    assert existing.read_bytes() == b"preserve conflicting backup"


def test_scope_review_includes_only_declared_evidence_and_verifies_bytes(tmp_path):
    evidence = tmp_path / "eligibility-proof.json"
    evidence.write_bytes(b'{"verified_source_fact": "synthetic fixture only"}\n')
    unrelated = tmp_path / "unrelated.json"
    unrelated.write_bytes(b"do not crawl this directory")
    review = tmp_path / "review.json"
    write_fixture_json(
        review,
        {
            "artifact": "bioetl_iuphar_scope_review",
            "schema_version": 1,
            "evidence_references": [
                {"path": "eligibility-proof.json", "sha256": _sha(evidence)}
            ],
        },
    )
    collector = _DependencyCollector(tmp_path)
    collector.document(review, "scope_review", _sha(review))
    assert set(collector.dependencies) == {"review.json", "eligibility-proof.json"}
    evidence.write_bytes(b"replaced eligibility")
    with pytest.raises(ValueError, match="digest mismatch"):
        _DependencyCollector(tmp_path).document(review, "scope_review", _sha(review))


def test_nested_scope_review_resolves_evidence_from_coverage_directory(tmp_path):
    """Evidence paths match snapshot_evidence._review (coverage root, not review dir)."""
    coverage_dir = tmp_path / "sources" / "coverage"
    reviews = coverage_dir / "reviews"
    reviews.mkdir(parents=True)
    evidence = coverage_dir / "eligibility.txt"
    evidence.write_text("reviewed eligibility\n", encoding="utf-8")
    review = reviews / "review.json"
    write_fixture_json(
        review,
        {
            "artifact": "bioetl_iuphar_scope_review",
            "schema_version": 1,
            "evidence_references": [
                {"path": "eligibility.txt", "sha256": _sha(evidence)}
            ],
        },
    )
    coverage = coverage_dir / "coverage.json"
    write_fixture_json(
        coverage,
        {
            "artifact": "bioetl_iuphar_coverage",
            "schema_version": 1,
            "review": {
                "path": "reviews/review.json",
                "sha256": _sha(review),
            },
        },
    )
    collector = _DependencyCollector(tmp_path)
    collector.document(coverage, "coverage", _sha(coverage))
    assert set(collector.dependencies) == {
        "sources/coverage/coverage.json",
        "sources/coverage/reviews/review.json",
        "sources/coverage/eligibility.txt",
    }


def test_validated_fk_restoration_bytes_enter_the_backup_closure(tmp_path):
    source = tmp_path / "recovery/CHEMBL2237.json"
    source.parent.mkdir()
    source.write_bytes(b'{"target_id":"CHEMBL2237"}\n')
    candidate = tmp_path / "candidate/gold/part.parquet"
    candidate.parent.mkdir(parents=True)
    candidate.write_bytes(b"pinned-candidate-bytes")
    manifest = tmp_path / "fk-restoration.json"
    write_fixture_json(
        manifest,
        {
            "artifact": "bioetl_target_fk_restoration",
            "schema_version": 1,
            "status": "validated_candidate",
            "sources": [
                {
                    "path": "recovery/CHEMBL2237.json",
                    "sha256": _sha(source),
                }
            ],
            "candidate_files": [
                {
                    "path": "candidate/gold/part.parquet",
                    "sha256": _sha(candidate),
                }
            ],
        },
    )
    dependencies = collect_target_dependencies(
        workspace=tmp_path, configs=(), restoration_manifest=manifest
    )
    assert dependencies["recovery/CHEMBL2237.json"] == _sha(source)
    assert dependencies["candidate/gold/part.parquet"] == _sha(candidate)
    backup = tmp_path / "backup"
    copied = backup_target_dependencies(
        workspace=tmp_path, dependencies=dependencies, destination=backup
    )
    assert (backup / "recovery/CHEMBL2237.json").read_bytes() == source.read_bytes()
    assert copied["backup/candidate/gold/part.parquet"] == _sha(candidate)
    blocked = tmp_path / "blocked.json"
    write_fixture_json(
        blocked,
        {
            "artifact": "bioetl_target_fk_restoration",
            "schema_version": 1,
            "status": "blocked",
            "sources": [{"path": "recovery/CHEMBL2237.json", "sha256": _sha(source)}],
            "candidate_files": [
                {"path": "candidate/gold/part.parquet", "sha256": _sha(candidate)}
            ],
        },
    )
    with pytest.raises(ValueError, match="blocked target FK restoration"):
        collect_target_dependencies(
            workspace=tmp_path, configs=(), restoration_manifest=blocked
        )
