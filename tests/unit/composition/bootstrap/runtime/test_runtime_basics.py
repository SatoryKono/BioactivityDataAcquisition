"""Unit tests for runtime_basics bootstrap helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.composition.bootstrap.runtime.runtime_basics import (
    bootstrap_runtime_basics,
    build_support_services,
)
from bioetl.composition.bootstrap.runtime.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)
from bioetl.domain.composite.config import CompositeConfig


_FIXED_UUID = UUID("12345678-1234-5678-1234-567812345678")


def _make_config(name: str = "test_pipeline") -> CompositeConfig:
    return cast(CompositeConfig, SimpleNamespace(name=name))


def _make_runtime() -> CompositeRuntimeConfig:
    return CompositeRuntimeConfig()


@pytest.mark.unit
class TestBootstrapRuntimeBasics:
    """Tests for bootstrap_runtime_basics."""

    def test_returns_infrastructure_context(self) -> None:
        """bootstrap_runtime_basics returns the typed infrastructure context."""
        config = _make_config()
        settings = SimpleNamespace(metrics_enabled=False)
        logger = MagicMock()
        tracer = MagicMock()
        storage = MagicMock()
        lock = MagicMock()

        result = bootstrap_runtime_basics(
            config=config,
            run_id=None,
            settings_provider=lambda: settings,
            logger_bootstrapper=lambda _n, _u, _l: logger,
            tracer_bootstrapper=lambda _settings: tracer,
            storage_bootstrapper=lambda **kw: storage,
            lock_factory=lambda: lock,
            uuid_factory=lambda: _FIXED_UUID,
        )

        assert isinstance(result, CompositeInfrastructureContext)
        assert result.run_id == str(_FIXED_UUID)
        assert result.settings is settings
        assert result.logger is logger
        assert result.metrics is not None
        assert result.tracer is tracer
        assert result.storage is storage
        assert result.lock is lock
        assert result.clock is not None

    def test_runtime_basics__uses_provided_run_id__fbc0f291(self) -> None:
        """When run_id is provided, it is used instead of generating a new one."""
        config = _make_config()
        provided_run_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

        result = bootstrap_runtime_basics(
            config=config,
            run_id=provided_run_id,
            settings_provider=MagicMock(
                return_value=SimpleNamespace(metrics_enabled=False)
            ),
            logger_bootstrapper=lambda _n, _u, _l: MagicMock(),
            tracer_bootstrapper=lambda _settings: MagicMock(),
            storage_bootstrapper=lambda **kw: MagicMock(),
            lock_factory=MagicMock(return_value=MagicMock()),
            uuid_factory=MagicMock(),
        )

        assert result.run_id == provided_run_id

    def test_runtime_basics__run_id_when_none__0ad92364(self) -> None:
        """When run_id is None, uuid_factory is called to generate one."""
        uuid_factory = MagicMock(return_value=_FIXED_UUID)

        result = bootstrap_runtime_basics(
            config=_make_config("p"),
            run_id=None,
            settings_provider=MagicMock(
                return_value=SimpleNamespace(metrics_enabled=False)
            ),
            logger_bootstrapper=lambda _n, _u, _l: MagicMock(),
            tracer_bootstrapper=lambda _settings: MagicMock(),
            storage_bootstrapper=lambda **kw: MagicMock(),
            lock_factory=MagicMock(return_value=MagicMock()),
            uuid_factory=uuid_factory,
        )

        uuid_factory.assert_called_once()
        assert result.run_id == str(_FIXED_UUID)

    def test_storage_bootstrapper_called_with_csv_export(self) -> None:
        """storage_bootstrapper receives explicit runtime context and ports."""
        storage_bootstrapper = MagicMock(return_value=MagicMock())
        settings = SimpleNamespace(metrics_enabled=False)
        logger = MagicMock()
        tracer = MagicMock()

        bootstrap_runtime_basics(
            config=_make_config("p"),
            run_id=str(_FIXED_UUID),
            settings_provider=MagicMock(return_value=settings),
            logger_bootstrapper=lambda _n, _u, _l: logger,
            tracer_bootstrapper=lambda _settings: tracer,
            storage_bootstrapper=storage_bootstrapper,
            lock_factory=MagicMock(return_value=MagicMock()),
            uuid_factory=MagicMock(),
        )

        storage_bootstrapper.assert_called_once()
        kwargs = storage_bootstrapper.call_args.kwargs
        assert kwargs["enable_csv_export"] is True
        assert kwargs["settings"] is settings
        assert kwargs["logger"] is logger
        assert kwargs["tracing"] is tracer
        assert kwargs["run_context"].run_id == _FIXED_UUID
        assert kwargs["run_context"].pipeline_name == "p"

    def test_runtime_basics_uses_injected_clock_factory(self) -> None:
        """clock_factory owns runtime time instead of hidden wall-clock reads."""
        started_at = datetime(2026, 7, 2, 8, 30, tzinfo=UTC)
        clock = SimpleNamespace(now=MagicMock(return_value=started_at))
        storage_bootstrapper = MagicMock(return_value=MagicMock())

        result = bootstrap_runtime_basics(
            config=_make_config("p"),
            run_id=str(_FIXED_UUID),
            settings_provider=MagicMock(
                return_value=SimpleNamespace(metrics_enabled=False)
            ),
            logger_bootstrapper=lambda _n, _u, _l: MagicMock(),
            tracer_bootstrapper=lambda _settings: MagicMock(),
            storage_bootstrapper=storage_bootstrapper,
            lock_factory=MagicMock(return_value=MagicMock()),
            uuid_factory=MagicMock(),
            clock_factory=lambda: clock,
        )

        assert result.clock is clock
        assert storage_bootstrapper.call_args.kwargs["run_context"].started_at == (
            started_at
        )

    def test_logger_bootstrapper_receives_pipeline_name(self) -> None:
        """logger_bootstrapper receives config.name as the first argument."""
        captured: list[str] = []

        def _logger_bootstrapper(name: str, uid: UUID, level: str) -> MagicMock:
            captured.append(name)
            return MagicMock()

        bootstrap_runtime_basics(
            config=_make_config("my_composite"),
            run_id=str(_FIXED_UUID),
            settings_provider=MagicMock(
                return_value=SimpleNamespace(metrics_enabled=False)
            ),
            logger_bootstrapper=_logger_bootstrapper,
            tracer_bootstrapper=lambda _settings: MagicMock(),
            storage_bootstrapper=lambda **kw: MagicMock(),
            lock_factory=MagicMock(return_value=MagicMock()),
            uuid_factory=MagicMock(),
        )

        assert captured == ["my_composite"]


@pytest.mark.unit
class TestBuildSupportServices:
    """Tests for build_support_services."""

    def test_delegates_to_factory_cls_build(self) -> None:
        """build_support_services calls factory_cls(...).build()."""
        expected_services = SimpleNamespace(key_extractor=MagicMock())
        mock_instance = MagicMock()
        mock_instance.build.return_value = expected_services
        mock_cls = MagicMock(return_value=mock_instance)
        infra_context = CompositeInfrastructureContext(
            run_id="rid",
            settings=SimpleNamespace(metrics_enabled=False),
            logger=MagicMock(),
            metrics=MagicMock(),
            tracer=MagicMock(),
            storage=MagicMock(),
            lock=MagicMock(),
        )

        result = build_support_services(
            config=_make_config(),
            runtime=_make_runtime(),
            infra_context=infra_context,
            support_services_factory_cls=mock_cls,
            resolve_gold_schema_fn=MagicMock(),
            load_field_group_registry_fn=MagicMock(),
            create_dq_report_service_fn=MagicMock(),
        )

        assert result is expected_services
        mock_instance.build.assert_called_once()

    def test_factory_cls_receives_config(self) -> None:
        """Factory class receives config kwarg."""
        mock_instance = MagicMock()
        mock_instance.build.return_value = SimpleNamespace()
        mock_cls = MagicMock(return_value=mock_instance)
        config = _make_config("test")
        infra_context = CompositeInfrastructureContext(
            run_id="rid",
            settings=SimpleNamespace(metrics_enabled=False),
            logger=MagicMock(),
            metrics=MagicMock(),
            tracer=MagicMock(),
            storage=MagicMock(),
            lock=MagicMock(),
        )

        build_support_services(
            config=config,
            runtime=_make_runtime(),
            infra_context=infra_context,
            support_services_factory_cls=mock_cls,
            resolve_gold_schema_fn=MagicMock(),
            load_field_group_registry_fn=MagicMock(),
            create_dq_report_service_fn=MagicMock(),
        )

        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["config"] is config
