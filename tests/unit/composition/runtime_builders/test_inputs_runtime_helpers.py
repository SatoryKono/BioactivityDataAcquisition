"""Direct tests for runtime policy helpers used by inputs_resolver."""

from __future__ import annotations

from tests.helpers.synthetic_paths import synthetic_test_root
from types import SimpleNamespace

import pytest

from bioetl.composition.runtime_builders import inputs_runtime_helpers

TEST_ROOT = synthetic_test_root("bioetl-inputs-runtime")
BRONZE_DISABLED_PATH = str(TEST_ROOT / "bronze-disabled")
BRONZE_ENABLED_PATH = str(TEST_ROOT / "bronze-enabled")


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
    events: list[tuple[str, dict[str, object]]] = []
    logger = SimpleNamespace(
        info=lambda event, **kwargs: events.append((event, kwargs))
    )
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
    assert events == [
        (
            "gold_sink_disabled",
            {
                "reason": "sink.gold.enabled_false",
                "pipeline": "chembl_activity",
            },
        )
    ]


@pytest.mark.unit
def test_resolve_skip_gold_policy_honors_cli_skip_without_logging() -> None:
    events: list[tuple[str, dict[str, object]]] = []
    ctx = SimpleNamespace(skip_gold=True)
    yaml_config = SimpleNamespace(
        pipeline_name="chembl_activity",
        sink={"gold": SimpleNamespace(enabled=True)},
    )

    result = inputs_runtime_helpers.resolve_skip_gold_policy(
        ctx=ctx,
        yaml_config=yaml_config,
        observability=SimpleNamespace(
            logger=SimpleNamespace(
                info=lambda event, **kwargs: events.append((event, kwargs))
            )
        ),
    )

    assert result is True
    assert events == []


@pytest.mark.unit
def test_resolve_skip_gold_policy_returns_false_when_gold_sink_enabled() -> None:
    events: list[tuple[str, dict[str, object]]] = []
    ctx = SimpleNamespace(skip_gold=False)
    yaml_config = SimpleNamespace(
        pipeline_name="chembl_activity",
        sink={"gold": SimpleNamespace(enabled=True)},
    )

    result = inputs_runtime_helpers.resolve_skip_gold_policy(
        ctx=ctx,
        yaml_config=yaml_config,
        observability=SimpleNamespace(
            logger=SimpleNamespace(
                info=lambda event, **kwargs: events.append((event, kwargs))
            )
        ),
    )

    assert result is False
    assert events == []


@pytest.mark.unit
def test_log_filter_config_is_noop_when_filter_is_missing() -> None:
    events: list[tuple[str, dict[str, object]]] = []

    inputs_runtime_helpers.log_filter_config(
        observability=SimpleNamespace(
            logger=SimpleNamespace(
                info=lambda event, **kwargs: events.append((event, kwargs))
            )
        ),
        filter_config=None,
        from_cli=False,
    )

    assert events == []


@pytest.mark.unit
def test_log_cached_bronze_only_logs_when_enabled() -> None:
    events: list[tuple[str, dict[str, object]]] = []
    observability = SimpleNamespace(
        logger=SimpleNamespace(
            info=lambda event, **kwargs: events.append((event, kwargs))
        )
    )

    inputs_runtime_helpers.log_cached_bronze(
        observability=observability,
        cached_bronze=SimpleNamespace(
            enabled=False,
            bronze_path=BRONZE_DISABLED_PATH,
            bronze_date="2026-01-01",
        ),
    )
    inputs_runtime_helpers.log_cached_bronze(
        observability=observability,
        cached_bronze=SimpleNamespace(
            enabled=True,
            bronze_path=BRONZE_ENABLED_PATH,
            bronze_date="2026-01-02",
        ),
    )

    assert events == [
        (
            "cached_bronze_mode_enabled",
            {
                "bronze_path": BRONZE_ENABLED_PATH,
                "bronze_date": "2026-01-02",
            },
        )
    ]


@pytest.mark.unit
def test_resolve_runtime_projection_combines_runtime_policies() -> None:
    result = inputs_runtime_helpers.resolve_runtime_projection(
        ctx=SimpleNamespace(skip_gold=False),
        settings=_make_settings(health_check_mode="probe", heartbeat_interval=45),
        yaml_config=SimpleNamespace(
            pipeline_name="chembl_activity",
            sink={"gold": SimpleNamespace(enabled=True)},
        ),
        observability=SimpleNamespace(
            logger=SimpleNamespace(info=lambda *_, **__: None)
        ),
        default_health_check_mode="strict",
    )

    assert result.heartbeat_interval == 45
    assert result.health_check_mode == "probe"
    assert result.skip_gold is False
