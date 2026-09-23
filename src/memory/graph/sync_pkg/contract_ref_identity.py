"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Callable

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.link_provider_suite_targets import (
    _link_provider_suite_targets,
)
from memory.graph.sync_pkg.provider_suite_provenance import (
    _provider_regression_suite_targets,
)

__all__ = [
    "_contract_ref_identity",
    "_link_provider_regression_suite_tests",
]


def _contract_ref_identity(contract_ref: object) -> tuple[str, str] | None:
    if not isinstance(contract_ref, str) or "." not in contract_ref:
        return None
    provider_name, entity_name = contract_ref.split(".", 1)
    return provider_name, entity_name


def _link_provider_regression_suite_tests(
    link_test_target: Callable[[NodeKey, str, str], None],
    provider_pipeline_index: dict[str, list[NodeKey]],
    *,
    suites: object,
    enabled: bool,
) -> None:
    if not enabled or not isinstance(suites, dict):
        return
    for suite_name, provider_targets in _provider_regression_suite_targets(suites):
        _link_provider_suite_targets(
            link_test_target,
            provider_pipeline_index,
            suite_name=suite_name,
            provider_targets=provider_targets,
        )
