"""Unit tests for factory_method_helpers."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.factories.pipeline.factory_method_helpers import (
    build_factory_services,
    create_factory_data_source,
    create_factory_runner,
    create_transformer_instance,
)


@pytest.mark.unit
class TestCreateTransformerInstance:
    """Tests for create_transformer_instance."""

    def test_returns_none_when_no_class(self) -> None:
        """Returns None when transformer_class is None."""
        result = create_transformer_instance(
            transformer_class=None,
            provider="chembl",
            pipeline_name="chembl_activity",
            extract_entity_type=lambda n: "activity",
        )

        assert result is None

    def test_creates_transformer_when_class_provided(self) -> None:
        """Instantiates transformer class with extracted entity type."""
        transformer_cls = MagicMock()
        expected = MagicMock()
        transformer_cls.return_value = expected

        result = create_transformer_instance(
            transformer_class=transformer_cls,
            provider="chembl",
            pipeline_name="chembl_activity",
            extract_entity_type=lambda n: "activity",
        )

        assert result is expected
        call_kwargs = transformer_cls.call_args[1]
        assert call_kwargs["provider"] == "chembl"
        assert call_kwargs["entity_type"] == "activity"

    @patch(
        "bioetl.composition.factories.pipeline.factory_method_helpers.build_transformer_dependencies"
    )
    def test_builds_dependencies_when_not_provided(
        self, mock_build_deps: MagicMock
    ) -> None:
        """Builds transformer dependencies when dependencies arg is None."""
        mock_build_deps.return_value = MagicMock()
        transformer_cls = MagicMock()

        create_transformer_instance(
            transformer_class=transformer_cls,
            provider="chembl",
            pipeline_name="chembl_activity",
            extract_entity_type=lambda n: "activity",
            dependencies=None,
        )

        mock_build_deps.assert_called_once()

    def test_uses_provided_dependencies(self) -> None:
        """Uses provided dependencies instead of building new ones."""
        deps = MagicMock()
        transformer_cls = MagicMock()

        create_transformer_instance(
            transformer_class=transformer_cls,
            provider="chembl",
            pipeline_name="chembl_activity",
            extract_entity_type=lambda n: "activity",
            dependencies=deps,
        )

        call_kwargs = transformer_cls.call_args[1]
        assert call_kwargs["dependencies"] is deps


@pytest.mark.unit
class TestCreateFactoryDataSource:
    """Tests for create_factory_data_source."""

    def test_delegates_to_creator_fn(self) -> None:
        """Delegates to the provided create_data_source_fn."""
        expected_source = MagicMock()
        creator = MagicMock(return_value=expected_source)

        result = create_factory_data_source(
            create_data_source_fn=creator,
            settings=MagicMock(),
            pipeline_config=MagicMock(),
            logger=MagicMock(),
            pipeline_name="test_pipe",
        )

        assert result is expected_source
        creator.assert_called_once()


@pytest.mark.unit
class TestBuildFactoryServices:
    """Tests for build_factory_services."""

    @patch(
        "bioetl.composition.factories.pipeline.factory_method_helpers.build_pipeline_services"
    )
    def test_delegates_to_build_pipeline_services(
        self, mock_build: MagicMock
    ) -> None:
        """Delegates to the canonical build_pipeline_services function."""
        expected = MagicMock()
        mock_build.return_value = expected

        result = build_factory_services(
            pipeline_name="test",
            create_data_source_fn=MagicMock(),
            settings=MagicMock(),
            logger=MagicMock(),
        )

        assert result is expected
        mock_build.assert_called_once()


@pytest.mark.unit
class TestCreateFactoryRunner:
    """Tests for create_factory_runner."""

    @patch(
        "bioetl.composition.factories.pipeline.factory_method_helpers.load_pipeline_config"
    )
    def test_loads_config_when_not_provided(
        self, mock_load: MagicMock
    ) -> None:
        """Loads pipeline config from disk when config arg is None."""
        mock_load.return_value = MagicMock()
        create_fn = MagicMock(return_value=MagicMock())
        assemble_fn = MagicMock(return_value=MagicMock())
        settings = SimpleNamespace(env="dev", test_mode=False)
        runtime = SimpleNamespace(strict_gold_validation=True)

        create_factory_runner(
            pipeline_name="test",
            silver_schema=None,
            gold_schema=MagicMock(),
            run_id="r1",
            runtime=runtime,
            settings=settings,
            observability=MagicMock(
                logger=MagicMock(),
                tracer=MagicMock(),
                metrics=MagicMock(),
                dq_monitor=None,
            ),
            create_with_services_fn=create_fn,
            assemble_runner_fn=assemble_fn,
            config=None,
        )

        mock_load.assert_called_once_with("test")

    def test_uses_provided_config(self) -> None:
        """Uses provided config instead of loading from disk."""
        yaml_config = MagicMock()
        create_fn = MagicMock(return_value=MagicMock())
        assemble_fn = MagicMock(return_value=MagicMock())
        settings = SimpleNamespace(env="dev", test_mode=False)
        runtime = SimpleNamespace(strict_gold_validation=True)

        create_factory_runner(
            pipeline_name="test",
            silver_schema=None,
            gold_schema=MagicMock(),
            run_id="r1",
            runtime=runtime,
            settings=settings,
            observability=MagicMock(
                logger=MagicMock(),
                tracer=MagicMock(),
                metrics=MagicMock(),
                dq_monitor=None,
            ),
            create_with_services_fn=create_fn,
            assemble_runner_fn=assemble_fn,
            config=yaml_config,
        )

        create_fn.assert_called_once()
        call_kwargs = create_fn.call_args[1]
        assert call_kwargs["config"] is yaml_config
