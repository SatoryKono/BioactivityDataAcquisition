"""Canonical BioETL admission prevents species-name false absence."""

from __future__ import annotations

import csv
import hashlib
import io
import json

import pytest

from iuphar_target_class.matching import CatalogTarget
from iuphar_target_class.models import ProviderAnnotation, RunProvenance
from iuphar_target_class.pipeline import IndexedSnapshot, classify_batch
from iuphar_target_class.pipeline_acceptance import (
    SourceImport,
    VolumePlan,
    load_admitted_cohort,
)
from iuphar_target_class.pipeline_io import (
    BIOETL_TARGET_KERNEL_CSV_V1,
    read_bioetl_target_kernel_csv_v1,
    read_legacy_batch,
)

pytestmark = pytest.mark.unit

_HEADERS = (
    "input_row_id",
    "target_kind",
    "target_chembl_id",
    "target_id",
    "uniprot",
    "organism",
    "name",
    "legacy_iuphar_class",
)


def _csv(*, taxon="9606", identity="row:1", kind="protein"):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(_HEADERS)
    writer.writerow((identity, kind, "CHEMBL1", "1", "P12345", taxon, "R1", "old"))
    return stream.getvalue().encode()


def _read(content):
    return read_bioetl_target_kernel_csv_v1(
        content, source_path="canonical.csv", target_kind="protein"
    )


def test_canonical_profile_matches_numeric_species_and_preserves_provenance():
    content = _csv()
    rows = _read(content)
    raw = '{"id":"1","type":"gpcr"}'
    snapshot = IndexedSnapshot.build(
        snapshot_id="synthetic-contract-only",
        mapping_version="synthetic",
        complete=True,
        catalog=(CatalogTarget("1", ("P12345",), None, None, "9606", ("R1",), ()),),
        annotations={
            "1": ProviderAnnotation(
                "1", "gpcr", (), hashlib.sha256(raw.encode()).hexdigest(), "9606", raw
            )
        },
        family_nodes=(),
        type_to_class={"gpcr": "Receptor"},
        family_to_class={},
    )
    batch = classify_batch(
        rows,
        snapshot=snapshot,
        provenance=RunProvenance(
            "synthetic-contract-only", "base", "rules", "schema", "t", "t"
        ),
        run_id="synthetic-contract-only",
    )
    assert batch.rows[0].result.match_status == "matched"
    assert batch.rows[0].result.iuphar_class == "Receptor"
    assert rows[0].input_row_id == "row:1"
    assert rows[0].fields["target_chembl_id"] == "CHEMBL1"
    assert rows[0].fields["target_id"] == "1"
    assert rows[0].fields["legacy_iuphar_class"] == "old"
    assert rows[0].fields["import_profile"] == BIOETL_TARGET_KERNEL_CSV_V1
    assert rows[0].fields["source_sha256"] == hashlib.sha256(content).hexdigest()
    assert rows[0].fields["source_path"] == "canonical.csv"
    assert rows[0].fields["source_record"] == "1"


@pytest.mark.parametrize("taxon", ["", "9606", "10090", "10116", "999999999"])
def test_canonical_profile_preserves_explicit_taxid_or_blank(taxon):
    assert _read(_csv(taxon=taxon))[0].fields["organism"] == taxon


@pytest.mark.parametrize(
    "taxon",
    [
        "Human",
        "Homo sapiens",
        "Mouse",
        "unknown",
        "0",
        "-1",
        "+9606",
        "09606",
        " 9606",
        "9606.0",
        "９６０６",
        "9６06",
        "9٦06",
    ],
)
def test_canonical_profile_rejects_noncanonical_taxonomy_before_matching(taxon):
    with pytest.raises(ValueError, match="positive ASCII TaxID or blank"):
        _read(_csv(taxon=taxon))


@pytest.mark.parametrize("kind", ["", "unknown", "complex"])
def test_canonical_profile_rejects_mixed_or_unapproved_row_kind(kind):
    with pytest.raises(ValueError, match="target_kind differs"):
        _read(_csv(kind=kind))


@pytest.mark.parametrize(
    "source,kind", [("", "protein"), (" ", "protein"), ("a", "unknown")]
)
def test_canonical_profile_requires_explicit_source_and_kind(source, kind):
    with pytest.raises(ValueError, match="source and explicit target kind"):
        read_bioetl_target_kernel_csv_v1(_csv(), source_path=source, target_kind=kind)


@pytest.mark.parametrize("identity", ["", " ", "bad/id", "bad\nid", "bad\rid"])
def test_canonical_profile_refuses_unusable_row_identity(identity):
    with pytest.raises(ValueError, match="input_row_id"):
        _read(_csv(identity=identity))


def test_canonical_profile_refuses_duplicate_identity_even_with_same_business_id():
    content = _csv()
    with pytest.raises(ValueError, match="duplicate canonical CSV input_row_id"):
        _read(content + content.splitlines(keepends=True)[1])


@pytest.mark.parametrize(
    "content",
    [
        b"input_row_id,target_kind,organism\nr1,protein,9606\n",
        _csv().replace(b",name,", b",organism,"),
        _csv().replace(b",legacy_iuphar_class", b",source_sha256"),
    ],
)
def test_canonical_profile_requires_unique_complete_unspoofed_header(content):
    with pytest.raises(ValueError, match="bioetl_target_kernel_csv_v1 header"):
        _read(content)


@pytest.mark.parametrize(
    "content", [_csv().replace(b",old\r\n", b"\r\n"), _csv() + b"extra\n"]
)
def test_canonical_profile_refuses_wrong_row_width(content):
    with pytest.raises(ValueError, match="CSV row width"):
        _read(content)


def test_admitted_cohort_executes_explicit_canonical_profile(tmp_path):
    source = tmp_path / "canonical.csv"
    content = _csv()
    source.write_bytes(content)
    proof_names = (
        "content_checks.csv",
        "m_code_versions.csv",
        "provenance_map.csv",
        "stage_report.json",
    )
    for name in proof_names:
        (tmp_path / name).write_bytes(name.encode())
    document = {
        "artifact": "stage0_manifest",
        "stage": "0",
        "artifact_sha256": {
            name: hashlib.sha256(name.encode()).hexdigest() for name in proof_names
        },
        "copies": [
            {
                "source_path": "canonical.csv",
                "copy_path": "canonical.csv",
                "sha256": hashlib.sha256(content).hexdigest(),
                "byte_count": len(content),
            }
        ],
    }
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(document), encoding="utf-8")
    plan = VolumePlan(
        hashlib.sha256(manifest.read_bytes()).hexdigest(),
        ("canonical.csv",),
        1,
        "synthetic test fixture only",
        "synthetic test fixture only",
        (SourceImport("canonical.csv", BIOETL_TARGET_KERNEL_CSV_V1, "protein"),),
    )
    cohort = load_admitted_cohort(manifest, plan)
    assert cohort.rows == _read(content)
    assert source.read_bytes() == content


def test_legacy_import_keeps_historical_species_names_compatible():
    assert read_legacy_batch(_csv(taxon="Human"))[0].fields["organism"] == "Human"
