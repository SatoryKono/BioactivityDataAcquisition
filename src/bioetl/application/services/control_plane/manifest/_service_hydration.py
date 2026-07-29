# pyright: reportUninitializedInstanceVariable=false
# Host attrs/methods provided by concrete composition.
"""Hydration helpers for typed control-plane objects from manifest payloads."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, cast

from bioetl.application.services.control_plane.manifest._reference_hydration import (
    hydrate_input_snapshots,
    hydrate_planned_artifacts,
    hydrate_source_refs,
)
from bioetl.domain.control_plane import (
    RunArtifactRef,
    RunCodeProvenance,
    RunInputSnapshotRef,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.types import RunType

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.manifest.models import (
        RunManifestCreateSpec,
    )


def _optional_payload_string(
    payload: dict[str, object],
    key: str,
) -> str | None:
    value = payload.get(key)
    return None if value is None else str(value)


class RunManifestHydrationMixin:
    """Hydrate typed control-plane objects from normalized manifest payloads."""

    _manifest_id_factory: Callable[[], str]
    schema_version: str

    def _hydrate_code_provenance(
        self,
        payload: dict[str, object],
    ) -> RunCodeProvenance:
        return RunCodeProvenance(
            pipeline_version=_optional_payload_string(payload, "pipeline_version"),
            git_commit=_optional_payload_string(payload, "git_commit"),
            source_revision_state=_optional_payload_string(
                payload,
                "source_revision_state",
            ),
            dependency_lock_hash=_optional_payload_string(
                payload,
                "dependency_lock_hash",
            ),
            config_hash=_optional_payload_string(payload, "config_hash"),
            resolved_config_hash=_optional_payload_string(
                payload,
                "resolved_config_hash",
            ),
            effective_config_hash=_optional_payload_string(
                payload,
                "effective_config_hash",
            ),
            source_fingerprint=_optional_payload_string(
                payload,
                "source_fingerprint",
            ),
            contract_ref=_optional_payload_string(payload, "contract_ref"),
            contract_version=_optional_payload_string(payload, "contract_version"),
            contract_schema_hash=_optional_payload_string(
                payload,
                "contract_schema_hash",
            ),
            dq_policy_ref=_optional_payload_string(payload, "dq_policy_ref"),
            rule_bundle_version=_optional_payload_string(
                payload,
                "rule_bundle_version",
            ),
            normalization_profile_ref=_optional_payload_string(
                payload,
                "normalization_profile_ref",
            ),
            normalization_profile_version=_optional_payload_string(
                payload,
                "normalization_profile_version",
            ),
            normalization_profile_hash=_optional_payload_string(
                payload,
                "normalization_profile_hash",
            ),
            dq_contract_compatibility_hash=_optional_payload_string(
                payload,
                "dq_contract_compatibility_hash",
            ),
            effective_config_artifact_id=_optional_payload_string(
                payload,
                "effective_config_artifact_id",
            ),
        )

    def _hydrate_source_refs(
        self,
        payload: list[object],
    ) -> tuple[RunSourceRef, ...]:
        return hydrate_source_refs(payload)

    def _hydrate_input_snapshots(
        self,
        payload: list[object],
        *,
        context: str = "input_snapshots",
    ) -> tuple[RunInputSnapshotRef, ...]:
        return hydrate_input_snapshots(payload, context=context)

    def _hydrate_planned_artifacts(
        self,
        payload: list[object],
    ) -> tuple[RunArtifactRef, ...]:
        return hydrate_planned_artifacts(payload)

    def _build_manifest(
        self,
        *,
        request: RunManifestCreateSpec,
        run_type: RunType,
        created_at: datetime,
        normalized_payload: dict[str, object],
        fingerprint: str,
    ) -> RunManifest:
        code_provenance_payload = cast(
            dict[str, object],
            normalized_payload["code_provenance"],
        )
        return RunManifest(
            manifest_id=self._manifest_id_factory(),
            execution_fingerprint=fingerprint,
            schema_version=self.schema_version,
            created_at=created_at,
            run_id=request.run_id,
            run_type=run_type,
            pipeline_name=request.pipeline_name,
            provider=request.provider,
            entity=request.entity,
            workflow_run_id=_optional_payload_string(
                normalized_payload, "workflow_run_id"
            ),
            workflow_name=_optional_payload_string(normalized_payload, "workflow_name"),
            workflow_step_id=_optional_payload_string(
                normalized_payload, "workflow_step_id"
            ),
            launch_context=cast(
                dict[str, object],
                normalized_payload["launch_context"],
            ),
            runtime_config=cast(
                dict[str, object],
                normalized_payload["runtime_config"],
            ),
            resolved_config=cast(
                dict[str, object],
                normalized_payload["resolved_config"],
            ),
            code_provenance=self._hydrate_code_provenance(code_provenance_payload),
            replay_of_run_id=_optional_payload_string(
                normalized_payload,
                "replay_of_run_id",
            ),
            replay_of_manifest_id=_optional_payload_string(
                normalized_payload,
                "replay_of_manifest_id",
            ),
            replay_capability=request.replay_capability,
            source_refs=self._hydrate_source_refs(
                cast(list[object], normalized_payload.get("source_refs", []))
            ),
            planned_artifacts=self._hydrate_planned_artifacts(
                cast(list[object], normalized_payload.get("planned_artifacts", []))
            ),
        )


__all__ = ["RunManifestHydrationMixin"]
