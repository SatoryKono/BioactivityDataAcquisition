"""Runtime choices retain replay and optional-observability semantics."""

from __future__ import annotations
import pytest
from bioetl.domain.runtime import composition_boundary_policy as policy


pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "enabled,server,expected",
    [
        (False, False, ("disabled", "disabled")),
        (False, True, ("disabled", "disabled")),
        (True, False, ("disabled", "best_effort_on_run_completion")),
        (
            True,
            True,
            ("auto_managed_during_pipeline_runs", "best_effort_on_run_completion"),
        ),
    ],
)
def test_metrics_publication_modes(enabled, server, expected):
    assert (
        policy.resolve_metrics_publication_modes(
            metrics_enabled=enabled, metrics_server_enabled=server
        )
        == expected
    )


def test_exact_replay_disables_adaptive_sizing():
    assert not policy.memory_adaptive_sizing_allowed(exact_replay=True)
    assert policy.memory_adaptive_sizing_allowed(exact_replay=False)


def test_health_check_test_mode_overrides_strict_configuration():
    assert (
        policy.resolve_health_check_mode(
            test_mode=True, configured_mode="strict", default_health_check_mode="strict"
        )
        == "probe"
    )
    assert (
        policy.resolve_health_check_mode(
            test_mode=False,
            configured_mode="invalid",
            default_health_check_mode="strict",
        )
        == "strict"
    )
