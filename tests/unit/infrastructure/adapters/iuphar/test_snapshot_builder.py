"""RF004 offline source contracts; all provider and review data are synthetic."""

from __future__ import annotations

import json

import pytest

from bioetl.infrastructure.adapters.iuphar import load_profile, load_snapshot_manifest
from bioetl.infrastructure.adapters.iuphar._manifest import sha256
from bioetl.infrastructure.adapters.iuphar.snapshot_payload import build_snapshot_bundle
from iuphar_target_class.models import RawTargetRow, RunProvenance
from iuphar_target_class.pipeline import classify_batch
from iuphar_target_class.stage0.io import canonical_json_bytes
from tests.helpers.iuphar_snapshot import (
    synthetic_export_row,
    synthetic_snapshot_bundle,
    synthetic_snapshot_sources,
    write_fixture_json,
)

pytestmark = pytest.mark.unit


def _run(loaded, **fields):
    snapshot = loaded.snapshot
    return classify_batch(
        (RawTargetRow("synthetic-row", fields, "protein"),),
        snapshot=snapshot,
        provenance=RunProvenance(
            snapshot.snapshot_id,
            "bioetl-iuphar-input-v1",
            "plan-v1-r9",
            "3.1.0",
            loaded.retrieved_at,
            "frozen",
        ),
        run_id="synthetic-run",
    ).rows[0]


def _edit_scope(coverage, update):
    document = json.loads(coverage.read_bytes())
    update(document["scope"])
    review_path = coverage.parent / document["review"]["path"]
    review = json.loads(review_path.read_bytes())
    review["scope_sha256"] = sha256(canonical_json_bytes(document["scope"]))
    document["review"]["sha256"] = write_fixture_json(review_path, review)
    return write_fixture_json(coverage, document)


def test_builder_is_deterministic_and_preserves_raw_receipt_bytes(tmp_path):
    root_a, first = synthetic_snapshot_bundle(tmp_path / "a")
    root_b, second = synthetic_snapshot_bundle(tmp_path / "b")
    assert first.files == second.files
    assert first.snapshot_sha256 == second.snapshot_sha256
    assert first.profile_sha256 == second.profile_sha256
    for name, content in first.files.items():
        assert (root_a / name).read_bytes() == (root_b / name).read_bytes() == content
    original = tmp_path / "a/sources/official-fixture.csv"
    assert (
        root_a / "sources/acquisition/official-fixture.csv"
    ).read_bytes() == original.read_bytes()


def test_scope_review_evidence_is_verified_and_copied(tmp_path):
    sources = synthetic_snapshot_sources(tmp_path / "sources")
    acquisition, acquisition_hash, coverage, _ = sources
    document = json.loads(coverage.read_bytes())
    review_path = coverage.parent / document["review"]["path"]
    evidence = coverage.parent / "eligibility.txt"
    evidence.write_bytes(b"Synthetic independently supplied eligibility proof")
    review = json.loads(review_path.read_bytes())
    review["evidence_references"] = [
        {"path": evidence.name, "sha256": sha256(evidence.read_bytes())}
    ]
    document["review"]["sha256"] = write_fixture_json(review_path, review)
    coverage_hash = write_fixture_json(coverage, document)
    bundle = build_snapshot_bundle(
        acquisition=acquisition,
        acquisition_sha256=acquisition_hash,
        coverage=coverage,
        coverage_sha256=coverage_hash,
        output_dir=tmp_path / "published",
    )
    assert bundle.files["sources/coverage/eligibility.txt"] == evidence.read_bytes()
    evidence.write_bytes(b"Changed after review")
    with pytest.raises(ValueError, match="digest mismatch"):
        build_snapshot_bundle(
            acquisition=acquisition,
            acquisition_sha256=acquisition_hash,
            coverage=coverage,
            coverage_sha256=coverage_hash,
            output_dir=tmp_path / "rejected",
        )
    assert not (tmp_path / "rejected").exists()


