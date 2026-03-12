"""Unit tests for CompositeRunnerSupportMixin."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.composite.runner_pkg.runner_support_mixin import (
    CompositeRunnerSupportMixin,
)
from bioetl.domain.composite.result import (
    EnrichmentResult,
    EnrichmentStatus,
    SeedResult,
)
from bioetl.domain.exceptions import (
    BioETLError,
    CheckpointConflictError,
    InvalidStateError,
    StorageError,
)


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def _make_enricher_cfg(
    pipeline: str,
    *,
    required: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(pipeline=pipeline, required=required)


def _make_composite_config(
    name: str = "test_composite",
    enrichers: list[Any] | None = None,
    required_enrichers: list[str] | None = None,
    required_dependencies: list[str] | None = None,
) -> SimpleNamespace:
    enricher_list = enrichers or []
    return SimpleNamespace(
        name=name,
        enrichers=enricher_list,
        required_enrichers=required_enrichers or [],
        required_dependencies=required_dependencies or [],
        seed=SimpleNamespace(pipeline="seed_pipeline"),
        merge=SimpleNamespace(
            field_priorities=[],
        ),
    )


class _SupportMixinHarness(CompositeRunnerSupportMixin):
    """Minimal test harness providing all required host attributes."""

    def __init__(
        self,
        config: SimpleNamespace | None = None,
    ) -> None:
        self._config = config or _make_composite_config()
        self._runtime = SimpleNamespace(
            required_only=False,
            enrich_only=None,
            force_enricher=None,
        )
        self._logger = MagicMock()
        self._run_id_str = "run-test-1"
        self._started_at: datetime | None = None
        self._checkpoint_manager = AsyncMock()
        self._checkpoint_manager.save = AsyncMock()
        self._seed_runner_factory = MagicMock()
        self._preflight_validator = None
        self._fsm = MagicMock()


# ---------------------------------------------------------------------------
# _get_preflight_skip_reason
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_preflight_skip_reason_when_no_validator_then_returns_reason() -> None:
    harness = _SupportMixinHarness()
    harness._preflight_validator = None

    reason = harness._get_preflight_skip_reason()

    assert reason is not None
    assert "preflight_validator" in reason


@pytest.mark.unit
def test_get_preflight_skip_reason_when_no_field_priorities_then_returns_reason() -> None:
    harness = _SupportMixinHarness()
    harness._preflight_validator = MagicMock()
    harness._config.merge.field_priorities = []

    reason = harness._get_preflight_skip_reason()

    assert reason is not None
    assert "field_priorities" in reason


@pytest.mark.unit
def test_get_preflight_skip_reason_when_configured_then_returns_none() -> None:
    harness = _SupportMixinHarness()
    harness._preflight_validator = MagicMock()
    harness._config.merge.field_priorities = ["title", "abstract"]

    reason = harness._get_preflight_skip_reason()

    assert reason is None


# ---------------------------------------------------------------------------
# _run_preflight_validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_run_preflight_validation_when_no_validator_then_logs_debug_and_skips() -> None:
    harness = _SupportMixinHarness()
    harness._preflight_validator = None

    harness._run_preflight_validation()

    harness._logger.debug.assert_called_once()


@pytest.mark.unit
def test_run_preflight_validation_when_valid_config_then_calls_validator() -> None:
    harness = _SupportMixinHarness()
    harness._preflight_validator = MagicMock()
    harness._preflight_validator.validate = MagicMock(
        return_value=SimpleNamespace(
            resolved_fields=["title"],
            warnings=[],
        )
    )
    harness._preflight_validator.log_resolved_field_sources = MagicMock()
    harness._config.merge.field_priorities = ["title"]

    harness._run_preflight_validation()

    harness._preflight_validator.validate.assert_called_once_with(
        harness._config,
        fail_on_error=True,
    )
    harness._preflight_validator.log_resolved_field_sources.assert_called_once()


# ---------------------------------------------------------------------------
# _validate_config_consistency
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_validate_config_consistency_when_consistent_then_no_warning() -> None:
    enrichers = [
        _make_enricher_cfg("req_a", required=True),
        _make_enricher_cfg("opt_b", required=False),
    ]
    config = _make_composite_config(
        enrichers=enrichers,
        required_enrichers=["req_a"],
    )
    harness = _SupportMixinHarness(config=config)

    harness._validate_config_consistency()

    harness._logger.warning.assert_not_called()


@pytest.mark.unit
def test_validate_config_consistency_when_mismatch_then_logs_warning() -> None:
    enrichers = [_make_enricher_cfg("req_a", required=True)]
    config = _make_composite_config(
        enrichers=enrichers,
        required_enrichers=["different_name"],  # mismatch!
    )
    harness = _SupportMixinHarness(config=config)

    harness._validate_config_consistency()

    harness._logger.warning.assert_called_once()


@pytest.mark.unit
def test_validate_config_consistency_when_all_optional_then_logs_info() -> None:
    enrichers = [_make_enricher_cfg("opt_a", required=False)]
    config = _make_composite_config(
        enrichers=enrichers,
        required_enrichers=[],
    )
    harness = _SupportMixinHarness(config=config)

    harness._validate_config_consistency()

    harness._logger.info.assert_called_once()


# ---------------------------------------------------------------------------
# _save_checkpoint_safe
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_checkpoint_safe_when_success_then_returns_true() -> None:
    harness = _SupportMixinHarness()
    state = MagicMock()

    result = await harness._save_checkpoint_safe(state, "test_op")

    assert result is True
    harness._checkpoint_manager.save.assert_awaited_once_with(state)


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc",
    [
        CheckpointConflictError("test_pipeline", "conflict"),
        StorageError("storage"),
        OSError("os error"),
        ValueError("bad value"),
        TypeError("bad type"),
    ],
)
async def test_save_checkpoint_safe_when_non_fatal_error_then_returns_false(
    exc: Exception,
) -> None:
    harness = _SupportMixinHarness()
    harness._checkpoint_manager.save = AsyncMock(side_effect=exc)
    state = MagicMock()

    result = await harness._save_checkpoint_safe(state, "test_op")

    assert result is False
    harness._logger.warning.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_checkpoint_safe_when_bioetl_error_then_returns_false() -> None:
    harness = _SupportMixinHarness()
    harness._checkpoint_manager.save = AsyncMock(
        side_effect=BioETLError("domain error")
    )
    state = MagicMock()

    result = await harness._save_checkpoint_safe(state, "test_op")

    assert result is False
    harness._logger.warning.assert_called_once()
    warning_kwargs = harness._logger.warning.call_args.kwargs
    assert warning_kwargs.get("reason_code") == "unexpected_bioetl_error"


# ---------------------------------------------------------------------------
# _should_run_enricher
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_should_run_enricher_when_already_completed_then_returns_false() -> None:
    harness = _SupportMixinHarness()
    enricher = _make_enricher_cfg("enricher_a")
    state = SimpleNamespace(completed_enrichers=frozenset({"enricher_a"}))

    assert harness._should_run_enricher(enricher, state) is False


@pytest.mark.unit
def test_should_run_enricher_when_force_enricher_matches_then_returns_true() -> None:
    harness = _SupportMixinHarness()
    harness._runtime.force_enricher = "enricher_a"
    enricher = _make_enricher_cfg("enricher_a")
    state = SimpleNamespace(completed_enrichers=frozenset({"enricher_a"}))

    assert harness._should_run_enricher(enricher, state) is True


@pytest.mark.unit
def test_should_run_enricher_when_required_only_and_optional_then_returns_false() -> None:
    harness = _SupportMixinHarness()
    harness._runtime.required_only = True
    enricher = _make_enricher_cfg("opt_enricher", required=False)
    state = SimpleNamespace(completed_enrichers=frozenset())

    assert harness._should_run_enricher(enricher, state) is False


@pytest.mark.unit
def test_should_run_enricher_when_required_only_and_required_then_returns_true() -> None:
    harness = _SupportMixinHarness()
    harness._runtime.required_only = True
    enricher = _make_enricher_cfg("req_enricher", required=True)
    state = SimpleNamespace(completed_enrichers=frozenset())

    assert harness._should_run_enricher(enricher, state) is True


@pytest.mark.unit
def test_should_run_enricher_when_enrich_only_excludes_enricher_then_returns_false() -> None:
    harness = _SupportMixinHarness()
    harness._runtime.enrich_only = {"other_enricher"}
    enricher = _make_enricher_cfg("enricher_a")
    state = SimpleNamespace(completed_enrichers=frozenset())

    assert harness._should_run_enricher(enricher, state) is False


@pytest.mark.unit
def test_should_run_enricher_when_enrich_only_includes_enricher_then_returns_true() -> None:
    harness = _SupportMixinHarness()
    harness._runtime.enrich_only = {"enricher_a"}
    enricher = _make_enricher_cfg("enricher_a")
    state = SimpleNamespace(completed_enrichers=frozenset())

    assert harness._should_run_enricher(enricher, state) is True


# ---------------------------------------------------------------------------
# _get_enrichers_to_run
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_enrichers_to_run_when_none_completed_then_returns_all() -> None:
    enrichers = [
        _make_enricher_cfg("a"),
        _make_enricher_cfg("b"),
    ]
    config = _make_composite_config(enrichers=enrichers)
    harness = _SupportMixinHarness(config=config)
    state = SimpleNamespace(completed_enrichers=frozenset())

    result = harness._get_enrichers_to_run(state)

    assert len(result) == 2


@pytest.mark.unit
def test_get_enrichers_to_run_when_one_completed_then_returns_remaining() -> None:
    enrichers = [
        _make_enricher_cfg("a"),
        _make_enricher_cfg("b"),
    ]
    config = _make_composite_config(enrichers=enrichers)
    harness = _SupportMixinHarness(config=config)
    state = SimpleNamespace(completed_enrichers=frozenset({"a"}))

    result = harness._get_enrichers_to_run(state)

    assert len(result) == 1
    assert result[0].pipeline == "b"


# ---------------------------------------------------------------------------
# _check_required_enrichers / _get_required_enricher_failure
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_required_enricher_failure_when_all_succeed_then_returns_none() -> None:
    config = _make_composite_config(required_enrichers=["req_a"])
    harness = _SupportMixinHarness(config=config)
    results = {
        "req_a": EnrichmentResult(
            enricher_name="req_a", status=EnrichmentStatus.SUCCESS
        )
    }

    assert harness._get_required_enricher_failure(results) is None


@pytest.mark.unit
def test_get_required_enricher_failure_when_required_not_run_then_returns_message() -> None:
    config = _make_composite_config(required_enrichers=["req_a"])
    harness = _SupportMixinHarness(config=config)

    failure = harness._get_required_enricher_failure({})

    assert failure is not None
    assert "req_a" in failure
    assert "did not run" in failure


@pytest.mark.unit
def test_get_required_enricher_failure_when_required_failed_then_returns_message() -> None:
    config = _make_composite_config(required_enrichers=["req_a"])
    harness = _SupportMixinHarness(config=config)
    results = {
        "req_a": EnrichmentResult(
            enricher_name="req_a",
            status=EnrichmentStatus.FAILED,
            error_message="downstream timeout",
        )
    }

    failure = harness._get_required_enricher_failure(results)

    assert failure is not None
    assert "req_a" in failure


@pytest.mark.unit
def test_check_required_enrichers_when_required_failed_then_raises_invalid_state() -> None:
    config = _make_composite_config(required_enrichers=["req_a"])
    harness = _SupportMixinHarness(config=config)

    with pytest.raises(InvalidStateError):
        harness._check_required_enrichers({})


@pytest.mark.unit
def test_check_required_enrichers_when_all_pass_then_no_exception() -> None:
    config = _make_composite_config(required_enrichers=["req_a"])
    harness = _SupportMixinHarness(config=config)
    results = {
        "req_a": EnrichmentResult(
            enricher_name="req_a", status=EnrichmentStatus.SUCCESS
        )
    }

    harness._check_required_enrichers(results)  # must not raise
