"""Owning TC-10 tests for indexed orchestration and separate child tables."""

from __future__ import annotations

import hashlib
import json

import pytest
from iuphar_target_class import pipeline
from iuphar_target_class.hierarchy import FamilyNode
from iuphar_target_class.matching import CatalogTarget
from iuphar_target_class.models import ProviderAnnotation, RawTargetRow, RunProvenance
from iuphar_target_class.pipeline_acceptance import (
    VolumePlan,
    load_admitted_cohort,
    run_admitted_volume,
)
from iuphar_target_class.pipeline_io import (
    publish_batch,
    read_legacy_batch,
    render_batch,
    run_csv_pipeline,
)


def _provenance() -> RunProvenance:
    return RunProvenance(
        "fixture", "fixture-base", "fixture-rules", "fixture-schema", "t", "t"
    )


def _snapshot(*, complete=True, broken=False):
    catalog = (
        CatalogTarget("1", ("P12345",), "R1", "10", "Human", ("receptor",), ()),
        CatalogTarget("2", ("Q12345",), "E2", "20", "Human", ("enzyme",), ("shared",)),
        CatalogTarget("3", ("Q12345",), "E3", "30", "Human", ("other",), ("shared",)),
    )
    raw = '{"id":"1","type":"gpcr"}'
    annotation = ProviderAnnotation(
        "1",
        "gpcr",
        ("family",),
        hashlib.sha256(raw.encode()).hexdigest(),
        "Human",
        raw,
    )
    return pipeline.IndexedSnapshot.build(
        snapshot_id="fixture",
        mapping_version="fixture-release",
        complete=complete,
        catalog=catalog,
        annotations={"1": annotation},
        family_nodes=(FamilyNode("family", ("missing",) if broken else (), "gpcr"),),
        type_to_class={"gpcr": "Receptor"},
        family_to_class={},
    )


def _run(*rows, snapshot=None):
    return pipeline.classify_batch(
        rows,
        snapshot=snapshot or _snapshot(),
        provenance=_provenance(),
        run_id="fixed",
    )


def test_empty_batch():
    result = _run()
    assert result.status == "empty"
    assert result.metrics["rows"] == 0 and not result.rows


def test_all_invalid_batch():
    result = _run(RawTargetRow("row", {}, "invented"))
    assert result.status == "rejected"
    assert result.rows[0].result.match_status is None
    assert result.metrics["invalid_rows"] == 1


def test_approved_channels_are_indexed_and_match_is_reproducible():
    good = RawTargetRow(
        "row-a", {"target_id": "1", "uniprot": "P12345", "organism": "Human"}, "protein"
    )
    invalid = RawTargetRow("row-b", {}, "unrecognized")
    lhs = _run(good, invalid)
    rhs = _run(invalid, good)
    assert render_batch(lhs) == render_batch(rhs)
    result = lhs.rows[0]
    assert result.result.match_status == "matched"
    assert result.result.iuphar_class == "Receptor"
    assert result.result.effective_class == "Receptor"
    assert {e.evidence_type for e in result.evidence.records} == {
        "match",
        "iuphar_raw",
        "iuphar_mapping",
    }
    assert result.result.provenance == _provenance()


def test_ambiguous_and_source_unavailable_are_not_absence():
    ambiguous = RawTargetRow(
        "r1", {"uniprot": "Q12345", "organism": "Human"}, "protein"
    )
    absent = RawTargetRow("r2", {"target_id": "99"}, "protein")
    result = _run(ambiguous, absent, snapshot=_snapshot(complete=False))
    assert result.rows[0].result.match_status == "ambiguous"
    assert result.rows[0].result.candidate_target_ids == ("2", "3")
    assert result.rows[1].result.match_status == "source_unavailable"
    assert _run(absent).rows[0].result.match_status == "not_found"


def test_graph_defect_and_complex_do_not_promote_the_wrong_class():
    item = RawTargetRow("r1", {"target_id": "1", "organism": "Human"}, "protein")
    bad = _run(item, snapshot=_snapshot(broken=True)).rows[0]
    assert bad.result.iuphar_annotation_status == "partial"
    graph_error = next(d for d in bad.result.diagnostics if d.code == "graph_error")
    assert graph_error.evidence_id in bad.result.match_evidence_ids
    complex_row = RawTargetRow(
        "r2", {**item.fields, "component_ids": "iuphar:1;CHEMBL1"}, "complex"
    )
    batch = _run(complex_row)
    result = batch.rows[0].result
    assert result.decision_status == "requires_review"
    assert result.effective_class is None
    assert result.iuphar_class is None and result.matched_target_id is None
    assert [(row.component_id, row.iuphar_class) for row in batch.components] == [
        ("CHEMBL1", None),
        ("iuphar:1", "Receptor"),
    ]


