"""The V31 refresh must retain Delta identity, schema and history."""

from __future__ import annotations

import re
import shutil
from dataclasses import replace
from pathlib import Path

import pyarrow as pa
import pytest
import yaml
from deltalake import write_deltalake

from bioetl.infrastructure.storage import target_candidates as builder
from bioetl.infrastructure.storage import target_migration_validation as validation
from bioetl.infrastructure.storage.target_migration_validation import (
    _validate_refresh_history,
)
from iuphar_target_class.stage0.io import sha256_file
from tests.unit.infrastructure.storage.test_target_candidate_builder import (
    source_bundle as _source_bundle,
)

source_bundle = _source_bundle

pytestmark = pytest.mark.unit


@pytest.fixture
def delta_pair(tmp_path: Path) -> tuple[Path, Path]:
    """Copy a real small Delta table before extending its history."""
    source = tmp_path / "source"
    candidate = tmp_path / "candidate"
    write_deltalake(str(source), pa.table({"target_id": ["first"]}))
    shutil.copytree(source, candidate)
    return source, candidate


def test_accepts_exactly_one_delta_version(delta_pair: tuple[Path, Path]) -> None:
    source, candidate = delta_pair
    write_deltalake(str(candidate), pa.table({"target_id": ["second"]}), mode="append")
    _validate_refresh_history(source, candidate)


@pytest.mark.parametrize(
    ("append_count", "wrong_identity"),
    [(0, False), (2, False), (1, True)],
    ids=["no-append", "two-appends", "wrong-id"],
)
def test_rejects_wrong_delta_version_or_identity(
    delta_pair: tuple[Path, Path],
    append_count: int,
    wrong_identity: bool,
    tmp_path: Path,
) -> None:
    source, candidate = delta_pair
    if wrong_identity:
        candidate = tmp_path / "different-table"
        write_deltalake(str(candidate), pa.table({"target_id": ["first"]}))
    for version in range(append_count):
        write_deltalake(
            str(candidate),
            pa.table({"target_id": [f"appended-{version}"]}),
            mode="append",
        )
    with pytest.raises(ValueError, match="must append one version"):
        _validate_refresh_history(source, candidate)


def test_rejects_delta_schema_change(delta_pair: tuple[Path, Path]) -> None:
    source, candidate = delta_pair
    write_deltalake(
        str(candidate),
        pa.table({"target_id": ["second"], "classification": ["example"]}),
        mode="append",
        schema_mode="merge",
    )
    with pytest.raises(ValueError, match="changed the Delta schema"):
        _validate_refresh_history(source, candidate)


def test_rejects_changed_original_delta_data_file(
    delta_pair: tuple[Path, Path],
) -> None:
    source, candidate = delta_pair
    original_data = next(source.glob("*.parquet"))
    original_bytes = original_data.read_bytes()
    write_deltalake(str(candidate), pa.table({"target_id": ["second"]}), mode="append")
    candidate_data = candidate / original_data.name
    candidate_data.write_bytes(original_bytes + b"fixture-only extra bytes")
    with pytest.raises(ValueError, match="changed an original Delta file"):
        _validate_refresh_history(source, candidate)
    assert original_data.read_bytes() == original_bytes


def test_freeze_v31_refuses_restoration(source_bundle) -> None:
    request = source_bundle
    output = request.paths.workspace / "refresh-inputs.json"
    with pytest.raises(ValueError, match="requires unchanged cohorts"):
        builder.freeze_target_inputs(
            request.paths,
            legacy_include_fields=request.legacy_include_fields,
            output=output,
            restoration_manifest=request.paths.workspace / "restoration.json",
            source_profile="V31",
        )
    assert not output.exists()


def test_build_refuses_frozen_source_profile_mismatch(source_bundle) -> None:
    request = replace(source_bundle, source_profile="V31")
    with pytest.raises(ValueError, match="frozen source profile differs"):
        builder.build_target_candidates(request)
    assert not request.paths.candidate_silver.exists()
    assert not request.paths.candidate_gold.exists()


def _write_v32_candidate_config(path: Path) -> None:
    config = yaml.safe_load(path.read_bytes())
    config["pipeline"]["target_classification"]["table_contract"] = "3.2.0"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")


def test_build_v31_refuses_wrong_contract(source_bundle) -> None:
    request = source_bundle
    config_path = request.paths.candidate_config
    _write_v32_candidate_config(config_path)
    frozen = request.input_manifest.with_name("frozen-v31.json")
    builder.freeze_target_inputs(
        request.paths,
        legacy_include_fields=request.legacy_include_fields,
        output=frozen,
        source_profile="V31",
    )
    request = replace(
        request,
        source_profile="V31",
        input_manifest=frozen,
        input_manifest_sha256=sha256_file(frozen),
        deployment=replace(
            request.deployment, deployment_config_sha256=sha256_file(config_path)
        ),
    )
    with pytest.raises(
        ValueError, match=re.escape("V31 refresh requires contract 3.1.0")
    ):
        builder.build_target_candidates(request)
    assert not request.paths.candidate_silver.exists()
    assert not request.paths.candidate_gold.exists()


@pytest.mark.parametrize(
    ("refresh", "has_column", "occupied", "message"),
    [
        (True, False, False, "requires all existing classification columns"),
        (True, True, True, "target refresh destination is not empty"),
        (False, True, False, "requires a legacy V30 source"),
    ],
    ids=["missing-classification", "nonempty-destination", "nonlegacy-source"],
)
def test_layer_refuses_incompatible_schema_or_destination(
    tmp_path, refresh, has_column, occupied, message
) -> None:
    original = tmp_path / "delta"
    candidate = tmp_path / "candidate"
    original_columns = {"target_id": ["first"]}
    if has_column:
        original_columns["classification"] = ["example"]
    write_deltalake(str(original), pa.table(original_columns))
    sentinel = candidate / "existing.txt"
    if occupied:
        candidate.mkdir()
        sentinel.write_text("keep", encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        builder._write_layer(
            candidate,
            original,
            [],
            ("classification",),
            refresh_v31=refresh,
        )
    if occupied:
        assert list(candidate.iterdir()) == [sentinel]
        assert sentinel.read_text(encoding="utf-8") == "keep"
    else:
        assert not candidate.exists()


def test_compare_v31_refuses_cohort_addition() -> None:
    with pytest.raises(ValueError, match="requires unchanged cohorts"):
        validation.compare_target_rows(
            [],
            [],
            ("target_id",),
            allowed_additions=frozenset({("CHEMBL1", None)}),
            refresh_v31=True,
        )


@pytest.mark.parametrize(
    "wrong_contract", [False, True], ids=["restoration", "contract"]
)
def test_validation_v31_refuses_wrong_contract_or_restoration(
    source_bundle, wrong_contract
) -> None:
    request = source_bundle
    if wrong_contract:
        _write_v32_candidate_config(request.paths.candidate_config)
    manifest = None if wrong_contract else request.paths.workspace / "restoration.json"
    with pytest.raises(
        ValueError,
        match=re.escape("V31 refresh requires contract 3.1.0 and unchanged cohorts"),
    ):
        validation.validate_target_candidate(
            request.paths.checked(),
            request.legacy_include_fields,
            workspace=request.paths.workspace,
            restoration_manifest=manifest,
            source_profile="V31",
        )
