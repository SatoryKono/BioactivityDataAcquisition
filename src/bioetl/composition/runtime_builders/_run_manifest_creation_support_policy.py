"""Support helpers for run-manifest request creation and replay metric emission."""

from __future__ import annotations

from dataclasses import dataclass

import bioetl.composition.runtime_builders.run_manifest_support as _manifest_support
from bioetl.application.services.control_plane.ledger.service import (
    RunLedgerService,
)
from bioetl.composition.runtime_builders._run_manifest_attr_support import (
    read_attr as _read_attr,
)
from bioetl.composition.runtime_builders.run_manifest_contract_identity import (
    RunManifestContractIdentity,
)
from bioetl.domain.control_plane import ReplayCapability
from bioetl.domain.control_plane.reproducibility_policy import assess_reproducibility_policy


@dataclass(frozen=True, slots=True)
class _RunManifestCreateRequestInputs:
    ctx: object
    inputs: object
    provider: str
    entity: str
    reproducibility_context: object
    run_type_value: str
    execution_context_value: str
    config_hash: str
    resolved_config_hash: str
    effective_config_hash: str
    source_fingerprint: str | None
    contract_identity: RunManifestContractIdentity
    dq_contract_compatibility_hash: str
    effective_config_artifact_id: str


def _validate_exact_replay_boundary(ctx: object, context: object) -> None:
    if not bool(_read_attr(ctx, "exact_replay", False)):
        return
    if bool(_read_attr(context, "strict_exact_replay_supported", False)):
        return
    raise RuntimeError(
        "Pipeline execution is outside the published strict exact-replay "
        "support boundary for this run family"
    )


def build_manifest_source_refs(
    *,
    ctx: object,
    inputs: object,
    provider: str,
    entity: str,
    required_persistence_profile: str,
) -> tuple[object, ...]:
    return _manifest_support.build_run_source_refs(
        ctx=ctx,
        cached_bronze=inputs.cached_bronze,
        settings=inputs.settings,
        provider=provider,
        entity=entity,
        required_persistence_profile=required_persistence_profile,
    )


def build_manifest_launch_context(
    *,
    request_inputs: _RunManifestCreateRequestInputs,
    reproducibility_context: object,
) -> dict[str, object]:
    return _manifest_support.build_launch_context_snapshot(
        request_inputs.ctx,
        run_type_value=request_inputs.run_type_value,
        execution_context_value=request_inputs.execution_context_value,
        configured_required_persistence_profile=_read_attr(
            reproducibility_context, "configured_required_persistence_profile"
        ),
        required_persistence_profile=_read_attr(
            reproducibility_context, "required_persistence_profile"
        ),
        required_persistence_profile_opt_down=bool(
            _read_attr(
                reproducibility_context,
                "required_persistence_profile_opt_down",
                False,
            )
        ),
        strict_exact_replay_supported=_read_attr(
            reproducibility_context, "strict_exact_replay_supported"
        ),
        reproducibility_family=_read_attr(reproducibility_context, "family"),
        replay_family_contract=_read_attr(
            reproducibility_context, "replay_family_contract"
        ),
        strict_replay_runtime_verdict=_read_attr(
            reproducibility_context, "strict_replay_runtime_verdict"
        ),
        replay_support_scope=_read_attr(reproducibility_context, "support_scope"),
        replay_support_reason=_read_attr(reproducibility_context, "reason"),
    )


def build_replay_assessment(
    *,
    request_inputs: _RunManifestCreateRequestInputs,
    reproducibility_context: object,
    source_refs: tuple[object, ...],
    replay_capability: ReplayCapability,
) -> object:
    return assess_reproducibility_policy(
        source_refs=source_refs,
        required_persistence_profile=_read_attr(
            reproducibility_context, "required_persistence_profile"
        ),
        strict_exact_replay_supported=_read_attr(
            reproducibility_context, "strict_exact_replay_supported"
        ),
        exact_replay_requested=bool(_read_attr(request_inputs.ctx, "exact_replay", False)),
        resume_requested=bool(_read_attr(request_inputs.ctx, "resume", False)),
        replay_capability=replay_capability,
        run_type=request_inputs.run_type_value,
        debug_only=bool(_read_attr(request_inputs.inputs.settings, "debug", False)),
    )


def apply_replay_assessment(
    launch_context: dict[str, object],
    replay_assessment: object,
) -> None:
    replay_verdict = _read_attr(replay_assessment, "replay_readiness_verdict").value
    launch_context.update(
        {
            "replay_readiness_verdict": replay_verdict,
            "exact_replay_ready": replay_verdict == "exact_replay_ready",
            "replay_blockers": list(_read_attr(replay_assessment, "blocking_gaps")),
        }
    )


def create_ledger_service(
    inputs: object,
    ctx: object,
) -> RunLedgerService | None:
    """Build the optional run-ledger service for manifest publication."""
    from bioetl.composition.control_plane_store_builders import create_run_ledger_store
    from bioetl.composition.occurrence_identity import create_runtime_occurrence_id

    return RunLedgerService(
        ledger_port=create_run_ledger_store(
            settings=inputs.settings,
            metrics=inputs.observability.metrics,
        ),
        manifest_id="pending",
        run_id=ctx.run_id,
        _entry_id_factory=lambda: create_runtime_occurrence_id("run_ledger_entry"),
    )


def emit_replay_reconstructability_metric(
    *,
    request: object,
    strict_exact_replay_supported: bool,
    metrics: object,
) -> None:
    """Backward-compatible shim kept for historical imports.

    Runtime metric emission now lives in
    ``_run_manifest_creation_support.py`` to satisfy ownership checks that expect
    runtime emission code to be co-located in the orchestration support layer.
    """
    from importlib import import_module

    emit_replay_reconstructability_metric_impl = import_module(
        "bioetl.composition.runtime_builders._run_manifest_creation_support"
    ).emit_replay_reconstructability_metric
    emit_replay_reconstructability_metric_impl(
        request=request,
        strict_exact_replay_supported=strict_exact_replay_supported,
        metrics=metrics,
    )
