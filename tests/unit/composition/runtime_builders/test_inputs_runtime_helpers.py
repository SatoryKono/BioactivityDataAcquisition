"""Direct tests for runtime policy helpers used by inputs_resolver."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.composition.runtime_builders import inputs_runtime_helpers


def _make_settings(
    *,
    test_mode: bool = False,
    health_check_mode: object = "strict",
    heartbeat_interval: int = 30,
) -> SimpleNamespace:
    return SimpleNamespace(
        test_mode=test_mode,
        pipeline=SimpleNamespace(
            health_check_mode=health_check_mode,
            heartbeat_interval=heartbeat_interval,
        ),
    )


@pytest.mark.unit
def test_resolve_health_check_mode_policy_uses_probe_in_test_mode() -> None:
    settings = _make_settings(test_mode=True, health_check_mode="strict")

    result = inputs_runtime_helpers.resolve_health_check_mode_policy(
        settings=settings,
        default_health_check_mode="strict",
    )

    assert result == "probe"


@pytest.mark.unit
def test_resolve_health_check_mode_policy_falls_back_to_default() -> None:
    settings = _make_settings(health_check_mode="unsupported")

    result = inputs_runtime_helpers.resolve_health_check_mode_policy(
        settings=settings,
        default_health_check_mode="strict",
    )

    assert result == "strict"


@pytest.mark.unit
def test_resolve_skip_gold_policy_logs_when_gold_sink_disabled() -> None:
    logger = SimpleNamespace(info=lambda *_, **__: None)
    ctx = SimpleNamespace(skip_gold=False)
    yaml_config = SimpleNamespace(
        pipeline_name="chembl_activity",
        sink={"gold": SimpleNamespace(enabled=False)},
    )

    result = inputs_runtime_helpers.resolve_skip_gold_policy(
        ctx=ctx,
        yaml_config=yaml_config,
        observability=SimpleNamespace(logger=logger),
    )

    assert result is True
