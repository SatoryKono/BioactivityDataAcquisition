"""Actual factories keep data and DQ writes in the same resolved deployment."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from pathlib import Path
from shutil import copyfile
from uuid import UUID

import pytest
from deltalake import DeltaTable

from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer
from bioetl.composition.factories.dq.context_resolver import extract_dq_output_paths
from bioetl.composition.factories.pipeline.assembler import create_pipeline_factory
from bioetl.composition.factories.pipeline.registry import chembl_target_factory
from bioetl.composition.factories.dq.composite_validation import (
    resolve_target_table_paths,
)
from bioetl.composition.runtime_builders.config_access import load_pipeline_config
from bioetl.domain.config import RuntimeConfig
from bioetl.domain.ports import PipelineCreateRunnerRequest
from bioetl.domain.types import HealthStatus, RunType
from bioetl.infrastructure.config.settings_api import Settings
from bioetl.infrastructure.config.config_root import resolve_configs_root
from bioetl.infrastructure.config.contract_policy_loader import (
    load_pipeline_contract_policy,
)
from tests.helpers.clock import FIXED_TEST_TIME
from tests.helpers.iuphar_snapshot import synthetic_snapshot_bundle
from tests.integration.pipelines.observability import build_test_observability_bundle

pytestmark = pytest.mark.unit


@pytest.fixture
def isolated_working_directory(tmp_path: Path) -> Iterator[Path]:
    """Supply real policy inputs to the cwd-based loader with a cold cache."""
    working_directory = tmp_path / "canonical-working-directory"
    working_directory.mkdir()
    configs_root = resolve_configs_root()
    for relative in (
        "base/pipeline.yaml",
        "base/contract_registry.yaml",
        "entities/chembl/target.yaml",
    ):
        destination = working_directory / "configs" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        copyfile(configs_root / relative, destination)
    load_pipeline_contract_policy.cache_clear()
    try:
        yield working_directory
    finally:
        load_pipeline_contract_policy.cache_clear()


def _hashes(paths):
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


class _Source:
    provider_name = "chembl"

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def aclose(self):
        pass

    async def health_check(self):
        return HealthStatus.HEALTHY

    async def fetch(self, entity_type, **kwargs):
        assert entity_type == "target"
        yield {
            "target_chembl_id": "CHEMBL1",
            "target_type": "SINGLE PROTEIN",
            "pref_name": "known enzyme",
            "tax_id": 9606,
            "organism": "Homo sapiens",
            "species_group_flag": False,
            "target_components": [
                {
                    "accession": "P12345",
                    "component_id": 1,
                    "component_type": "PROTEIN",
                    "relationship": "SINGLE PROTEIN",
                    "target_component_synonyms": [],
                    "target_component_xrefs": [],
                }
            ],
        }


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["enrich", "shadow"])
async def test_real_factory_preserves_canonical_dq_and_writes_isolated_data_and_reports(
    tmp_path, monkeypatch, mode, isolated_working_directory
):
    config = load_pipeline_config("chembl_target")
    if mode == "shadow":
        output, bundle = synthetic_snapshot_bundle(tmp_path / "reference-fixture")
        config = config.model_copy(
            update={
                "target_classification": config.target_classification.model_copy(
                    update={
                        "mode": "shadow",
                        "table_contract": "3.0.0",
                        "snapshot_manifest": str(output / "profile.json"),
                        "snapshot_manifest_sha256": bundle.profile_sha256,
                    }
                )
            }
        )
    assert config.target_classification.mode == mode
    canonical = isolated_working_directory
    sentinels = []
    for layer in ("bronze", "silver", "gold"):
        report = (
            canonical
            / f"data/output/{layer}/chembl/target/{layer}_chembl_target_dq_report.json"
        )
        report.parent.mkdir(parents=True)
        report.write_bytes(b"Preserve every byte of the existing canonical report\n")
        sentinels.append(report)
    before = _hashes(sentinels)
    monkeypatch.chdir(canonical)
    settings = Settings(
        test_mode=True, data_dir=tmp_path / "isolated/data", _env_file=None
    )
    paths = extract_dq_output_paths(config, settings=settings)
    assert all(
        Path(path).is_relative_to(settings.data_dir)
        for path in (paths.bronze_path, paths.silver_path, paths.gold_path)
    )
    source = _Source()
    factory = create_pipeline_factory(
        "chembl_target",
        chembl_target_factory.pipeline_class,
        "chembl",
        silver_schema=chembl_target_factory.silver_schema,
        gold_schema=chembl_target_factory.gold_schema,
        pandera_silver_schema=chembl_target_factory.pandera_silver_schema,
        transformer_class=TargetTransformer,
        data_source_creator=lambda *_args, **_kwargs: source,
    )
    runner = factory.create_runner(
        PipelineCreateRunnerRequest(
            run_id=UUID("00000000-0000-4000-8000-0000000000a1"),
            started_at=FIXED_TEST_TIME,
            runtime=RuntimeConfig(
                run_type=RunType.INCREMENTAL, limit=1, strict_validation=True
            ),
            settings=settings,
            config=config,
            observability=build_test_observability_bundle(),
        )
    )
    await runner.run()
    assert (
        runner.execution_metrics["records_silver"]
        == runner.execution_metrics["records_gold"]
        == 1
    )
    assert _hashes(sentinels) == before
    for layer in ("silver", "gold"):
        table = settings.data_dir / f"output/{layer}/chembl/target"
        assert DeltaTable(table).to_pyarrow_table().num_rows == 1
    for layer in ("bronze", "silver", "gold"):
        assert (
            settings.data_dir
            / f"output/{layer}/chembl/target/{layer}_chembl_target_dq_report.json"
        ).is_file()


@pytest.mark.parametrize("test_mode", [False, True])
def test_dq_paths_follow_the_actual_writer_roots_and_layout(tmp_path, test_mode):
    config = load_pipeline_config("chembl_target")
    settings = Settings(
        test_mode=test_mode, data_dir=tmp_path / "runtime-data", _env_file=None
    )
    paths = extract_dq_output_paths(config, settings=settings)
    silver, gold = resolve_target_table_paths(settings, config)
    assert Path(paths.silver_path) == silver
    assert Path(paths.gold_path) == gold
    assert Path(paths.bronze_path) == settings.bronze_path / "chembl/target"
    assert paths.flat_structure


def test_normal_production_custom_flat_sink_is_preserved(tmp_path):
    config = load_pipeline_config("chembl_target")
    gold = config.sink["gold"].model_copy(
        update={"path": str(tmp_path / "custom-dataset"), "flat_structure": True}
    )
    config = config.model_copy(update={"sink": {**config.sink, "gold": gold}})
    settings = Settings(
        test_mode=False, data_dir=tmp_path / "runtime-data", _env_file=None
    )
    assert (
        Path(extract_dq_output_paths(config, settings=settings).gold_path)
        == tmp_path / "custom-dataset"
    )


def test_legacy_extraction_without_settings_preserves_original_api():
    config = load_pipeline_config("chembl_target")
    paths = extract_dq_output_paths(config)
    assert paths.bronze_path == config.sink["bronze"].path
    assert paths.silver_path == config.sink["silver"].path
    assert paths.gold_path == config.sink["gold"].path
