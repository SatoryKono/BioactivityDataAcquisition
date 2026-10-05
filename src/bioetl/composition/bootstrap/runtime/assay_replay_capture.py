"""Assemble offline assay merge replay using the production storage writers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import replace
from pathlib import Path
from uuid import UUID
from typing import override


from bioetl.application.composite.merger_orchestration import (
    MergeExecutionRequest,
)
from bioetl.composition.factories.storage import StorageBundle
from bioetl.domain.composite import CompositeConfig
from bioetl.domain.composite.field_groups import FieldGroupRegistry
from bioetl.domain.composite.result import (
    MergeResult,
)
from bioetl.domain.ports import DeltaReaderPort, LoggerPort
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config.settings_api import Settings
from bioetl.infrastructure.storage.composite_replay_bundle import (
    digest_bytes,
    implementation_fingerprint,
    publish_bytes,
    publish_json,
    publish_table,
)
from bioetl.infrastructure.storage.composite_replay_inputs import (
    CompositeInputCapture,
)
from bioetl.infrastructure.storage.delta_reader import DeltaReader
from bioetl.infrastructure.time import SystemClock
from bioetl.composition.bootstrap.runtime.assay_replay import replay_assay
from bioetl.application.composite.helpers.replay_context import (
    freeze_field_groups,
    freeze_merge_request,
    freeze_target_mapping,
    required_replay_tables,
    output_table_name,
)


_DEPENDENCY_LOCK_FILE = "uv.lock"
MergeExecutor = Callable[[MergeExecutionRequest], Awaitable[MergeResult]]
MergeHook = Callable[[MergeExecutionRequest, MergeExecutor], Awaitable[MergeResult]]


class RequestReader(DeltaReaderPort):
    def __init__(self, captures: dict[str, CompositeInputCapture]) -> None:
        self._captures = captures

    async def read_table(
        self,
        table_path: str,
        columns: list[str] | None = None,
        limit: int | None = None,
    ) -> object:
        return await self._captures["active"].read_table(table_path, columns, limit)

    async def get_schema(self, table_path: str) -> object:
        return await self._captures["active"].get_schema(table_path)

    async def get_row_count(self, table_path: str) -> int:
        return await self._captures["active"].get_row_count(table_path)

    async def table_exists(self, table_path: str) -> bool:
        return await self._captures["active"].table_exists(table_path)

    @override
    async def aclose(self) -> None:
        return None


def prepare_assay_replay(
    *,
    config: CompositeConfig,
    reader: DeltaReaderPort,
    storage: StorageBundle,
    settings: Settings,
    logger: LoggerPort,
    field_group_registry: FieldGroupRegistry | None = None,
) -> tuple[DeltaReaderPort, MergeHook]:
    """Capture inputs at the merge boundary; publish proof only after offline replay."""
    if settings.report_root is None:
        raise ValueError("assay_replay_requires_report_root")
    report_root = settings.report_root
    # The capture directory is selected when the canonical request supplies its ID.
    captures: dict[str, CompositeInputCapture] = {}

    async def execute(
        request: MergeExecutionRequest, merge: MergeExecutor
    ) -> MergeResult:
        if captures:
            raise ValueError("assay_replay_request_not_supported")
        run_id = str(UUID(request.run_id))
        root = report_root / "pipeline" / config.name / run_id / "replay"
        root.mkdir(parents=True, exist_ok=False)
        capture = CompositeInputCapture(root / "inputs", reader)
        captures["active"] = capture
        resolved = replace(
            request,
            metadata_timestamp=request.metadata_timestamp or SystemClock().now(),
        )
        result = await merge(resolved)
        input_hash = capture.seal(required_tables=required_replay_tables(resolved))
        objects = {
            path.relative_to(root).as_posix(): digest_bytes(path.read_bytes())
            for path in (root / "inputs").iterdir()
        }
        objects["config.json"] = publish_json(root, "config.json", config.to_dict())
        objects[_DEPENDENCY_LOCK_FILE] = publish_bytes(
            root, _DEPENDENCY_LOCK_FILE, Path(_DEPENDENCY_LOCK_FILE).read_bytes()
        )
        objects["pipeline-settings.json"] = publish_json(
            root, "pipeline-settings.json", settings.pipeline.model_dump(mode="json")
        )
        objects["field-groups.json"] = publish_json(
            root, "field-groups.json", freeze_field_groups(field_group_registry)
        )
        if config.name == "composite_target":
            objects["target-mapping.json"] = publish_json(
                root, "target-mapping.json", freeze_target_mapping()
            )
        output_reader = DeltaReader(Path(settings.data_dir) / "output", logger)
        for layer in ("silver", "gold"):
            table_name = output_table_name(
                getattr(config.merge, f"output_{layer}_path"), layer
            )
            path = storage.get_table_path(table_name, layer=layer)
            table = await output_reader.read_table(str(path))
            name = f"expected/{layer}.arrow"
            objects[name] = publish_table(root, name, table)
        envelope: JsonDict = {
            "version": "composite-parent-replay-v2",
            "pipeline": config.name,
            "run_id": run_id,
            "implementation": implementation_fingerprint(),
            "input_snapshot_fingerprint": input_hash,
            "objects": objects,
            "request": freeze_merge_request(resolved),
        }
        envelope_hash = publish_json(root, "parent.json", envelope)
        await replay_assay(root, envelope_hash, root / "verification", logger=logger)
        return result

    return RequestReader(captures), execute
