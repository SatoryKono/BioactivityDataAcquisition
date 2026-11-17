"""Frozen candidate construction preserves each layer and refuses input drift."""

from dataclasses import replace
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


@pytest.fixture
def source_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
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
    write_deltalake(
        str(paths.gold),
        coerce_null_types_for_delta(pa.Table.from_pylist([_gold(rows[0])])),
    )
    write_deltalake(str(paths.assay), pa.table({"target_id": ["CHEMBL1", None]}))
    profile = _synthetic_profile(tmp_path)
    monkeypatch.setattr(builder, "_load_candidate_profile", lambda _: profile)
    monkeypatch.setattr(validation, "_load_candidate_profile", lambda _: profile)
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
