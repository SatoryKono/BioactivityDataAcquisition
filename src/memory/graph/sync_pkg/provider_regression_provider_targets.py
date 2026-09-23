"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg.provider_regression_provider_target import (
    _provider_regression_provider_target,
)

__all__ = [
    "_provider_regression_provider_targets",
]


def _provider_regression_provider_targets(
    suite_payload: dict[str, object],
) -> tuple[tuple[str, str], ...]:
    providers = suite_payload.get("providers")
    if not isinstance(providers, dict):
        return ()
    return tuple(
        target
        for provider_name, raw_test_path in providers.items()
        for target in [
            _provider_regression_provider_target(provider_name, raw_test_path)
        ]
        if target is not None
    )