def test_builder_keeps_public_identity_with_three_distinct_species(tmp_path):
    root, bundle = synthetic_snapshot_bundle(
        tmp_path, species=("9606", "10116", "10090")
    )
    loaded = load_snapshot_manifest(root / "snapshot.json", bundle.snapshot_sha256)
    assert {row.target_id for row in loaded.snapshot.catalog} == {"1"}
    assert len(loaded.snapshot.catalog) == 3
    assert set(loaded.snapshot.species_annotations) == {
        ("1", "9606"),
        ("1", "10116"),
        ("1", "10090"),
    }
    assert (
        loaded.snapshot.admission_complete is True and loaded.snapshot.complete is True
    )
    for taxon, accession in [
        ("9606", "P12345"),
        ("10116", "Q12345"),
        ("10090", "Q99999"),
    ]:
        result = _run(loaded, target_id="1", uniprot=accession, organism=taxon)
        assert result.result.matched_target_id == "1"
        assert result.annotation is not None
        assert result.annotation.taxon == taxon
        assert result.result.iuphar_class == "Receptor"
        assert result.annotation.type_raw is None
        assert len(result.candidates) == len(
            {(item.target_id, item.match_method) for item in result.candidates}
        )


def test_same_provider_id_cannot_hide_cross_species_accession_conflict(tmp_path):
    root, bundle = synthetic_snapshot_bundle(tmp_path, species=("9606", "10116"))
    loaded = load_snapshot_manifest(root / "snapshot.json", bundle.snapshot_sha256)
    result = _run(loaded, target_id="1", uniprot="Q12345", organism="9606")
    assert result.result.match_status == "identity_conflict"
    assert result.result.iuphar_class is None


def test_species_ambiguous_explicit_id_requires_taxon_but_unique_accession_can_resolve(
    tmp_path,
):
    root, bundle = synthetic_snapshot_bundle(tmp_path, species=("9606", "10116"))
    loaded = load_snapshot_manifest(root / "snapshot.json", bundle.snapshot_sha256)
    assert _run(loaded, target_id="1").result.match_status == "insufficient_input"
    resolved = _run(loaded, target_id="1", uniprot="Q12345")
    assert resolved.result.match_status == "matched"
    assert resolved.annotation is not None
    assert resolved.annotation.taxon == "10116"


def test_csv_type_is_family_evidence_and_mixed_families_are_preserved(tmp_path):
    rows = [
        synthetic_export_row(target_id="498", family_id="78", family_type="vgic"),
        synthetic_export_row(target_id="498", family_id="471", family_type="enzyme"),
    ]
    root, bundle = synthetic_snapshot_bundle(tmp_path, rows=rows)
    loaded = load_snapshot_manifest(root / "snapshot.json", bundle.snapshot_sha256)
    row = _run(loaded, target_id="498", organism="9606")
    assert row.annotation is not None
    assert row.annotation.type_raw is None
    assert set(row.annotation.family_ids) == {"78", "471"}
    assert row.result.iuphar_class is None
    assert set(row.result.iuphar_class_candidates) == {"Ion Channel", "Enzyme"}
    audit = json.loads((root / "projection-audit.json").read_bytes())
    assert audit["raw_row_count"] == 2 and audit["species_variant_count"] == 1


def test_exclusions_keep_full_raw_accounting_without_false_absence(tmp_path):
    rows = [synthetic_export_row(), synthetic_export_row(target_id="2")]
    root, bundle = synthetic_snapshot_bundle(tmp_path, rows=rows, included=("1",))
    loaded = load_snapshot_manifest(root / "snapshot.json", bundle.snapshot_sha256)
    assert loaded.completeness.complete and loaded.completeness.publishable
    assert loaded.snapshot.admission_complete is True
    assert (
        loaded.snapshot.complete is False and not loaded.completeness.allows_not_found
    )
    assert (
        _run(loaded, target_id="2", organism="9606").result.match_status
        == "source_unavailable"
    )
    assert (
        _run(loaded, target_id="999", organism="9606").result.match_status
        == "source_unavailable"
    )
    audit = json.loads((root / "projection-audit.json").read_bytes())
    assert audit["raw_provider_target_count"] == 2
    assert audit["included_source_records"] == {"1": [1]}
    assert audit["excluded_targets"][0]["source_records"] == [2]


