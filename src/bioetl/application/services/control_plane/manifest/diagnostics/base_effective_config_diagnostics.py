"""Effective-config diagnostics payload helpers."""

from __future__ import annotations


def _build_effective_config_diagnostics(
    summary: dict[str, object],
) -> dict[str, object]:
    return {
        "semantic": {
            "legacy_config_hash": summary.get("config_hash"),
            "legacy_config_hash_alias_of": "resolved_config_hash",
            "effective_config_artifact_id": summary.get("effective_config_artifact_id"),
            "resolved_config_hash": summary.get("resolved_config_hash"),
            "effective_config_hash": summary.get("effective_config_hash"),
            "source_fingerprint": summary.get("source_fingerprint"),
            "config_hash_compatibility_anchor": summary.get("config_hash"),
            "config_hash_legacy_alias_of": "resolved_config_hash",
        },
        "occurrence": {
            "run_id": summary.get("run_id"),
            "manifest_id": summary.get("manifest_id"),
            "manifest_created_at": summary.get("manifest_created_at"),
        },
        "diff_policy": {
            "semantic_anchor": "effective_config_hash",
            "occurrence_fields": ["run_id", "manifest_id", "manifest_created_at"],
            "config_hash_policy": ("deprecated_legacy_alias_for_resolved_config_hash"),
            "legacy_config_hash_display_only": True,
            "legacy_config_hash_replay_identity_anchor": False,
        },
    }


__all__ = ["_build_effective_config_diagnostics"]
