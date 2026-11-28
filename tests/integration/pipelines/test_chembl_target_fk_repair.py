"""Actual target transformer/normalizer/filter/writer recovery on synthetic inputs."""

from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path
from shutil import copytree, ignore_patterns
from uuid import UUID

import pyarrow as pa
import pytest
import yaml
from deltalake import DeltaTable, write_deltalake

from bioetl.composition.bootstrap.assembly.target_classification_runtime import (
    isolated_v30_target_fk_repair,
    resolve_target_runtime_config,
    validate_target_runtime_dependency,
)
from bioetl.composition.bootstrap.cli.lineage import (
    TargetFKRepairRequest,
    _verify_isolated_paths,
    isolate_recovery_config,
    prepare_target_fk_repair,
)
from bioetl.infrastructure.config.pipeline_config_api import (
    load_pipeline_config,
    load_pipeline_config_from_root,
)
from bioetl.infrastructure.config.settings_api import Settings
from tests.unit.infrastructure.storage.test_target_fk_repair import make_source

pytestmark = pytest.mark.integration


def _raw_record() -> dict:
    return {
        "target_chembl_id": "CHEMBL3",
        "target_type": "SINGLE PROTEIN",
        "pref_name": "Synthetic recovery enzyme",
        "tax_id": 9606,
        "organism": "Homo sapiens",
        "species_group_flag": False,
        "target_components": [
            {
                "accession": "P12345",
                "component_id": 3,
                "component_type": "PROTEIN",
                "relationship": "SINGLE PROTEIN",
                "target_component_synonyms": [],
                "target_component_xrefs": [],
            }
        ],
    }


@pytest.fixture
def active_repair_request(tmp_path, monkeypatch):
    repo = Path(__file__).resolve().parents[3]
    root = tmp_path / "synthetic-repo"
    old = {
        "target_id": "CHEMBL1",
        "entity_id": "chembl:CHEMBL1",
        "content_hash": "original-hash",
        "target_type": "SINGLE PROTEIN",
        "pref_name": "Original target",
        "organism": "Homo sapiens",
    }
    for layer in ("silver", "gold"):
        write_deltalake(
            root / "data/output" / layer / "chembl/target",
            pa.Table.from_pylist([old]),
            partition_by=["target_type"] if layer == "silver" else None,
        )
    write_deltalake(
        root / "data/output/gold/chembl/assay",
        pa.Table.from_pylist([{"target_id": "CHEMBL3"}]),
    )
    source = make_source(tmp_path / "synthetic-source", ["CHEMBL3"], [_raw_record()])
    # Both pipeline and contract policy must come from the same explicit root.
    copytree(
        repo / "configs", root / "configs", ignore=ignore_patterns(".env*", "*.env")
    )
    monkeypatch.chdir(root)
    return TargetFKRepairRequest(
        root,
        source,
        root / "reports/local/repair",
        UUID("00000000-0000-4000-8000-0000000000a1"),
        datetime(2026, 11, 16, 18, 0, tzinfo=UTC),
    )


@pytest.fixture
def repair_request(active_repair_request):
    target_path = (
        active_repair_request.repo_root / "configs/entities/chembl/target.yaml"
    )
    document = yaml.safe_load(target_path.read_bytes())
    document["pipeline"]["target_classification"] = {"mode": "off"}
    target_path.write_text(yaml.safe_dump(document), encoding="utf-8")
    return active_repair_request


@pytest.mark.asyncio
async def test_active_profile_cannot_prepare_v30_candidate(active_repair_request):
    with pytest.raises(
        ValueError, match="V30 recovery requires classification mode off"
    ):
        await prepare_target_fk_repair(active_repair_request)
    assert not active_repair_request.output_directory.exists()