def test_missing_species_identity_is_unknown_not_assigned_to_human(tmp_path):
    row = synthetic_export_row()
    row.update({"Rat SwissProt": "", "Rat Entrez Gene": "", "RGD symbol": ""})
    root, bundle = synthetic_snapshot_bundle(
        tmp_path, rows=[row], species=("9606", "10116")
    )
    loaded = load_snapshot_manifest(root / "snapshot.json", bundle.snapshot_sha256)
    assert set(loaded.snapshot.species_annotations) == {("1", "9606")}
    assert not loaded.completeness.allows_not_found
    assert (
        _run(loaded, target_id="1", organism="10116").result.match_status
        == "source_unavailable"
    )
    assert (
        _run(loaded, target_id="99", organism="10116").result.match_status
        == "source_unavailable"
    )


def test_unverified_manifest_flags_cannot_override_source_coverage(tmp_path):
    root, bundle = synthetic_snapshot_bundle(
        tmp_path,
        rows=[synthetic_export_row(), synthetic_export_row(target_id="2")],
        included=("1",),
    )
    document = json.loads((root / "snapshot.json").read_bytes())
    document.update(
        complete=True,
        pagination_complete=True,
        allows_not_found=True,
        coverage_approval_reference="forged",
    )
    digest = write_fixture_json(root / "modified-snapshot.json", document)
    loaded = load_snapshot_manifest(root / "modified-snapshot.json", digest)
    assert not loaded.snapshot.complete and not loaded.completeness.allows_not_found


def test_acquisition_mutation_refuses_publication_before_output_creation(tmp_path):
    acquisition, acquisition_hash, coverage, coverage_hash = synthetic_snapshot_sources(
        tmp_path / "source"
    )
    (acquisition.parent / "official-fixture.csv").write_bytes(b"modified")
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="digest mismatch"):
        build_snapshot_bundle(
            acquisition=acquisition,
            acquisition_sha256=acquisition_hash,
            coverage=coverage,
            coverage_sha256=coverage_hash,
            output_dir=output,
        )
    assert not output.exists()


def test_reviewed_scope_must_account_for_every_raw_provider_target(tmp_path):
    acquisition, acquisition_hash, coverage, _ = synthetic_snapshot_sources(
        tmp_path / "source",
        rows=[synthetic_export_row(), synthetic_export_row(target_id="2")],
        included=("1",),
    )
    coverage_hash = _edit_scope(
        coverage, lambda scope: scope.update(excluded_targets=[])
    )
    with pytest.raises(ValueError, match="every raw provider identity"):
        build_snapshot_bundle(
            acquisition=acquisition,
            acquisition_sha256=acquisition_hash,
            coverage=coverage,
            coverage_sha256=coverage_hash,
            output_dir=tmp_path / "output",
        )


def test_scope_changes_require_new_independent_review_digest(tmp_path):
    acquisition, acquisition_hash, coverage, _ = synthetic_snapshot_sources(
        tmp_path / "source"
    )
    document = json.loads(coverage.read_bytes())
    document["scope"]["expected_variant_count"] = 1000
    coverage_hash = write_fixture_json(coverage, document)
    with pytest.raises(ValueError, match="another scope"):
        build_snapshot_bundle(
            acquisition=acquisition,
            acquisition_sha256=acquisition_hash,
            coverage=coverage,
            coverage_sha256=coverage_hash,
            output_dir=tmp_path / "output",
        )


def test_species_gene_id_can_anchor_without_a_swissprot_accession(tmp_path):
    row = synthetic_export_row()
    row["Human SwissProt"] = ""
    root, bundle = synthetic_snapshot_bundle(tmp_path, rows=[row])
    loaded = load_snapshot_manifest(root / "snapshot.json", bundle.snapshot_sha256)
    result = _run(loaded, gene_id="10", organism="9606")
    assert result.result.match_status == "matched"
    assert result.result.matched_target_id == "1"
    assert result.result.iuphar_class == "Receptor"


