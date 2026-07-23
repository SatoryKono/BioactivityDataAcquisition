"""Shared checkpoint execution-identity payload helpers."""

from __future__ import annotations

from typing import Final

from bioetl.domain.config.runtime import CANONICAL_SILVER_FILTER_COMPATIBILITY_MODE
from bioetl.domain.normalization import build_execution_identity_payload
from bioetl.domain.types import JsonDict

CANONICAL_ONLY_IDENTITY_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "pipeline_name",
        "run_type",
        "pipeline_version",
        "git_commit",
        "dependency_lock_hash",
        "dq_contract_compatibility_hash",
        "normalization_profile_ref",
        "normalization_profile_version",
        "normalization_profile_hash",
        "exact_replay",
        "input_snapshot_fingerprint",
        "silver_filter_compatibility_mode",
    }
)


def build_checkpoint_execution_identity_payload(
    *,
    pipeline_name: str | None,
    run_type: str | None,
    pipeline_version: str | None,
    git_commit: str | None,
    dependency_lock_hash: str | None,
    effective_config_hash: str | None,
    dq_contract_compatibility_hash: str | None,
    contract: tuple[str | None, str | None],
    normalization_profile: tuple[str | None, str | None, str | None],
    effective_config_artifact_id: str | None,
    exact_replay: bool | None,
    input_snapshot_fingerprint: str | None,
    silver_filter_compatibility_mode: str | None = (
        CANONICAL_SILVER_FILTER_COMPATIBILITY_MODE
    ),
) -> JsonDict:
    """Build the canonical checkpoint execution-identity fallback payload.

    Packed groups keep this helper under the Sonar S107 budget:
    - ``contract``: ``(contract_ref, contract_version)``
    - ``normalization_profile``: ``(ref, version, hash)``
    """
    contract_ref, contract_version = contract
    (
        normalization_profile_ref,
        normalization_profile_version,
        normalization_profile_hash,
    ) = normalization_profile
    if all(
        value is None
        for value in (
            pipeline_name,
            run_type,
            pipeline_version,
            git_commit,
            dependency_lock_hash,
            dq_contract_compatibility_hash,
            normalization_profile_ref,
            normalization_profile_version,
            normalization_profile_hash,
            exact_replay,
            input_snapshot_fingerprint,
            silver_filter_compatibility_mode,
        )
    ):
        return {}
    return {
        key: value
        for key, value in build_execution_identity_payload(
            pipeline_name=pipeline_name,
            run_type=run_type,
            pipeline_version=pipeline_version,
            git_commit=git_commit,
            dependency_lock_hash=dependency_lock_hash,
            effective_config_hash=effective_config_hash,
            dq_contract_compatibility_hash=dq_contract_compatibility_hash,
            contract=(contract_ref, contract_version),
            normalization_profile=(
                normalization_profile_ref,
                normalization_profile_version,
                normalization_profile_hash,
            ),
            effective_config_artifact_id=effective_config_artifact_id,
            exact_replay=exact_replay,
            input_snapshot_fingerprint=input_snapshot_fingerprint,
            silver_filter_compatibility_mode=silver_filter_compatibility_mode,
        ).items()
        if value is not None
    }


def has_canonical_checkpoint_execution_identity_fields(payload: JsonDict) -> bool:
    """Return whether payload contains any canonical-only checkpoint identity field."""
    return any(field in payload for field in CANONICAL_ONLY_IDENTITY_FIELDS)
