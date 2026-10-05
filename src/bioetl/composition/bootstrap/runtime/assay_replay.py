"""Execute ADR-062 offline assay replay through production storage writers."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID
from typing import cast


from bioetl.application.ports.storage import CompositeMergeStorageProtocol
from bioetl.application.services.run_reports.observations import (
    bind_run_observations,
    reset_run_observations,
)
from bioetl.application.composite.runtime_wiring_api import (
    JOIN_KEY_NORMALIZATION_POLICIES,
    EnrichmentCrossValidator,
)
from bioetl.composition.bootstrap.assembly.storage import bootstrap_storage_adapter
from bioetl.composition.bootstrap.runtime.composite_merge_service_builder import (
    build_composite_merge_service,
    SYSTEM_COLUMNS_TO_DROP,
)

from bioetl.domain.composite import CompositeConfig
from bioetl.domain.mapping.protein_class_target_type import (
    scoped_protein_class_target_type_mapping as mapping_scope,
)
from bioetl.domain.ports import LoggerPort
from bioetl.domain.ports.noop import NoOpMetrics, NoOpTracing
from bioetl.domain.types import JsonDict, RunID, RunType
from bioetl.domain.value_objects.run_context import RunContext
from bioetl.infrastructure.config.composite_config_api import (
    resolve_composite_gold_schema,
)
from bioetl.infrastructure.config.settings_api import Settings
import bioetl.infrastructure.config.protein_class_target_type_loader as mapping
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.composite_replay_bundle import (
    SUPPORTED_COMPOSITES,
    digest_bytes,
    load_verified_json,
    publish_json,
    verify_bundle,
)
from bioetl.infrastructure.storage.composite_replay_evidence import (
    verify_replay_outputs,
    verification_receipt,
)
from bioetl.infrastructure.storage.composite_replay_inputs import (
    CompositeReplayInputReader,
)
from bioetl.infrastructure.storage.delta_reader import DeltaReader
from bioetl.infrastructure.time import SystemClock
from bioetl.application.composite.helpers.replay_context import (
    output_table_name,
    restore_field_groups,
    restore_merge_request,
)


async def replay_assay(
    root: Path,
    envelope_hash: str,
    destination: Path,
    *,
    logger: LoggerPort | None = None,
) -> JsonDict:
    """Rebuild physical Silver/Gold offline, then compare their materialized tables."""
    logger = logger or NoOpLogger()
    envelope = verify_bundle(root, envelope_hash)
    objects = envelope["objects"]
    if digest_bytes(Path("uv.lock").read_bytes()) != objects["uv.lock"]:
        raise ValueError("assay_replay_dependency_lock_mismatch")
    with mapping_scope(
        mapping.restore_target_mapping(
            load_verified_json(
                root, "target-mapping.json", objects["target-mapping.json"]
            )
        )
        if envelope["pipeline"] == "composite_target"
        else None
    ):
        config = CompositeConfig.from_dict(
            load_verified_json(root, "config.json", objects["config.json"])
        )
        if (
            config.name not in SUPPORTED_COMPOSITES
            or config.name != envelope["pipeline"]
        ):
            raise ValueError("assay_replay_config_not_supported")
        if envelope["version"] == "assay-parent-replay-v1" and config.dependencies:
            raise ValueError("assay_replay_config_not_supported")
        reader = CompositeReplayInputReader(
            root / "inputs", envelope_sha256=envelope["input_snapshot_fingerprint"]
        )
        request = restore_merge_request(config, envelope["request"], envelope["run_id"])
        assert request.metadata_timestamp is not None
        destination.mkdir(parents=True, exist_ok=False)
        settings = Settings.model_validate(
            {
                "data_dir": destination,
                "pipeline": load_verified_json(
                    root, "pipeline-settings.json", objects["pipeline-settings.json"]
                ),
            }
        )
        storage = bootstrap_storage_adapter(
            run_context=RunContext(
                run_id=RunID(UUID(request.run_id)),
                run_type=RunType.REBUILD,
                started_at=request.metadata_timestamp,
                pipeline_name=config.name,
                provider="composite",
                entity=config.name.removeprefix("composite_"),
            ),
            logger=logger,
            metrics=NoOpMetrics(),
            tracing=NoOpTracing(),
            settings=settings,
        )
        observation_token = bind_run_observations()
        try:
            merger = build_composite_merge_service(
                config=config,
                storage=cast(CompositeMergeStorageProtocol, storage),
                resolve_gold_schema=resolve_composite_gold_schema,
                delta_reader=reader,
                field_group_registry=restore_field_groups(
                    load_verified_json(
                        root, "field-groups.json", objects["field-groups.json"]
                    )
                )
                if "field-groups.json" in objects
                else None,
                cross_validator=EnrichmentCrossValidator(
                    config=config.cross_validation, logger=logger
                )
                if config.cross_validation.enabled
                else None,
                logger=logger,
                system_columns_to_drop=SYSTEM_COLUMNS_TO_DROP,
                normalization_policies=JOIN_KEY_NORMALIZATION_POLICIES,
                clock=SystemClock(),
            )
            result = await merger.execute_request(request)
            output_reader = DeltaReader(destination / "output", logger)
            paths = {
                layer: storage.get_table_path(
                    output_table_name(
                        getattr(config.merge, f"output_{layer}_path"), layer
                    ),
                    layer=layer,
                )
                for layer in ("silver", "gold")
            }
            await verify_replay_outputs(root, output_reader, paths)
            receipt = verification_receipt(
                destination, envelope_hash, request.run_id, result.records_merged
            )
            publish_json(destination, "verification.json", receipt)
            return receipt
        finally:
            try:
                await storage.aclose()
            finally:
                reset_run_observations(observation_token)
