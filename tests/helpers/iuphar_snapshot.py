"""Synthetic RF004 source bundles; never evidence of biological approval."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from bioetl.infrastructure.adapters.iuphar._manifest import sha256
from bioetl.infrastructure.adapters.iuphar._official_targets_csv import SPECIES_COLUMNS
from bioetl.infrastructure.adapters.iuphar.snapshot_payload import build_snapshot_bundle
from iuphar_target_class.stage0.io import canonical_json_bytes


def write_fixture_json(path: Path, value: object) -> str:
    path.write_bytes(canonical_json_bytes(value))
    return sha256(path.read_bytes())


def synthetic_export_row(*, target_id="1", family_id="1", family_type="gpcr"):
    row = dict.fromkeys(
        (
            "Type",
            "Family id",
            "Family name",
            "Target id",
            "Target name",
            "Subunit id",
            "Subunit name",
            "Target systematic name",
            "Target abbreviated name",
            "synonyms",
        ),
        "",
    )
    row.update(
        {
            "Type": family_type,
            "Family id": family_id,
            "Family name": "synthetic family",
            "Target id": target_id,
            "Target name": "known enzyme",
            "synonyms": "enzyme alias",
        }
    )
    for taxon, (prefix, symbol) in SPECIES_COLUMNS.items():
        row.update(
            {
                prefix + " SwissProt": "P12345"
                if taxon == "9606"
                else ("Q12345" if taxon == "10116" else "Q99999"),
                prefix + " Entrez Gene": {"9606": "10", "10116": "20", "10090": "30"}[
                    taxon
                ],
                symbol: "GENE" + taxon,
            }
        )
    return row


def synthetic_snapshot_sources(
    root: Path, *, rows=None, species=("9606",), included=None
):
    root.mkdir(parents=True, exist_ok=True)
    rows = rows if rows is not None else [synthetic_export_row()]
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(["# GtoPdb Version: 2026.3.1 - published: 2026-10-12"])
    writer.writerow(rows[0])
    writer.writerows([row.values() for row in rows])
    raw = stream.getvalue().encode()
    (root / "official-fixture.csv").write_bytes(raw)
    acquisition = root / "acquisition.json"
    acquisition_hash = write_fixture_json(
        acquisition,
        {
            "artifact": "bioetl_iuphar_acquisition",
            "schema_version": 1,
            "fixture_kind": "synthetic_contract_fixture",
            "source_format": "gtopdb_targets_csv_v1",
            "provider_release": "2026.3.1",
            "retrieved_at": "2026-11-16T00:00:00Z",
            "raw_artifacts": {
                "targets_csv": {
                    "path": "official-fixture.csv",
                    "sha256": sha256(raw),
                    "byte_count": len(raw),
                    "source_url": "https://www.guidetopharmacology.org/synthetic-contract-fixture.csv",
                }
            },
        },
    )
    targets = sorted({row["Target id"] for row in rows}, key=int)
    selected = targets if included is None else list(included)
    exclusions = [
        {
            "target_id": target,
            "source_records": [
                i for i, row in enumerate(rows, 1) if row["Target id"] == target
            ],
            "rationale": "synthetic reviewed exclusion fixture only",
        }
        for target in targets
        if target not in selected
    ]
    variants = sum(
        any(
            row[SPECIES_COLUMNS[taxon][0] + " SwissProt"]
            or row[SPECIES_COLUMNS[taxon][0] + " Entrez Gene"]
            or row[SPECIES_COLUMNS[taxon][1]]
            for row in rows
            if row["Target id"] == target
        )
        for target in selected
        for taxon in species
    )
    scope = {
        "species_taxon_ids": list(species),
        "required_family_types": sorted(
            {row["Type"] for row in rows if row["Target id"] in selected}
        ),
        "included_target_ids": selected,
        "excluded_targets": exclusions,
        "selection_basis": "reviewed_single_protein_targets",
        "expected_raw_row_count": len(rows),
        "expected_provider_target_count": len(targets),
        "expected_variant_count": variants,
    }
    review_hash = write_fixture_json(
        root / "scope-review.json",
        {
            "artifact": "bioetl_iuphar_scope_review",
            "schema_version": 1,
            "fixture_kind": "synthetic_contract_fixture",
            "reviewer_reference": "synthetic contract expectation only",
            "approval_reference": "synthetic contract expectation only",
            "acquisition_sha256": acquisition_hash,
            "scope_sha256": sha256(canonical_json_bytes(scope)),
        },
    )
    coverage = root / "coverage.json"
    coverage_hash = write_fixture_json(
        coverage,
        {
            "artifact": "bioetl_iuphar_coverage",
            "schema_version": 1,
            "fixture_kind": "synthetic_contract_fixture",
            "acquisition_sha256": acquisition_hash,
            "scope": scope,
            "review": {"path": "scope-review.json", "sha256": review_hash},
        },
    )
    return acquisition, acquisition_hash, coverage, coverage_hash


def synthetic_snapshot_bundle(
    root: Path, *, rows=None, species=("9606",), included=None
):
    acquisition, acquisition_hash, coverage, coverage_hash = synthetic_snapshot_sources(
        root / "sources", rows=rows, species=species, included=included
    )
    output = root / "bundle"
    bundle = build_snapshot_bundle(
        acquisition=acquisition,
        acquisition_sha256=acquisition_hash,
        coverage=coverage,
        coverage_sha256=coverage_hash,
        output_dir=output,
    )
    return output, bundle


def synthetic_reference_receipt(
    snapshot_sha256: str, *, root: Path
) -> dict[str, object]:
    """Shape-only positive fixture, explicitly unrelated to biological acceptance."""
    from bioetl.infrastructure.adapters.iuphar.snapshot_loader import (
        OUTPUT_NAMES,
        REQUIRED_ACCEPTANCE_CHECKS,
    )
    from iuphar_target_class.reference_coverage import REQUIRED_REFERENCE_CATEGORIES

    scope = {
        "scope_id": "synthetic-contract-only",
        "kind": "bounded_reviewed_reference",
        "approval_reference": "synthetic contract fixture only",
        "limitations": ["Synthetic contract fixture; no biological approval"],
        "reviewed_row_ids": ["synthetic-row"],
        "unreviewed_row_ids": [],
    }
    references = [{"path": "synthetic-review.txt", "sha256": "f" * 64}]
    categories = {
        category: {
            "status": "real_reference"
            if category == "direct_family"
            else "out_of_scope",
            "case_row_ids": ["synthetic-row"] if category == "direct_family" else [],
            "rationale": "Synthetic contract fixture only",
            "source_references": references,
        }
        for category in REQUIRED_REFERENCE_CATEGORIES
    }
    receipt = {
        "artifact": "bioetl_iuphar_acceptance",
        "schema_version": 2,
        "fixture_kind": "synthetic_contract_fixture",
        "scope": "offline_target_integration",
        "status": "PASS",
        "snapshot_manifest_sha256": snapshot_sha256,
        "stage0_manifest_sha256": "a" * 64,
        "expected_labels_sha256": "b" * 64,
        "cohort_manifest_sha256": "d" * 64,
        "conversion_ledger_sha256": "e" * 64,
        "output_sha256": dict.fromkeys(OUTPUT_NAMES, "c" * 64),
        "checks": dict.fromkeys(REQUIRED_ACCEPTANCE_CHECKS, "PASS"),
        "reference_cases_accepted": True,
        "biological_accuracy_accepted": False,
        "run_id": "synthetic-contract-run",
        "reviewer_reference": "synthetic contract fixture only",
        "normalization_version": "bioetl-iuphar-input-v1",
        "rules_version": "local-rules-2026.11.23",
        "classification_schema_version": "3.1.0",
        "matching_policy_version": "rf002-uniprot-roles-2026-11-23",
        "scope_declaration": scope,
        "scientific_status": "bounded_reference_cases_only",
        "reference_coverage": {
            "schema_version": 2,
            "cohort_row_count": 1,
            "reviewed_row_ids": ["synthetic-row"],
            "unreviewed_row_ids": [],
            "categories": categories,
        },
    }
    root.mkdir(parents=True, exist_ok=True)
    artifact_references = []
    bindings = {
        "stage0_manifest": "stage0_manifest_sha256",
        "expected_labels": "expected_labels_sha256",
        "cohort_manifest": "cohort_manifest_sha256",
        "conversion_ledger": "conversion_ledger_sha256",
        "pipeline_proof": "pipeline_proof_sha256",
        "pipeline_report": "pipeline_report_sha256",
    }
    outputs = {}
    for kind in (*bindings, *sorted(OUTPUT_NAMES)):
        path = root / (kind if kind.endswith(".json") else kind + ".json")
        digest = write_fixture_json(
            path, {"fixture_kind": "synthetic_contract_fixture", "kind": kind}
        )
        artifact_references.append(
            {"kind": kind, "immutable_uri": path.resolve().as_uri(), "sha256": digest}
        )
        if kind in bindings:
            receipt[bindings[kind]] = digest
        else:
            outputs[kind] = digest
    receipt["output_sha256"] = outputs
    receipt["artifact_references"] = artifact_references
    return receipt