def test_inconsistent_identity_across_family_rows_is_not_silently_deduplicated(
    tmp_path,
):
    first = synthetic_export_row()
    second = synthetic_export_row(family_id="2")
    second["HGNC symbol"] = "DIFFERENT_GENE"
    with pytest.raises(ValueError, match="conflicting provider identity"):
        synthetic_snapshot_bundle(tmp_path, rows=[first, second])
    assert not (tmp_path / "bundle").exists()


def test_complex_target_needs_an_explicit_reviewed_exclusion(tmp_path):
    row = synthetic_export_row()
    row["Subunit id"] = "2|3"
    with pytest.raises(ValueError, match="subunit/complex target"):
        synthetic_snapshot_bundle(tmp_path, rows=[row])
    assert not (tmp_path / "bundle").exists()


def test_self_consistent_rehash_cannot_replace_the_source_derived_projection(tmp_path):
    root, bundle = synthetic_snapshot_bundle(tmp_path)
    rows = json.loads((root / "targets.json").read_bytes())
    rows[0]["geneId"] = "999"
    target_hash = write_fixture_json(root / "targets.json", rows)
    document = json.loads((root / "snapshot.json").read_bytes())
    document["targets"]["sha256"] = target_hash
    snapshot_hash = write_fixture_json(root / "snapshot.json", document)
    with pytest.raises(ValueError, match="verified official source projection"):
        load_snapshot_manifest(root / "snapshot.json", snapshot_hash)


def test_legacy_receipt_cannot_activate_a_new_source_verified_profile(tmp_path):
    root, bundle = synthetic_snapshot_bundle(tmp_path)
    receipt_hash = write_fixture_json(
        root / "legacy-receipt.json",
        {"artifact": "bioetl_iuphar_acceptance", "schema_version": 1},
    )
    document = json.loads((root / "profile.json").read_bytes())
    document["acceptance"] = {"path": "legacy-receipt.json", "sha256": receipt_hash}
    digest = write_fixture_json(root / "enrich-profile.json", document)
    with pytest.raises(ValueError, match="reference acceptance schema 2"):
        load_profile(root / "enrich-profile.json", digest)


def test_published_bundle_is_immutable_and_new_enrich_needs_receipt2(tmp_path):
    acquisition, acquisition_hash, coverage, coverage_hash = synthetic_snapshot_sources(
        tmp_path / "source"
    )
    output = tmp_path / "output"
    bundle = build_snapshot_bundle(
        acquisition=acquisition,
        acquisition_sha256=acquisition_hash,
        coverage=coverage,
        coverage_sha256=coverage_hash,
        output_dir=output,
    )
    before = {name: (output / name).read_bytes() for name in bundle.files}
    with pytest.raises(FileExistsError):
        build_snapshot_bundle(
            acquisition=acquisition,
            acquisition_sha256=acquisition_hash,
            coverage=coverage,
            coverage_sha256=coverage_hash,
            output_dir=output,
        )
    assert all(
        (output / name).read_bytes() == content for name, content in before.items()
    )
    with pytest.raises(ValueError, match="requires executed"):
        load_profile(output / "profile.json", bundle.profile_sha256)


def test_thin_cli_publishes_verified_offline_snapshot(tmp_path, capsys):
    from scripts.engineering.qa.iuphar_snapshot_build import main

    acquisition, acquisition_hash, coverage, coverage_hash = synthetic_snapshot_sources(
        tmp_path / "sources"
    )
    output = tmp_path / "bundle"
    assert (
        main(
            [
                "--acquisition",
                str(acquisition),
                "--acquisition-sha256",
                acquisition_hash,
                "--coverage",
                str(coverage),
                "--coverage-sha256",
                coverage_hash,
                "--output-dir",
                str(output),
            ]
        )
        == 0
    )
    loaded = load_profile(
        output / "profile.json",
        sha256((output / "profile.json").read_bytes()),
        require_acceptance=False,
    )
    assert loaded.snapshot.completeness.complete
    assert loaded.snapshot.manifest["annotation_capability"] == "family_only"
    assert "profile_sha256=" in capsys.readouterr().out
