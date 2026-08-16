# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Private manifest-service support helpers owned by the manifest package."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.services.control_plane.manifest._service_hydration import (
    RunManifestHydrationMixin as RunManifestHydrationMixin,
)
from bioetl.application.services.control_plane.manifest.execution_identity_support import (
    build_code_provenance_dict,
)
from bioetl.application.services.control_plane.manifest.execution_identity_support import (
    build_degraded_runtime_anchor_payload as build_degraded_runtime_anchor_payload,
)
from bioetl.application.services.control_plane.manifest.execution_identity_support import (
    build_execution_identity_payload_from_code_provenance as build_execution_identity_payload_from_code_provenance,
)
from bioetl.application.services.control_plane.manifest.execution_identity_support import (
    build_identity_graph_core as build_identity_graph_core,
)
from bioetl.application.services.control_plane.manifest.snapshot_payloads import (
    source_refs_payload,
)
from bioetl.domain.config.runtime import CANONICAL_SILVER_FILTER_COMPATIBILITY_MODE
from bioetl.domain.control_plane import RunCodeProvenance
from bioetl.domain.normalization import compute_input_snapshot_identity_fingerprint
from bioetl.domain.types import RunType

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.manifest.models import (
        RunManifestCreateSpec,
    )


class RunManifestPayloadMixin:
    """Build normalized manifest payloads and canonical identity anchors."""

    schema_version: str = cast(Any, None)  # Any: host attr default (PD5)

    def _build_execution_identity_payload(
        self,
        *,
        request: RunManifestCreateSpec,
        code_provenance: RunCodeProvenance,
        run_type: RunType,
    ) -> dict[str, object]:
        snapshots = [
            snapshot
            for source_ref in request.source_refs
            for snapshot in source_ref.input_snapshots
        ]
        return build_execution_identity_payload_from_code_provenance(
            pipeline_name=request.pipeline_name,
            run_type=run_type.value,
            code_provenance=code_provenance,
            exact_replay=bool(request.launch_context.get("exact_replay")),
            input_snapshot_fingerprint=compute_input_snapshot_identity_fingerprint(
                snapshots
            ),
            silver_filter_compatibility_mode=str(
                request.runtime_config.get(
                    "silver_filter_compatibility_mode",
                    CANONICAL_SILVER_FILTER_COMPATIBILITY_MODE,
                )
            ),
        )

    def _build_manifest_payload(
        self,
        *,
        request: RunManifestCreateSpec,
        code_provenance: RunCodeProvenance,
        run_type: RunType,
    ) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "run_type": str(run_type.value),
            "pipeline_name": request.pipeline_name,
            "provider": request.provider,
            "entity": request.entity,
            "workflow_run_id": request.workflow_run_id,
            "workflow_name": request.workflow_name,
            "workflow_step_id": request.workflow_step_id,
            "launch_context": request.launch_context,
            "runtime_config": request.runtime_config,
            "resolved_config": request.resolved_config,
            "replay_of_run_id": request.replay_of_run_id,
            "replay_of_manifest_id": request.replay_of_manifest_id,
            "replay_capability": request.replay_capability.value,
            "code_provenance": build_code_provenance_dict(
                code_provenance,
                include_execution_anchors=True,
            ),
            "source_refs": source_refs_payload(request.source_refs),
            "planned_artifacts": [
                {"layer": item.layer, "path": item.path}
                for item in request.planned_artifacts
            ],
        }
