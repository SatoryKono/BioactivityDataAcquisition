"""Effective-config diagnostics payload helpers."""

from __future__ import annotations


def _build_effective_config_diagnostics(
    summary: dict[str, object],
) -> dict[str, object]:
    return {
        "semantic": {
            "effective_config_artifact_id": summary.get("effective_config_artifact_id"),
            "resolved_config_hash": summary.get("resolved_config_hash"),
            "effective_config_hash": summary.get("effective_config_hash"),
            "source_fingerprint": summary.get("source_fingerprint"),
        },
        "occurrence": {
            "run_id": summary.get("run_id"),
            "manifest_id": summary.get("manifest_id"),
            "manifest_created_at": summary.get("manifest_created_at"),
        },
        "diff_policy": {
            "semantic_anchor": "effective_config_hash",
            "occurrence_fields": ["run_id", "manifest_id", "manifest_created_at"],
            "config_hash_policy": "resolved_and_effective_hashes_only",
        },
    }


__all__ = ["_build_effective_config_diagnostics"]
