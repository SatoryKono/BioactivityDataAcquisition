"""Role-separated admission verifies original, converted and evidence bytes."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import replace
from pathlib import Path

import pyarrow as pa
import pytest

from bioetl.infrastructure.adapters.iuphar._input_projection import (
    project_target_fields,
)
from bioetl.infrastructure.adapters.iuphar.cohort_builder import (
    ARROW_SOURCE_FORMAT,
    CSV_SOURCE_FORMAT,
    NORMALIZED_TARGET_SCHEMA,
    CohortExportRequest,
    export_canonical_cohort,
)
from iuphar_target_class.pipeline_acceptance import (
    SourceImport,
    VolumePlan,
    load_admitted_cohort,
)
from iuphar_target_class.pipeline_io import (
    BIOETL_TARGET_KERNEL_CSV_V1,
    read_bioetl_target_kernel_csv_v1,
)
from iuphar_target_class.stage0.io import sha256_file
from iuphar_target_class.stage0.models import ProvenanceClaim
from iuphar_target_class.stage0.v2 import (
    Stage0MaterialV2,
    Stage0V2Request,
    publish_stage0_v2,
    verify_stage0_v2,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "source", [".env", ".ENV.local", "config.env", "evidence/secret.EnV"]
)
def test_material_rejects_environment_identities_without_opening_files(source: str):
    with pytest.raises(ValueError, match="environment files"):
        Stage0MaterialV2(source, "a" * 64, "evidence", "text/plain")


def _source(tmp_path: Path, **updates: str) -> tuple[Path, dict[str, str]]:
    row = {
        "target_id": "CHEMBL1",
        "target_type": "SINGLE PROTEIN",
        "taxonomy_id": "9606",
        "pref_name": "Fixture",
        "organism": "Homo sapiens",
        "component_accessions": '["P12345"]',
        "target_protein_synonyms": "alias1|alias2",
        "target_ec_numbers": "1.1.1.1",
        **updates,
    }
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(row), lineterminator="\n")
    writer.writeheader()
    writer.writerow(row)
    source = tmp_path / "normalized.csv"
    source.write_bytes(stream.getvalue().encode())
    return source, row


def _export(tmp_path: Path, **updates: str):
    source, row = _source(tmp_path, **updates)
    request = CohortExportRequest(
        source,
        sha256_file(source),
        CSV_SOURCE_FORMAT,
        NORMALIZED_TARGET_SCHEMA,
        "synthetic technical mapping only",
        "unit-test",
    )
    return (
        export_canonical_cohort(request, output_dir=tmp_path / "export"),
        request,
        row,
    )


def _bundle(tmp_path: Path, **updates: str):
    export, _, _ = _export(tmp_path, **updates)
    proof = tmp_path / "review.txt"
    proof.write_bytes(b"synthetic engineering evidence, not biological review")
    materials = (
        Stage0MaterialV2(
            "export/cohort.csv",
            export.canonical_sha256,
            "cohort",
            BIOETL_TARGET_KERNEL_CSV_V1,
            "protein",
            "export/conversion-ledger.json",
        ),
        Stage0MaterialV2(
            "export/raw-source.bin", export.raw_sha256, "evidence", CSV_SOURCE_FORMAT
        ),
        Stage0MaterialV2(
            "export/conversion-ledger.json",
            export.conversion_ledger_sha256,
            "evidence",
            "bioetl_target_cohort_conversion_v1",
        ),
        Stage0MaterialV2("review.txt", sha256_file(proof), "evidence", "text/plain"),
    )
    request = Stage0V2Request(
        "synthetic-cohort",
        "synthetic software test scope",
        "unit-test",
        materials,
        (
            ProvenanceClaim(
                "target_all",
                "review.txt",
                sha256_file(proof),
                "synthetic test",
                "test fixture",
            ),
        ),
    )
    manifest = publish_stage0_v2(
        request, repo_root=tmp_path, output_dir=tmp_path / "stage0"
    )
    plan = VolumePlan(
        sha256_file(manifest),
        ("export/cohort.csv",),
        1,
        "synthetic software test scope",
        "unit-test",
        (SourceImport("export/cohort.csv", BIOETL_TARGET_KERNEL_CSV_V1, "protein"),),
    )
    return manifest, plan, export


def test_large_business_field_survives_export_stage0_and_canonical_import(
    tmp_path: Path,
):
    original_limit = csv.field_size_limit()
    large_value = 'large,quoted"value\n' * 12000
    manifest, plan, export = _bundle(tmp_path, target_protein_synonyms=large_value)
    frozen = verify_stage0_v2(
        manifest, plan.manifest_sha256, plan.selected_source_paths
    )
    cohort = load_admitted_cohort(manifest, plan)
    business = json.loads(cohort.rows[0].fields["source_business_data"])
    assert business["target_protein_synonyms"] == large_value
    assert export.raw_sha256 == sha256_file(tmp_path / "normalized.csv")
    assert dict(frozen.cohort_digests)["export/cohort.csv"] == export.canonical_sha256
    assert len(cohort.rows) == 1
    assert csv.field_size_limit() == original_limit


def test_v2_selects_all_cohort_and_keeps_bound_evidence_separate(tmp_path: Path):
    manifest, plan, _ = _bundle(tmp_path)
    cohort = load_admitted_cohort(manifest, plan)
    assert len(cohort.rows) == 1
    assert cohort.rows[0].input_row_id == "chembl.target:CHEMBL1"
    assert len(cohort.source_digests) == 1 and len(cohort.evidence_digests) == 3
    assert cohort.schema_version == 2
    assert len(cohort.cohort_manifest_sha256) == 64
    assert len(cohort.conversion_ledger_sha256) == 64
    document = json.loads(manifest.read_bytes())
    assert document["provenance_bindings"][0]["source_role"] == "evidence"
    assert document["biological_accuracy_accepted"] is False


def test_tampered_unselected_evidence_fails_closed(tmp_path: Path):
    manifest, plan, _ = _bundle(tmp_path)
    document = json.loads(manifest.read_bytes())
    proof = next(
        row for row in document["copies"] if row["source_path"] == "review.txt"
    )
    (manifest.parent / proof["copy_path"]).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="byte count|bytes differ"):
        load_admitted_cohort(manifest, plan)


def test_evidence_cannot_be_selected_as_a_cohort(tmp_path: Path):
    manifest, plan, _ = _bundle(tmp_path)
    with pytest.raises(ValueError, match="complete pinned Stage-0 cohort"):
        load_admitted_cohort(
            manifest, replace(plan, selected_source_paths=("review.txt",))
        )


def test_raw_and_canonical_hashes_are_distinct_and_source_unchanged(tmp_path: Path):
    export, request, row = _export(tmp_path)
    assert (
        sha256_file(request.source_path) == request.source_sha256 == export.raw_sha256
    )
    assert export.canonical_sha256 != export.raw_sha256
    assert export.raw_copy_path.read_bytes() == request.source_path.read_bytes()
    parsed = next(csv.DictReader(io.StringIO(export.canonical_path.read_text())))
    assert {name: parsed[name] for name in project_target_fields(row, "9606")} == {
        name: value or "" for name, value in project_target_fields(row, "9606").items()
    }
    assert parsed["target_id"] == "" and parsed["target_chembl_id"] == "CHEMBL1"


@pytest.mark.parametrize(
    "updates",
    [
        {"taxonomy_id": "Homo sapiens"},
        {"taxonomy_id": "09606"},
        {"taxonomy_id": "9６06"},
        {"taxonomy_id": "9٦06"},
        {"target_id": "CHEMBL１"},
        {"target_id": "CHEMBL١"},
        {"target_type": "PROTEIN COMPLEX"},
        {"import_profile": "forged"},
        {"iuphar_class": "Enzyme"},
    ],
)
def test_export_refuses_unqualified_or_reserved_inputs(
    tmp_path: Path, updates: dict[str, str]
):
    with pytest.raises(ValueError):
        _export(tmp_path, **updates)
    assert not (tmp_path / "export").exists()


@pytest.mark.parametrize("identity", ["1１", "1١"])
def test_direct_iuphar_identity_rejects_mixed_unicode_digits(
    tmp_path: Path, identity: str
):
    source, _ = _source(tmp_path, confirmed_iuphar_id=identity)
    request = CohortExportRequest(
        source,
        sha256_file(source),
        CSV_SOURCE_FORMAT,
        NORMALIZED_TARGET_SCHEMA,
        "synthetic source field mapping",
        "unit-test",
        direct_iuphar_id_column="confirmed_iuphar_id",
    )
    with pytest.raises(ValueError, match="positive ASCII text"):
        export_canonical_cohort(request, output_dir=tmp_path / "export")
    assert sha256_file(source) == request.source_sha256
    assert not (tmp_path / "export").exists()


def test_duplicate_ids_preserve_rejection_ledger_without_choosing_first(tmp_path: Path):
    source, _ = _source(tmp_path)
    raw = source.read_bytes()
    source.write_bytes(raw + raw.splitlines(keepends=True)[1])
    request = CohortExportRequest(
        source,
        sha256_file(source),
        CSV_SOURCE_FORMAT,
        NORMALIZED_TARGET_SCHEMA,
        "synthetic mapping",
        "unit-test",
    )
    with pytest.raises(ValueError, match="duplicate target identity"):
        export_canonical_cohort(request, output_dir=tmp_path / "rejected")
    ledger = json.loads((tmp_path / "rejected/conversion-ledger.json").read_bytes())
    assert ledger["status"] == "REJECTED"
    assert ledger["diagnostic"]["source_record"] == 2
    assert not (tmp_path / "rejected/cohort.csv").exists()


def test_explicit_iuphar_mapping_never_uses_chembl_identity(tmp_path: Path):
    source, _ = _source(tmp_path, confirmed_iuphar_id="12")
    request = CohortExportRequest(
        source,
        sha256_file(source),
        CSV_SOURCE_FORMAT,
        NORMALIZED_TARGET_SCHEMA,
        "synthetic source field mapping",
        "unit-test",
        direct_iuphar_id_column="confirmed_iuphar_id",
    )
    export = export_canonical_cohort(request, output_dir=tmp_path / "export")
    rows = read_bioetl_target_kernel_csv_v1(
        export.canonical_path.read_bytes(),
        source_path="cohort.csv",
        target_kind="protein",
    )
    assert rows[0].fields["target_id"] == "12"
    with pytest.raises(ValueError, match="ChEMBL identity"):
        export_canonical_cohort(
            replace(request, direct_iuphar_id_column="target_id"),
            output_dir=tmp_path / "invalid",
        )


def test_arrow_source_retains_raw_snapshot_and_equivalent_projection(tmp_path: Path):
    _, row = _source(tmp_path)
    table = pa.Table.from_pylist([{**row, "taxonomy_id": 9606}])
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)
    source = tmp_path / "source.arrow"
    source.write_bytes(sink.getvalue().to_pybytes())
    request = CohortExportRequest(
        source,
        sha256_file(source),
        ARROW_SOURCE_FORMAT,
        NORMALIZED_TARGET_SCHEMA,
        "synthetic normalized Arrow snapshot",
        "unit-test",
    )
    export = export_canonical_cohort(request, output_dir=tmp_path / "export")
    assert export.raw_copy_path.read_bytes() == source.read_bytes()
    assert export.row_ids == ("chembl.target:CHEMBL1",)


def test_v2_publisher_never_overwrites_occurrence(tmp_path: Path):
    manifest, plan, _ = _bundle(tmp_path)
    before = manifest.read_bytes()
    assert verify_stage0_v2(manifest, plan.manifest_sha256, plan.selected_source_paths)
    with pytest.raises(FileExistsError):
        _bundle(tmp_path)
    assert manifest.read_bytes() == before
