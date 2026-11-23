"""Owning TC-10 tests for indexed orchestration and separate child tables."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest
from iuphar_target_class import pipeline
from iuphar_target_class.evidence import ContractDefect
from iuphar_target_class.hierarchy import FamilyNode
from iuphar_target_class.matching import CatalogTarget
from iuphar_target_class.models import (
    Diagnostic,
    ProviderAnnotation,
    RawTargetRow,
    RunProvenance,
)
from iuphar_target_class.pipeline_acceptance import (
    SourceImport,
    VolumePlan,
    load_admitted_cohort,
    run_admitted_volume,
)
from iuphar_target_class.pipeline_io import (
    publish_batch,
    read_legacy_batch,
    read_chembl_target_csv_v1,
    render_batch,
    run_csv_pipeline,
)

pytestmark = pytest.mark.unit


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


def test_indexed_pipeline__empty_batch__reports_empty():
    result = _run()
    assert result.status == "empty"
    assert result.metrics["rows"] == 0 and not result.rows


def test_indexed_pipeline__all_invalid_rows__rejects_batch():
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


@pytest.mark.parametrize("identity", ["bad/id", "bad\nid", "bad\rid"])
def test_invalid_evidence_identity_cannot_publish_derived_fields(identity):
    raw = {"uniprot": "P12345", "organism": "Human", "ec": "3.1.-.-"}
    batch = _run(RawTargetRow(identity, raw, "protein"))
    output = batch.rows[0]
    assert output.result.input_validation_status == "invalid_input"
    assert output.validated.taxon is None
    assert output.validated.uniprot_accessions == ()
    assert output.validated.ec_numbers == ()
    assert output.validated.normalized_fields == {}
    row = json.loads(render_batch(batch)["classification.json"])[0]
    assert row["taxon_id"] is None and row["uniprot_accessions"] == []
    assert row["normalized_fields"] == {} and row["ec_numbers"] is None
    assert row["raw_fields"] == raw


def test_auxiliary_xref_divergence_survives_primary_shortlist():
    """RF-002 / Codex P2: auxiliary hits outside the primary shortlist still diverge.

    Primary shortlist must not admit auxiliary targets into identity channels, but
    diagnostics look them up separately so same-species xref hits become
    ``auxiliary_uniprot_divergence`` rather than a false unknown.
    """
    snapshot = pipeline.IndexedSnapshot.build(
        snapshot_id="fixture",
        mapping_version="fixture-release",
        complete=True,
        catalog=(
            CatalogTarget("1", ("P11111",), None, None, "Human", (), ()),
            CatalogTarget("2", ("Q88888",), None, None, "Human", (), ()),
        ),
        annotations={},
        family_nodes=(),
        type_to_class={},
        family_to_class={},
    )
    batch = _run(
        RawTargetRow(
            "aux-div",
            {
                "uniprot": "P11111",
                "uniprot_xref": "Q88888",
                "organism": "Human",
            },
            "protein",
        ),
        snapshot=snapshot,
    )
    result = batch.rows[0].result
    codes = {item.code for item in result.diagnostics}
    assert result.match_status == "matched"
    assert result.matched_target_id == "1"
    assert "auxiliary_uniprot_divergence" in codes
    assert "unknown_auxiliary_uniprot" not in codes


def test_identity_conflict_publishes_the_cross_species_witnesses():
    base = _snapshot()
    snapshot = pipeline.IndexedSnapshot.build(
        snapshot_id="fixture",
        mapping_version="fixture-release",
        complete=True,
        catalog=(
            base.catalog[0],
            replace(base.catalog[1], species="Mouse", uniprot_ids=("Q88888",)),
        ),
        annotations={},
        family_nodes=(),
        type_to_class={},
        family_to_class={},
    )
    batch = _run(
        RawTargetRow(
            "conflict",
            {"target_id": "1", "uniprot": "Q88888", "organism": "Human"},
            "protein",
        ),
        snapshot=snapshot,
    )
    result = batch.rows[0].result
    assert result.match_status == "identity_conflict"
    assert result.candidate_target_ids == ("1", "2")
    rendered = render_batch(batch)
    assert {row["target_id"] for row in json.loads(rendered["candidates.json"])} == {
        "1",
        "2",
    }
    evidence_sources = {
        row["source_id"] for row in json.loads(rendered["evidence.json"])
    }
    assert {"1", "2"}.issubset(evidence_sources)
    assert "primary_uniprot" in evidence_sources
    assert result.effective_class is None
    only_mouse = _run(
        RawTargetRow("filtered", {"uniprot": "Q88888", "organism": "Human"}, "protein"),
        snapshot=snapshot,
    )
    assert only_mouse.rows[0].result.match_status != "matched"


def test_shortlist_reports_cross_species_accession_conflict():
    snapshot = pipeline.IndexedSnapshot.build(
        snapshot_id="fixture",
        mapping_version="fixture-release",
        complete=True,
        catalog=(
            CatalogTarget("1", ("P99999",), None, None, "9606", ("Shared",), ()),
            CatalogTarget("1", ("P12345",), None, None, "10090", ("Shared",), ()),
        ),
        annotations={},
        family_nodes=(),
        type_to_class={},
        family_to_class={},
    )
    conflict = _run(
        RawTargetRow("q", {"uniprot": "P12345", "organism": "9606"}, "protein"),
        snapshot=snapshot,
    )
    assert conflict.rows[0].result.match_status == "identity_conflict"
    matched = _run(
        RawTargetRow("ok", {"uniprot": "P99999", "organism": "9606"}, "protein"),
        snapshot=snapshot,
    )
    assert matched.rows[0].result.match_status == "matched"


def test_confirmed_annotation_supplies_missing_taxon_without_rewriting_input():
    original = {"target_id": "1"}
    batch = _run(RawTargetRow("exact", original, "protein"))
    output = batch.rows[0]
    assert output.result.match_status == "matched"
    assert output.annotation.taxon == output.validated.taxon == "Human"
    assert output.validated.raw_fields == original
    assert output.validated.normalized_fields["organism"] is None
    assert (
        json.loads(render_batch(batch)["classification.json"])[0]["taxon_id"] == "Human"
    )
    ambiguous = _run(RawTargetRow("ambiguous", {"uniprot": "Q12345"}, "protein")).rows[
        0
    ]
    assert ambiguous.result.match_status != "matched"
    assert ambiguous.validated.taxon is None


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


@pytest.mark.parametrize(
    "raw,categories,depths,levels",
    [
        ("3.1.-.-", ["Hydrolases"], [2], [["3", "3.1"]]),
        (
            "1.1.1.1;3.1.-.-",
            ["Oxidoreductases", "Hydrolases"],
            [4, 2],
            [["1", "1.1", "1.1.1", "1.1.1.1"], ["3", "3.1"]],
        ),
    ],
)
def test_render_preserves_ec_categories_and_confirmed_depth(
    raw, categories, depths, levels
):
    batch = _run(RawTargetRow("ec-row", {"ec": raw}, "protein"))
    row = json.loads(render_batch(batch)["classification.json"])[0]
    assert row["raw_fields"]["ec"] == raw
    assert row["ec_categories"] == categories
    assert row["multiple_ec_categories"] is (len(categories) > 1)
    assert [number["depth"] for number in row["ec_numbers"]] == depths
    assert [number["confirmed_levels"] for number in row["ec_numbers"]] == levels


def test_diagnostic_evidence_resolves_or_is_explicitly_absent():
    batch = _run(
        RawTargetRow(
            "prediction",
            {"predicted_l1": "Enzyme", "predicted_l2": "Receptor"},
            "protein",
        ),
        RawTargetRow("bad-ec", {"ec": "bad"}, "protein"),
        RawTargetRow("direct", {"target_id": "1"}, "protein"),
    )
    rendered = render_batch(batch)
    witnesses = {item["evidence_id"] for item in json.loads(rendered["evidence.json"])}
    diagnostics = json.loads(rendered["diagnostics.json"])
    assert all(
        item["evidence_id"] is None or item["evidence_id"] in witnesses
        for item in diagnostics
    )
    predicted = [item for item in diagnostics if item["code"] == "candidate_only"]
    assert len(predicted) == 2 and all(
        item["evidence_id"] is None for item in predicted
    )
    row = next(row for row in batch.rows if row.result.input_row_id == "prediction")
    assert row.result.effective_class is None


def test_unexpected_dangling_diagnostic_is_a_contract_defect(monkeypatch):
    original = pipeline.apply_local

    def broken(*args, **kwargs):
        local = original(*args, **kwargs)
        return replace(
            local,
            diagnostics=(
                *local.diagnostics,
                Diagnostic(
                    "unexpected_witness",
                    "warning",
                    "missing real evidence",
                    "not-in-table",
                ),
            ),
        )

    monkeypatch.setattr(pipeline, "apply_local", broken)
    with pytest.raises(ContractDefect, match="unresolvable diagnostic"):
        _run(RawTargetRow("row", {"target_id": "1"}, "protein"))


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


_PROJECT_TARGET_CSV = (
    b"target_chembl_id,isoform_ids,isoform_names,isoforms,organism,pH_dependence,primaryAccession,target_names,target_uniprot_id\n"
    b"CHEMBL1,,,,Human,,P12345,Receptor,P12345\n"
)


def test_project_names_are_separate_channels_and_cannot_hide_ambiguity():
    raw = _PROJECT_TARGET_CSV.replace(b",Receptor,", b",receptor | shared,")
    rows = read_chembl_target_csv_v1(
        raw, source_path="target.csv", target_kind="protein"
    )
    assert rows[0].fields["target_names"] == "receptor | shared"
    assert (
        rows[0].fields["name"] == "receptor" and rows[0].fields["synonyms"] == "shared"
    )
    batch = _run(*rows)
    assert batch.rows[0].result.match_status == "ambiguous"
    assert batch.rows[0].result.candidate_target_ids == ("1", "2", "3")
    assert batch.rows[0].result.effective_class is None


def test_stage0_original_target_copies_use_frozen_explicit_profiles(tmp_path):
    manifest, _, plan = _stage0_fixture(tmp_path)
    document = json.loads(manifest.read_bytes())
    copies = []
    profiles = []
    for name in ("targets-a.csv", "targets-b.csv"):
        copy = tmp_path / (name + ".frozen")
        copy.write_bytes(_PROJECT_TARGET_CSV)
        copies.append(
            {
                "source_path": name,
                "copy_path": copy.name,
                "sha256": hashlib.sha256(_PROJECT_TARGET_CSV).hexdigest(),
                "byte_count": len(_PROJECT_TARGET_CSV),
            }
        )
        profiles.append(SourceImport(name, "chembl_target_csv_v1", "protein"))
    document["copies"] = copies
    manifest.write_text(json.dumps(document), encoding="utf-8")
    plan = replace(
        plan,
        manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
        selected_source_paths=tuple(p.source_path for p in profiles),
        expected_rows=2,
        source_imports=tuple(profiles),
    )
    cohort = load_admitted_cohort(manifest, plan)
    assert len({row.input_row_id for row in cohort.rows}) == 2
    with pytest.raises(ValueError, match="complete pinned Stage-0"):
        run_admitted_volume(
            manifest_path=manifest,
            plan=replace(
                plan,
                selected_source_paths=(profiles[0].source_path,),
                source_imports=(profiles[0],),
                expected_rows=1,
            ),
            snapshot=_snapshot(),
            provenance=_provenance(),
            run_id="subset",
            output_dir=tmp_path / "subset-volume",
        )
    assert not (tmp_path / "subset-volume").exists()
    for row in cohort.rows:
        assert row.target_kind == "protein"
        assert row.fields["target_chembl_id"] == "CHEMBL1"
        assert "target_id" not in row.fields
        assert row.fields["uniprot"] == row.fields["primaryAccession"] == "P12345"
        assert row.fields["organism"] == "Human"
        assert row.fields["source_record"] == "1"
    for entry in copies:
        assert (tmp_path / entry["copy_path"]).read_bytes() == _PROJECT_TARGET_CSV
    output = tmp_path / "volume"
    ticks = iter((1.0, 1.001))

    def clock():
        frozen = json.loads((output / "volume-config.json").read_bytes())
        assert frozen["source_imports"] == [
            {
                "source_path": p.source_path,
                "format_version": p.format_version,
                "target_kind": p.target_kind,
            }
            for p in profiles
        ]
        return next(ticks)

    _, result = run_admitted_volume(
        manifest_path=manifest,
        plan=plan,
        snapshot=_snapshot(),
        provenance=_provenance(),
        run_id="fixture",
        output_dir=output,
        clock=clock,
    )
    assert result["biological_accuracy_accepted"] is False
    with pytest.raises(ValueError, match="invalid CSV header"):
        load_admitted_cohort(manifest, replace(plan, source_imports=()))
    with pytest.raises(ValueError, match="duplicate or unselected"):
        load_admitted_cohort(
            manifest, replace(plan, source_imports=(*profiles, profiles[0]))
        )


@pytest.mark.parametrize("kind", ["", "inferred", "unknown"])
def test_original_target_import_never_guesses_kind(kind):
    with pytest.raises(ValueError, match="explicit target kind"):
        read_chembl_target_csv_v1(
            _PROJECT_TARGET_CSV, source_path="target.csv", target_kind=kind
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


@pytest.mark.parametrize("admission_complete", [True, False, None])
def test_volume_respects_scoped_admission_without_global_absence_claims(
    tmp_path, admission_complete
):
    manifest, _, plan = _stage0_fixture(tmp_path)
    scoped = pipeline.IndexedSnapshot.build(
        snapshot_id="fixture",
        mapping_version="fixture-release",
        complete=False,
        admission_complete=admission_complete,
        catalog=(),
        annotations={},
        family_nodes=(),
        type_to_class={},
        family_to_class={},
    )
    output = tmp_path / "scoped-volume"
    kwargs = {
        "manifest_path": manifest,
        "plan": plan,
        "snapshot": scoped,
        "provenance": _provenance(),
        "run_id": "scoped-fixture",
        "output_dir": output,
    }
    if not admission_complete:
        with pytest.raises(ValueError, match="admitted snapshot scope"):
            run_admitted_volume(**kwargs)
        assert not output.exists()
        return
    batch, report = run_admitted_volume(**kwargs)
    assert report["status"] == "PASS"
    assert report["biological_accuracy_accepted"] is False
    assert batch.rows[0].result.match_status == "source_unavailable"
    assert batch.rows[0].result.iuphar_class is None
    assert batch.rows[0].result.matched_target_id is None


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
