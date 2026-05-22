"""Control-plane ref helpers for manifest builders."""

from __future__ import annotations

import os
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from bioetl.domain.control_plane import RunArtifactRef

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.config._base import Settings


DataRootMode = Literal["explicit", "repo_default", "private_cache", "tmp"]


def legacy_config_hash_from_resolved_config_hash(
    resolved_config_hash: str | None,
) -> str | None:
    """Return the legacy manifest config-hash alias for older consumers."""
    return resolved_config_hash


def is_explicit_data_root_configured(settings: Settings) -> bool:
    """Return ``True`` when settings declare an explicit non-empty data root."""
    configured_root = getattr(settings, "data_dir", None)
    return bool(str(configured_root or "").strip())


def resolve_data_root_mode(settings: Settings) -> DataRootMode:
    """Classify which data-root strategy would be used in the current runtime."""
    if is_explicit_data_root_configured(settings):
        return "explicit"

    candidate = Path("data")
    try:
        candidate.mkdir(parents=True, exist_ok=True)
    except OSError:
        return _private_fallback_data_root_mode()
    if not os.access(candidate, os.W_OK):
        return _private_fallback_data_root_mode()
    return "repo_default"


def _resolve_data_root(settings: Settings) -> Path:
    """Resolve a writable data root for control-plane artifacts.

    Explicit `settings.data_dir` values are preserved. When no data directory is
    configured, try the conventional `data/` under the current working
    directory, but fall back to `/tmp/bioetl-data` if the checkout is mounted
    read-only in the current execution environment.
    """
    configured_root = getattr(settings, "data_dir", None)
    if configured_root:
        return Path(configured_root)

    candidate = Path("data")
    try:
        candidate.mkdir(parents=True, exist_ok=True)
    except OSError:
        return _private_fallback_data_root()
    if not os.access(candidate, os.W_OK):
        return _private_fallback_data_root()
    return candidate


def _private_fallback_data_root() -> Path:
    """Return a user-private fallback data root when the checkout is read-only."""
    preferred = Path.home() / ".cache" / "bioetl-data"
    try:
        return _prepare_private_runtime_dir(preferred)
    except OSError:
        runtime_user = getattr(os, "getuid", lambda: "user")()
        fallback = Path(tempfile.gettempdir()) / f"bioetl-data-{runtime_user}"
        return _prepare_private_runtime_dir(fallback)


def _private_fallback_data_root_mode() -> DataRootMode:
    """Classify which private fallback would be used when checkout is read-only."""
    preferred = Path.home() / ".cache" / "bioetl-data"
    try:
        _prepare_private_runtime_dir(preferred)
    except OSError:
        return "tmp"
    return "private_cache"


def _prepare_private_runtime_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    with suppress(OSError):
        path.chmod(0o700)
    return path


def build_planned_artifacts(
    *,
    settings: Settings,
    provider: str,
    entity: str,
) -> tuple[RunArtifactRef, ...]:
    """Capture planned layer roots for the manifest control-plane snapshot."""
    output_root = _resolve_data_root(settings) / "output"
    return (
        RunArtifactRef(
            layer="bronze", path=str(output_root / "bronze" / provider / entity)
        ),
        RunArtifactRef(
            layer="silver", path=str(output_root / "silver" / provider / entity)
        ),
        RunArtifactRef(
            layer="gold", path=str(output_root / "gold" / provider / entity)
        ),
    )


def control_plane_root(settings: Settings, leaf: str) -> Path:
    """Return the canonical control-plane output root for one leaf namespace."""
    return _resolve_data_root(settings) / "output" / "control" / leaf


@dataclass(frozen=True, slots=True)
class ManifestControlPlaneRefs:
    """Resolved control-plane references produced before factory runner wiring."""

    manifest_id: str
    execution_fingerprint: str | None
    config_hash: str | None
    resolved_config_hash: str | None
    effective_config_hash: str | None
    source_fingerprint: str | None
    dq_contract_compatibility_hash: str | None
    effective_config_artifact_id: str | None
    replay_of_run_id: str | None = None
    replay_of_manifest_id: str | None = None
    input_snapshot_fingerprint: str | None = None
    contract_ref: str | None = None
    contract_version: str | None = None
    contract_schema_hash: str | None = None
    dq_policy_ref: str | None = None
    rule_bundle_version: str | None = None
    normalization_profile_ref: str | None = None
    normalization_profile_version: str | None = None
    normalization_profile_hash: str | None = None
    required_persistence_profile: str | None = None


def resolve_run_context_values(
    ctx: PipelineRunContext,
) -> tuple[str, str]:
    """Resolve run type and execution context values from context."""
    raw_run_type = getattr(ctx, "run_type", "incremental")
    run_type_value = str(getattr(raw_run_type, "value", raw_run_type))
    raw_execution_context = getattr(ctx, "execution_context", "isolated")
    execution_context_value = str(
        getattr(raw_execution_context, "value", raw_execution_context)
    )
    return run_type_value, execution_context_value


def create_control_plane_refs(
    manifest_id: str,
    execution_fingerprint: str,
    resolved_config_hash: str,
    effective_config_hash: str,
    source_fingerprint: str | None,
    dq_contract_compatibility_hash: str,
    effective_config_artifact_id: str,
    replay_of_run_id: str | None,
    replay_of_manifest_id: str | None,
    input_snapshot_fingerprint: str | None,
    contract_ref: str,
    contract_version: str | None,
    contract_schema_hash: str | None,
    dq_policy_ref: str | None,
    rule_bundle_version: str | None,
    normalization_profile_ref: str | None,
    normalization_profile_version: str | None,
    normalization_profile_hash: str | None,
    required_persistence_profile: str | None,
) -> ManifestControlPlaneRefs:
    """Build the compact control-plane refs bundle returned to callers."""
    return ManifestControlPlaneRefs(
        manifest_id=manifest_id,
        execution_fingerprint=execution_fingerprint,
        config_hash=legacy_config_hash_from_resolved_config_hash(resolved_config_hash),
        resolved_config_hash=resolved_config_hash,
        effective_config_hash=effective_config_hash,
        source_fingerprint=source_fingerprint,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        effective_config_artifact_id=effective_config_artifact_id,
        replay_of_run_id=replay_of_run_id,
        replay_of_manifest_id=replay_of_manifest_id,
        input_snapshot_fingerprint=input_snapshot_fingerprint,
        contract_ref=contract_ref,
        contract_version=contract_version,
        contract_schema_hash=contract_schema_hash,
        dq_policy_ref=dq_policy_ref,
        rule_bundle_version=rule_bundle_version,
        normalization_profile_ref=normalization_profile_ref,
        normalization_profile_version=normalization_profile_version,
        normalization_profile_hash=normalization_profile_hash,
        required_persistence_profile=required_persistence_profile,
    )
