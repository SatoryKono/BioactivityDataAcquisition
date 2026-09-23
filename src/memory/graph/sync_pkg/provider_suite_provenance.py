"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg.provider_regression_suite_target import (
    _provider_regression_suite_target,
)

__all__ = [
    "_provider_regression_suite_targets",
    "_provider_suite_provenance",
]


def _provider_suite_provenance(suite_name: str) -> str:
    return f"impact_pipeline_regression_suite:{suite_name}"


def _provider_regression_suite_targets(
    suites: dict[object, object],
) -> tuple[tuple[str, tuple[tuple[str, str], ...]], ...]:
    return tuple(
        suite_target
        for suite_name, suite_payload in suites.items()
        for suite_target in [
            _provider_regression_suite_target(suite_name, suite_payload)
        ]
        if suite_target is not None
    )