@pytest.mark.parametrize(
    "check", [resolve_target_runtime_config, validate_target_runtime_dependency]
)
def test_v30_repair_admission_is_scoped_to_the_isolated_config(repair_request, check):
    ordinary = load_pipeline_config_from_root(
        "chembl_target", configs_root=repair_request.repo_root / "configs"
    )
    isolated = isolate_recovery_config(
        ordinary, repair_request.output_directory / "execution" / "data"
    )
    with isolated_v30_target_fk_repair(isolated):
        check(isolated)
        with pytest.raises(ValueError, match="off requires exact replay"):
            check(ordinary)
    with pytest.raises(ValueError, match="off requires exact replay"):
        check(isolated)


@pytest.mark.asyncio
async def test_actual_v30_runner_prepares_additive_candidate(repair_request):
    path = await prepare_target_fk_repair(repair_request)
    document = json.loads(path.read_bytes())
    assert document["execution"]["run_id"] == str(repair_request.run_id)
    assert document["execution"]["metrics"]["records_silver"] == 1
    assert document["execution"]["metrics"]["records_gold"] == 1
    for layer in ("silver", "gold"):
        rows = (
            DeltaTable(path.parent / layer / "chembl/target")
            .to_pyarrow_table()
            .to_pylist()
        )
        assert len(rows) == 2
        by_id = {row["target_id"]: row for row in rows}
        assert by_id["CHEMBL1"]["content_hash"] == "original-hash"
        assert len(by_id["CHEMBL3"]["content_hash"]) == 64
        assert by_id["CHEMBL3"]["target_type"] == "SINGLE PROTEIN"
        assert by_id["CHEMBL3"]["component_accessions"] == '["P12345"]'


@pytest.mark.asyncio
async def test_actual_gold_ineligibility_blocks_candidate(repair_request):
    raw = _raw_record()
    raw["target_components"][0]["component_type"] = "DNA"
    source = make_source(
        repair_request.source_directory.parent / "ineligible-source", ["CHEMBL3"], [raw]
    )
    repair_request = TargetFKRepairRequest(
        repair_request.repo_root,
        source,
        repair_request.output_directory,
        repair_request.run_id,
        repair_request.started_at,
    )
    with pytest.raises(ValueError, match="records_gold"):
        await prepare_target_fk_repair(repair_request)
    assert not (repair_request.output_directory / "tables/manifest.json").exists()


@pytest.mark.asyncio
async def test_output_outside_local_reports_is_rejected(repair_request):
    repair_request = TargetFKRepairRequest(
        repair_request.repo_root,
        repair_request.source_directory,
        repair_request.repo_root / "data/output",
        repair_request.run_id,
        repair_request.started_at,
    )
    with pytest.raises(ValueError, match="reports/local"):
        await prepare_target_fk_repair(repair_request)


def test_all_sink_csv_and_dq_paths_are_rebound_before_factory(tmp_path):
    config = load_pipeline_config("chembl_target")
    original_path = config.sink["silver"].path
    root = tmp_path / "isolated-data"
    isolated = isolate_recovery_config(config, root)
    settings = Settings(test_mode=True, data_dir=root, _env_file=None)
    _verify_isolated_paths(isolated, settings)
    assert config.sink["silver"].path == original_path
    assert isolated.sink["silver"].path != original_path
    assert Path(isolated.sink["silver"].dq_report.output_path).is_relative_to(root)


def test_sidecar_path_outside_isolation_is_rejected(tmp_path):
    root = tmp_path / "isolated-data"
    config = isolate_recovery_config(load_pipeline_config("chembl_target"), root)
    silver = config.sink["silver"]
    config = config.model_copy(
        update={
            "sink": {
                **config.sink,
                "silver": silver.model_copy(
                    update={
                        "dq_report": silver.dq_report.model_copy(
                            update={
                                "output_path": str(tmp_path / "protected-canonical")
                            }
                        )
                    }
                ),
            }
        }
    )
    settings = Settings(test_mode=True, data_dir=root, _env_file=None)
    with pytest.raises(ValueError, match="escapes isolated"):
        _verify_isolated_paths(config, settings)
