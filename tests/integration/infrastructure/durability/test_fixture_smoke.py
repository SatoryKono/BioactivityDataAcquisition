"""Construction smoke for the S1 durability-sweep denominator.

These tests prove each concrete store can be assembled under an isolated
root and that the child-process harness reports exit codes. They do not
interrupt a write, restart a worker, or record a durability verdict.
"""

from __future__ import annotations

from datetime import UTC
from pathlib import Path

import pytest

from tests.integration.infrastructure.durability._child_runner import (
    child_exit_failure,
    child_exit_success,
)
from tests.integration.infrastructure.durability.builders import (
    DurabilityCollaborators,
    StoreAssembly,
    assemble_store,
    builder_names,
    isolated_store_root,
)
from tests.integration.infrastructure.durability.data_factories import (
    CHILD_FAILURE_CODE,
    RUN_REPORT_MARKER,
    STORE_NAMES,
)
from tests.integration.infrastructure.durability.harness import DurabilityHarness

pytestmark = pytest.mark.integration


def _assert_anchored(root: Path, assembly: StoreAssembly) -> None:
    assert assembly.anchored_paths
    resolved_root = root.resolve()
    for anchored in assembly.anchored_paths:
        assert anchored.resolve().is_relative_to(resolved_root)


def _assert_wiring(
    store_name: str,
    assembly: StoreAssembly,
    deps: DurabilityCollaborators,
) -> None:
    if store_name == "g1_bronze":
        assert assembly.bound_metrics is deps.metrics
        return
    if store_name == "g1_silver":
        assert assembly.bound_validator is deps.silver_validator
        assert assembly.bound_clock is deps.clock
        return
    if store_name == "g4_workflow_transform_artifact":
        assert assembly.bound_clock is deps.clock
        return
    if store_name == "g5_run_report":
        marker = assembly.anchored_paths[0]
        assert marker.read_text(encoding="utf-8") == RUN_REPORT_MARKER


def _store_cases() -> list[object]:
    cases: list[object] = []
    for store_name in STORE_NAMES:
        if store_name == "g1_silver":
            cases.append(
                pytest.param(
                    store_name,
                    marks=pytest.mark.require_silver_validator,
                )
            )
        else:
            cases.append(store_name)
    return cases


@pytest.mark.parametrize("store_name", _store_cases())
def test_store_assembles_under_isolated_root(
    tmp_path: Path,
    durability_collaborators: DurabilityCollaborators,
    store_name: str,
) -> None:
    root = isolated_store_root(tmp_path, store_name)
    assembly = assemble_store(store_name, root, durability_collaborators)
    assert type(assembly.instance) is assembly.expected_type
    assert assembly.name == store_name
    _assert_anchored(root, assembly)
    _assert_wiring(store_name, assembly, durability_collaborators)


def test_store_catalog_matches_builders() -> None:
    assert builder_names() == STORE_NAMES


def test_runtime_fixtures_expose_utc_clock_and_contract_validator(
    durability_collaborators: DurabilityCollaborators,
) -> None:
    moment = durability_collaborators.clock.now()
    durability_collaborators.logger.info("durability-construction-smoke")
    assert moment.tzinfo is UTC
    assert durability_collaborators.silver_validator.policy_ref is None


def test_harness_reports_child_exit_codes() -> None:
    harness = DurabilityHarness()
    assert harness.run_isolated(child_exit_success, ()) == 0
    assert harness.run_isolated(child_exit_failure, ()) == CHILD_FAILURE_CODE