def test_legacy_original_bytes_and_outputs_preserved(tmp_path):
    path = tmp_path / "legacy.csv"
    content = (
        b"input_row_id,target_kind,target_id,old_iuphar_class\nr1,protein,1,Legacy\n"
    )
    path.write_bytes(content)
    result = _run(*read_legacy_batch(content))
    artifacts = render_batch(result)
    row = json.loads(artifacts["classification.json"])[0]
    assert row["legacy_iuphar_class"] == "Legacy" and row["iuphar_class"] == "Receptor"
    assert set(artifacts) == {
        "classification.json",
        "evidence.json",
        "candidates.json",
        "components.json",
        "diagnostics.json",
        "metrics.json",
    }
    args = {
        "root": tmp_path,
        "snapshot_id": "fixture",
        "rules_version": "rules",
        "run_id": "fixed",
        "result": result,
    }
    assert publish_batch(path, **args) is not None
    assert publish_batch(path, **args) is None
    assert path.read_bytes() == content


def test_same_chembl_id_does_not_drop_rows_and_io_keeps_source_fields(tmp_path):
    path = tmp_path / "source.csv"
    original = (
        b"input_row_id,target_kind,target_id,target_chembl_id,isoform_id,isoform_suffix\n"
        b"r1,protein,1,CHEMBL1,P12345-2,-2\n"
        b"r2,protein,99,CHEMBL1,,\n"
    )
    path.write_bytes(original)
    result, output = run_csv_pipeline(
        path,
        root=tmp_path,
        snapshot=_snapshot(),
        provenance=_provenance(),
        run_id="fixed",
    )
    assert output is not None and path.read_bytes() == original
    rows = json.loads(render_batch(result)["classification.json"])
    assert [(x["input_row_id"], x["target_chembl_id"]) for x in rows] == [
        ("r1", "CHEMBL1"),
        ("r2", "CHEMBL1"),
    ]
    assert rows[0]["isoform_id"] == "P12345-2" and rows[0]["isoform_suffix"] == "-2"
    assert (
        rows[0]["provider_release"] == "fixture-release"
        and len(rows[0]["payload_sha256"]) == 64
    )
    assert rows[1]["effective_class"] is None


def test_approved_runtime_uses_exact_merged_mapping_release():
    raw = '{"id":"1","type":"gpcr"}'
    annotation = ProviderAnnotation(
        "1",
        "gpcr",
        ("1",),
        hashlib.sha256(raw.encode()).hexdigest(),
        None,
        raw,
    )
    args = {
        "snapshot_id": "fixture",
        "complete": False,
        "catalog": (CatalogTarget("1", (), None, None, None, (), ()),),
        "annotations": {"1": annotation},
    }
    with pytest.raises(ValueError, match="does not match approved mapping"):
        pipeline.IndexedSnapshot.from_approved_gtopdb(release="stale", **args)
    ready = pipeline.IndexedSnapshot.from_approved_gtopdb(release="2026.3.1", **args)
    assert len(ready.family_to_class) == 744 and "694" not in ready.family_to_class
    row = _run(RawTargetRow("r1", {"target_id": "1"}, "protein"), snapshot=ready).rows[
        0
    ]
    assert row.result.iuphar_class == "Receptor"
    assert row.result.iuphar_mapping_version == "2026.3.1"


def _stage0_fixture(tmp_path):
    names = (
        "content_checks.csv",
        "m_code_versions.csv",
        "provenance_map.csv",
        "stage_report.json",
    )
    for name in names:
        (tmp_path / name).write_bytes(name.encode())
    raw = b"input_row_id,target_kind,target_id\nr1,protein,1\n"
    copy = tmp_path / "frozen.bin"
    copy.write_bytes(raw)
    manifest = tmp_path / "manifest.json"
    doc = {
        "artifact": "stage0_manifest",
        "stage": "0",
        "artifact_sha256": {
            name: hashlib.sha256(name.encode()).hexdigest() for name in names
        },
        "copies": [
            {
                "source_path": "source.csv",
                "copy_path": "frozen.bin",
                "sha256": hashlib.sha256(raw).hexdigest(),
                "byte_count": len(raw),
            }
        ],
    }
    manifest.write_text(json.dumps(doc), encoding="utf-8")
    return (
        manifest,
        copy,
        VolumePlan(
            hashlib.sha256(manifest.read_bytes()).hexdigest(),
            ("source.csv",),
            1,
            "owning test fixture only",
            "owning test fixture only",
        ),
    )


