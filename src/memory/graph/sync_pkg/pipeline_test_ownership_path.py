"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg.default_batch_size import TEST_MATRIX_CONFIG_PATH

__all__ = [
    "_pipeline_test_mapping_config",
    "_pipeline_test_ownership",
    "_pipeline_test_ownership_path",
]


def _pipeline_test_ownership_path(root: Path, ownership_config: str) -> Path:
    return root / ownership_config


def _pipeline_test_ownership(payload: dict[str, object]) -> dict[object, object] | None:
    ownership = payload.get("entity_test_ownership")
    return ownership if isinstance(ownership, dict) else None


def _pipeline_test_mapping_config(
    tests_mapping: object,
) -> tuple[str, str, bool]:
    if not isinstance(tests_mapping, dict):
        return "TESTED_BY", TEST_MATRIX_CONFIG_PATH, True
    return (
        str(tests_mapping.get("relation_type", "TESTED_BY")),
        str(tests_mapping.get("ownership_config", TEST_MATRIX_CONFIG_PATH)),
        bool(tests_mapping.get("provider_regression_suites", True)),
    )
