"""Runner-builder artifact recorder wiring contract."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from bioetl.composition.runtime_builders.runner_builder_wiring import (
    LegacyRunnerBuilderOverrides,
    resolve_runner_builder_wiring,
)
from tests.unit.composition.runtime_builders.runner_builder_test_support import (
    SILVER_METADATA_PATH,
    SILVER_OUTPUT_PATH,
    _FakeFactory,
    _FakeRegistry,
    _RecorderAwareMetadataWriter,
    _build_context,
    _clean_provenance_context_if_unpatched,
    _ensure_default_cached_bronze_fixture,
    _namespace_observability,
    runner_builder,
)


pytestmark = pytest.mark.unit


def test_build_pipeline_runner_attaches_artifact_recorder_to_metadata_writers(
    tmp_path: Path,
) -> None:
    fake_factory = _FakeFactory()
    fake_registry = _FakeRegistry(factory=fake_factory)
    top_writer = _RecorderAwareMetadataWriter()
    bronze_writer = _RecorderAwareMetadataWriter()
    silver_writer = _RecorderAwareMetadataWriter()
    gold_writer = _RecorderAwareMetadataWriter()
    fake_factory.runner.services = SimpleNamespace(
        metadata_writer=top_writer,
        storage=SimpleNamespace(
            bronze=SimpleNamespace(_metadata_writer=bronze_writer),
            silver=SimpleNamespace(_metadata_writer=silver_writer),
            gold=SimpleNamespace(_metadata_writer=gold_writer),
        ),
    )
    context = _build_context(limit=25)

    with _clean_provenance_context_if_unpatched():
        runner_builder.build_pipeline_runner(
            context,
            registry=fake_registry,
            wiring=resolve_runner_builder_wiring(
                legacy_overrides=LegacyRunnerBuilderOverrides(
                    ensure_providers_loaded_fn=lambda: None,
                    register_all_pipelines_fn=lambda registry=None: None,
                    get_settings_fn=cast(Any, lambda: SimpleNamespace(
                        data_dir=str(tmp_path),
                        pipeline=SimpleNamespace(
                            heartbeat_interval=30,
                            control_plane=SimpleNamespace(
                                required_persistence_profile="degraded_observable",
                                checkpoint_compatibility_policy="hard_fail",
                                run_manifest_enabled=True,
                                run_ledger_enabled=True,
                            ),
                        ),
                        test_mode=False,
                    )),
                    load_pipeline_config_fn=cast(Any, lambda _: SimpleNamespace(
                        provider="chembl",
                        entity_type="activity",
                        version="2.0.0",
                        maintenance=None,
                        input_filter=SimpleNamespace(),
                        business_primary_keys=["activity_id"],
                        technical_primary_key="entity_id",
                        sink={
                            "bronze": SimpleNamespace(enabled=True, save_metadata=True),
                            "silver": SimpleNamespace(enabled=True, save_metadata=True),
                            "gold": SimpleNamespace(enabled=True, save_metadata=True),
                        },
                    )),
                    build_observability_bundle_fn=lambda **_: _namespace_observability(
                        SimpleNamespace(info=lambda *_, **__: None),
                    ),
                    assemble_vacuum_settings_fn=cast(Any, lambda **_: None),
                    assemble_runtime_config_fn=cast(
                        Any, lambda **_: SimpleNamespace(run_type="incremental")
                    ),
                    assemble_filter_config_fn=lambda **_: None,
                    assemble_cached_bronze_context_fn=lambda _: (
                        _ensure_default_cached_bronze_fixture(
                            settings=SimpleNamespace(
                                data_dir=str(tmp_path),
                                pipeline=SimpleNamespace(
                                    heartbeat_interval=30,
                                    control_plane=SimpleNamespace(
                                        required_persistence_profile=(
                                            "degraded_observable"
                                        ),
                                        checkpoint_compatibility_policy="hard_fail",
                                        run_manifest_enabled=True,
                                        run_ledger_enabled=True,
                                    ),
                                ),
                                test_mode=False,
                            ),
                            pipeline_config=SimpleNamespace(
                                provider="chembl",
                                entity_type="activity",
                            ),
                        )
                    ),
                )
            ),
        )

    for writer in (top_writer, bronze_writer, silver_writer, gold_writer):
        assert writer.recorder is not None
    manifest_id = fake_factory.kwargs["manifest_id"]
    assert isinstance(manifest_id, str)
    silver_writer.recorder(
        "silver",
        SILVER_OUTPUT_PATH,
        {
            "metadata_path": SILVER_METADATA_PATH,
            "artifact_content_hash": "sha256:silver-artifact",
            "dataset_ref": "silver:chembl.activity@1",
            "lineage_fragment_id": "silver:fragment-1",
        },
    )
    ledger_path = (
        tmp_path / "output" / "control" / "run_ledger" / f"{manifest_id}.jsonl"
    )
    ledger_payload = json.loads(ledger_path.read_text(encoding="utf-8").splitlines()[1])
    assert ledger_payload["event_type"] == "artifact_published"
    assert ledger_payload["stage"] == "silver"
    assert (
        ledger_payload["details"]["artifact_content_hash"] == "sha256:silver-artifact"
    )
    assert ledger_payload["dataset_ref"] == "silver:chembl.activity@1"
    assert ledger_payload["lineage_fragment_id"] == "silver:fragment-1"
