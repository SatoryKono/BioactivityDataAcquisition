"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg.provider_regression_provider_targets import (
    _provider_regression_provider_targets,
)

__all__ = [
    "_provider_regression_suite_target",
]


def _provider_regression_suite_target(
    suite_name: object,
    suite_payload: object,
) -> tuple[str, tuple[tuple[str, str], ...]] | None:
    if not isinstance(suite_name, str) or not isinstance(suite_payload, dict):
        return None
    provider_targets = _provider_regression_provider_targets(suite_payload)
    if not provider_targets:
        return None
    return suite_name, provider_targets
