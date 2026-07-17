"""Private helpers for run-manifest creation orchestration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

import bioetl.composition.runtime_builders.run_manifest_support as _manifest_support
from bioetl.application.services.control_plane.manifest.service import (
    RunManifestCreateSpec,
)
from bioetl.composition.runtime_builders._run_manifest_attr_support import (
    read_attr as _read_attr,
)
from bioetl.composition.runtime_builders._run_manifest_creation_support_helpers import (
    RunManifestCreateRequestInputs,
)
from bioetl.composition.runtime_builders._run_manifest_creation_support_helpers import (
    assemble_manifest_create_spec as _assemble_manifest_create_spec,
)
from bioetl.composition.runtime_builders._run_manifest_creation_support_helpers import (
    build_manifest_source_refs as _build_manifest_source_refs,
)
from bioetl.composition.runtime_builders._run_manifest_creation_support_helpers import (
    create_ledger_service as _create_ledger_service,
)
from bioetl.composition.runtime_builders._run_manifest_builder_policy import (
    resolve_code_revision_for_manifest,
    validate_required_runtime_persistence_profile,
)
from bioetl.composition.runtime_builders._run_manifest_replay_support import (
    apply_replay_assessment as _apply_replay_assessment,
)
from bioetl.composition.runtime_builders._run_manifest_replay_support import (
    build_manifest_launch_context as _build_manifest_launch_context,
)
from bioetl.composition.runtime_builders._run_manifest_replay_support import (
    build_replay_assessment as _build_replay_assessment,
)
from bioetl.composition.runtime_builders._run_manifest_replay_support import (
    validate_exact_replay_boundary as _validate_exact_replay_boundary,
)
from bioetl.domain.control_plane import ReplayCapability
from bioetl.domain.control_plane.reproducibility_policy import (
    DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
    STRICT_PERSISTENCE_PROFILES,
)

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.ledger.service import (
        RunLedgerService,
    )
    from bioetl.composition.runtime_builders.runner_inputs import RunnerInputs
    from bioetl.domain.context import PipelineRunContext

_RunManifestCreateRequestInputs = RunManifestCreateRequestInputs


def build_manifest_create_request(
    request_inputs: RunManifestCreateRequestInputs,
) -> RunManifestCreateSpec:
    """Build the canonical RunManifest create request."""
    ctx = request_inputs.ctx
    inputs = request_inputs.inputs
    reproducibility_context = request_inputs.reproducibility_context
    _validate_exact_replay_boundary(ctx, reproducibility_context)
    source_refs = _build_manifest_source_refs(
        manifest_support=_manifest_support,
        ctx=ctx,
        inputs=inputs,
        provider=request_inputs.provider,
        entity=request_inputs.entity,
        required_persistence_profile=(
            reproducibility_context.required_persistence_profile
        ),
    )
    replay_of_run_id, replay_of_manifest_id = (
        _manifest_support.resolve_replay_parentage(
            ctx=ctx,
            runtime_config=inputs.runtime_config,
        )
    )
    replay_capability = _manifest_support.resolve_replay_capability(
        source_refs=source_refs,
        resume_requested=bool(_read_attr(ctx, "resume", False)),
    )
    launch_context = _build_manifest_launch_context(
        manifest_support=_manifest_support,
        request_inputs=request_inputs,
        reproducibility_context=reproducibility_context,
    )
    replay_assessment = _build_replay_assessment(
        request_inputs=request_inputs,
        reproducibility_context=reproducibility_context,
        source_refs=source_refs,
        replay_capability=replay_capability,
    )
    _apply_replay_assessment(launch_context, replay_assessment)
    request = _assemble_manifest_create_spec(
        request_inputs=request_inputs,
        source_refs=source_refs,
        replay_of_run_id=replay_of_run_id,
        replay_of_manifest_id=replay_of_manifest_id,
        code_revision=resolve_code_revision_for_manifest(
            resolved_config_hash=request_inputs.resolved_config_hash,
            test_mode=bool(_read_attr(inputs.settings, "test_mode", False)),
        ),
        replay_capability=replay_capability,
        launch_context=launch_context,
    )
    validate_required_runtime_persistence_profile(
        request=request,
        required_persistence_profile=(
            reproducibility_context.required_persistence_profile
        ),
        strict_exact_replay_supported=(
            reproducibility_context.strict_exact_replay_supported
        ),
    )
    return request


def emit_replay_reconstructability_metric(
    *,
    request: RunManifestCreateSpec,
    strict_exact_replay_supported: bool,
    metrics: object,
) -> None:
    """Emit replay reconstructability metrics for one manifest request."""
    increment_counter = _read_attr(metrics, "increment_counter", None)
    if not callable(increment_counter):
        return
    set_gauge = _read_attr(metrics, "set_gauge", None)
    launch_context = request.launch_context
    strict_replay_requested = bool(
        launch_context.get("exact_replay", False)
        if isinstance(launch_context, Mapping)
        else _read_attr(launch_context, "exact_replay", False)
    )
    required_persistence_profile = str(
        (
            launch_context.get("required_persistence_profile")
            if isinstance(launch_context, Mapping)
            else _read_attr(launch_context, "required_persistence_profile")
        )
        or DEFAULT_REQUIRED_PERSISTENCE_PROFILE
    )
    strict_requirement = (
        strict_replay_requested
        or required_persistence_profile in STRICT_PERSISTENCE_PROFILES
    )
    status = "reconstructable"
    if strict_requirement and (
        not strict_exact_replay_supported
        or request.replay_capability != ReplayCapability.EXACT_REPLAY_SUPPORTED
    ):
        status = "not_reconstructable"
    raw_run_type = _read_attr(request.run_type, "value", request.run_type)
    run_type = str(raw_run_type or "unknown").strip().lower().replace(" ", "_")
    bounded_run_type = run_type or "unknown"
    increment_counter(
        "bioetl_replay_reconstructability_events_total",
        value=1,
        labels={
            "pipeline": request.pipeline_name,
            "replay_capability": request.replay_capability.value,
            "strict_requirement": "true" if strict_requirement else "false",
            "status": status,
        },
    )
    lag_status = "not_requested"
    if status == "not_reconstructable":
        lag_status = "blocked"
    elif strict_replay_requested:
        lag_status = "ready"
    replay_labels = {
        "pipeline": request.pipeline_name,
        "run_type": bounded_run_type,
        "replay_capability": request.replay_capability.value,
    }
    if callable(set_gauge):
        set_gauge(
            "bioetl_replay_lag_seconds",
            value=0.0,
            labels={**replay_labels, "status": lag_status},
        )
    if status == "not_reconstructable":
        increment_counter(
            "bioetl_replay_drift_events_total",
            value=1,
            labels={
                **replay_labels,
                "drift_type": "strict_replay_not_reconstructable",
                "status": "detected",
            },
        )


def create_ledger_service(
    inputs: RunnerInputs,
    ctx: PipelineRunContext,
) -> RunLedgerService | None:
    """Keep the public ownership seam local to this support module."""
    return _create_ledger_service(inputs, ctx)
