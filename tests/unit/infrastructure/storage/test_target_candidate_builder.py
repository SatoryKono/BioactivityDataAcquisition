"""Frozen candidate construction preserves each layer and refuses input drift."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pytest
import yaml
from deltalake import write_deltalake

from bioetl.infrastructure.storage import target_candidates as builder
from bioetl.infrastructure.storage import target_migration_validation as validation
from bioetl.infrastructure.storage.delta.schema_ops import coerce_null_types_for_delta
from bioetl.infrastructure.storage.target_classification_migration import (
    TargetMigrationPaths,
)
from bioetl.infrastructure.storage.target_deployment_binding import (
    TargetDeploymentBinding,
)
from bioetl.infrastructure.schemas.silver_chembl_core import CHEMBL_TARGET_SCHEMA
from iuphar_target_class.stage0.io import sha256_file
from tests.unit.infrastructure.storage.test_target_migration_admission import (
    _old_row,
    _gold,
    _synthetic_profile,
)

pytestmark = pytest.mark.unit


@pytest.fixture(params=[False, True], ids=["plain-gold", "scd-gold"])
def source_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request):
    root = Path(__file__).resolve().parents[4]
    config = yaml.safe_load((root / "configs/entities/chembl/target.yaml").read_bytes())
    fields = tuple(config["hash_policy"]["hash_policy"]["include_fields"])
    canonical = tmp_path / "config.yaml"
    canonical.write_text(yaml.safe_dump(config), encoding="utf-8")
    deployment = tmp_path / "deployment.yaml"
    config["pipeline"]["target_classification"] = {
        "mode": "enrich",
        "snapshot_manifest": "profile.json",
        "snapshot_manifest_sha256": "a" * 64,
    }
    deployment.write_text(yaml.safe_dump(config), encoding="utf-8")
    paths = TargetMigrationPaths(
        tmp_path,
        tmp_path / "silver",
        tmp_path / "gold",
        tmp_path / "assay",
        canonical,
        tmp_path / "new-silver",
        tmp_path / "new-gold",
        deployment,
        tmp_path / "backup",
    )
    rows = [_old_row("CHEMBL1", fields), _old_row("CHEMBL2", fields)]
    write_deltalake(
        str(paths.silver), pa.Table.from_pylist(rows, schema=CHEMBL_TARGET_SCHEMA)
    )
    gold_row = _gold(rows[0])
    if request.param:
        gold_row.update(
            _valid_from=datetime(2026, 11, 16, tzinfo=UTC),
            _valid_to=None,
            _is_current=True,
            _version=1,
        )
    write_deltalake(
        str(paths.gold),
        coerce_null_types_for_delta(pa.Table.from_pylist([gold_row])),
    )
    write_deltalake(str(paths.assay), pa.table({"target_id": ["CHEMBL1", None]}))
    profile = _synthetic_profile(tmp_path)
    monkeypatch.setattr(
        builder, "_load_candidate_profile", lambda *_args, **_kwargs: profile
    )
    monkeypatch.setattr(
        validation, "_load_candidate_profile", lambda *_args, **_kwargs: profile
    )
    binding = TargetDeploymentBinding(
        str(canonical.resolve()),
        sha256_file(canonical),
        sha256_file(deployment),
        str(paths.silver.resolve()),
        str(paths.gold.resolve()),
        profile.profile_sha256,
        "d" * 64,
    )
    freeze = tmp_path / "frozen-inputs.json"
    builder.freeze_target_inputs(paths, legacy_include_fields=fields, output=freeze)
    request = builder.TargetCandidateBuildRequest(
        paths,
        freeze,
        sha256_file(freeze),
        tmp_path / "build",
        fields,
        "synthetic-builder",
        "2026-11-16T00:00:00Z",
        binding,
    )
    return request


def test_frozen_rows_build_real_candidates_and_pass_validator(source_bundle):
    request = source_bundle
    original = {
        name: builder._tree_hashes(getattr(request.paths, name))
        for name in ("silver", "gold", "assay", "config")
    }
    report = builder.build_target_candidates(request)
    assert report["status"] == "complete"
    assert len(validation._read_delta(request.paths.candidate_silver)) == 2
    assert len(validation._read_delta(request.paths.candidate_gold)) == 1
    for name, digest in original.items():
        assert builder._tree_hashes(getattr(request.paths, name)) == digest
    assert (request.output_dir / "build-manifest.json").is_file()
    assert (
        validation.validate_target_candidate(
            request.paths.checked(), request.legacy_include_fields
        )["fk_closure"]
        == "PASS"
    )


def test_v32_candidate_persists_details_and_revalidates_them(source_bundle):
    request = source_bundle
    config_path = request.paths.candidate_config
    config = yaml.safe_load(config_path.read_bytes())
    config["pipeline"]["target_classification"]["table_contract"] = "3.2.0"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    frozen = request.input_manifest.with_name("frozen-v32.json")
    builder.freeze_target_inputs(
        request.paths,
        legacy_include_fields=request.legacy_include_fields,
        output=frozen,
    )
    request = replace(
        request,
        input_manifest=frozen,
        input_manifest_sha256=sha256_file(frozen),
        deployment=replace(
            request.deployment, deployment_config_sha256=sha256_file(config_path)
        ),
    )

    report = builder.build_target_candidates(request)
    assert report["status"] == "complete"
    silver = validation._read_delta(request.paths.candidate_silver)
    gold = validation._read_delta(request.paths.candidate_gold)
    assert silver[0]["local_rule_ids"] is not None
    assert (
        gold[0]["classification_evidence_refs"]
        == silver[0]["classification_evidence_refs"]
    )
    gold[0]["local_rule_ids"] = None
    with pytest.raises(
        ValueError, match="candidate classification differs.*local_rule_ids"
    ):
        validation._verify_source_classifications(
            {"silver": silver, "gold": gold},
            builder._load_candidate_profile({}),
            "3.2.0",
        )


def test_restored_v32_rows_accept_only_the_selected_classification_fields():
    fields = validation.classification_fields("3.2.0")
    restored = {"target_id": "CHEMBL1", "content_hash": "original"}
    current = {**restored, **dict.fromkeys(fields), "content_hash": "candidate"}
    validation._assert_restored_values("CHEMBL1", restored, current, contract="3.2.0")
    with pytest.raises(ValueError, match="gained unexpected fields"):
        validation._assert_restored_values(
            "CHEMBL1", restored, current, contract="3.1.0"
        )
    with pytest.raises(ValueError, match="gained unexpected fields"):
        validation._assert_restored_values(
            "CHEMBL1", restored, {**current, "foreign": None}, contract="3.2.0"
        )


def test_source_drift_refuses_before_any_candidate_write(source_bundle):
    request = source_bundle
    (request.paths.silver / "unexpected-writer.txt").write_text("new bytes")
    with pytest.raises(ValueError, match="sources differ"):
        builder.build_target_candidates(request)
    assert not request.paths.candidate_silver.exists()
    assert not request.output_dir.exists()


def test_changed_input_manifest_cannot_be_rebound_silently(source_bundle):
    request = replace(source_bundle, input_manifest_sha256="f" * 64)
    with pytest.raises(ValueError, match="manifest digest"):
        builder.build_target_candidates(request)
    assert not request.paths.candidate_gold.exists()


def test_failed_build_occurrence_is_not_overwritten(source_bundle):
    request = source_bundle
    request.output_dir.mkdir()
    (request.output_dir / "preserved.txt").write_text("keep")
    with pytest.raises(ValueError, match="occurrence already exists"):
        builder.build_target_candidates(request)
    assert (request.output_dir / "preserved.txt").read_text() == "keep"


@pytest.mark.parametrize("name", ["candidate_silver", "candidate_gold"])
@pytest.mark.parametrize("nested", [False, True])
def test_build_evidence_cannot_overlap_candidate_tables(source_bundle, name, nested):
    path = getattr(source_bundle.paths, name)
    request = replace(source_bundle, output_dir=path / "evidence" if nested else path)
    with pytest.raises(ValueError, match="overlaps a preserved resource"):
        builder.build_target_candidates(request)
    assert not path.exists()