def test_volume_refuses_changed_cohort_and_records_config_before_run(tmp_path):
    manifest, copy, plan = _stage0_fixture(tmp_path)
    output = tmp_path / "result"
    stamps = iter((100.0, 100.01))

    def clock():
        assert (output / "volume-config.json").is_file()
        return next(stamps)

    batch, report = run_admitted_volume(
        manifest_path=manifest,
        plan=plan,
        snapshot=_snapshot(),
        provenance=_provenance(),
        run_id="fixture",
        output_dir=output,
        clock=clock,
    )
    assert batch.rows[0].result.effective_class == "Receptor"
    assert report["status"] == "PASS" and not report["biological_accuracy_accepted"]
    copy.write_bytes(copy.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="cohort source bytes differ"):
        load_admitted_cohort(manifest, plan)


def test_legacy_target_all_without_provenance_does_not_create_direct():
    source = (
        b"input_row_id,target_kind,target_id,old_iuphar_class\n"
        b"legacy-orphan,protein,99,Receptor\n"
    )
    batch = _run(*read_legacy_batch(source))
    row = json.loads(render_batch(batch)["classification.json"])[0]
    assert row["legacy_iuphar_class"] == "Receptor"
    assert row["raw_fields"]["old_iuphar_class"] == "Receptor"
    assert row["match_status"] == "not_found"
    assert row["effective_class"] is None and row["iuphar_class"] is None
    assert not row["match_evidence_ids"]


def test_heterogeneous_complex_retains_distinct_classes_without_promoting_either():
    annotations = {}
    for key, kind in (("1", "gpcr"), ("2", "enzyme")):
        raw = json.dumps({"id": key, "type": kind})
        annotations[key] = ProviderAnnotation(
            key, kind, (), hashlib.sha256(raw.encode()).hexdigest(), "Human", raw
        )
    catalog = _snapshot().catalog
    snapshot = pipeline.IndexedSnapshot.build(
        snapshot_id="fixture",
        mapping_version="fixture-release",
        complete=True,
        catalog=catalog,
        annotations=annotations,
        family_nodes=(),
        type_to_class={"gpcr": "Receptor", "enzyme": "Enzyme"},
        family_to_class={},
    )
    row = RawTargetRow(
        "complex", {"target_id": "1", "component_ids": "iuphar:1;iuphar:2"}, "complex"
    )
    batch = _run(row, snapshot=snapshot)
    assert batch.rows[0].result.decision_status == "requires_review"
    assert batch.rows[0].result.effective_class is None
    assert batch.rows[0].result.iuphar_class is None
    assert {(item.component_id, item.iuphar_class) for item in batch.components} == {
        ("iuphar:1", "Receptor"),
        ("iuphar:2", "Enzyme"),
    }
    assert all(item.payload_sha256 for item in batch.components)


def test_distinct_chembl_rows_keep_conflicting_direct_evidence():
    annotations = {}
    for key, kind, families in (
        ("1", "gpcr", ("family-gpcr", "family-enzyme")),
        ("2", "enzyme", ("family-enzyme",)),
    ):
        raw = json.dumps({"id": key, "type": kind, "families": families})
        annotations[key] = ProviderAnnotation(
            key, kind, families, hashlib.sha256(raw.encode()).hexdigest(), "Human", raw
        )
    snapshot = pipeline.IndexedSnapshot.build(
        snapshot_id="fixture",
        mapping_version="fixture-release",
        complete=True,
        catalog=_snapshot().catalog,
        annotations=annotations,
        family_nodes=(
            FamilyNode("family-gpcr", (), "gpcr"),
            FamilyNode("family-enzyme", (), "enzyme"),
        ),
        type_to_class={"gpcr": "Receptor", "enzyme": "Enzyme"},
        family_to_class={"family-gpcr": "Receptor", "family-enzyme": "Enzyme"},
    )
    batch = _run(
        RawTargetRow("a", {"target_id": "1", "target_chembl_id": "CHEMBL1"}, "protein"),
        RawTargetRow("b", {"target_id": "2", "target_chembl_id": "CHEMBL1"}, "protein"),
        snapshot=snapshot,
    )
    rows = json.loads(render_batch(batch)["classification.json"])
    assert len(rows) == 2
    assert [x["target_chembl_id"] for x in rows] == ["CHEMBL1", "CHEMBL1"]
    assert rows[0]["iuphar_annotation_status"] == "conflicting"
    assert rows[0]["iuphar_class"] is None
    assert set(rows[0]["iuphar_class_candidates"]) == {"Receptor", "Enzyme"}
    assert rows[1]["iuphar_class"] == "Enzyme"
    assert all(row["match_evidence_ids"] for row in rows)
