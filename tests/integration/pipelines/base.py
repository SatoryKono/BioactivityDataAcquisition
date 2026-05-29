"""Base class for pipeline integration tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import os
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest

from bioetl.application.core.runner import PipelineRunner
from bioetl.composition.factories.pipeline import GenericPipelineFactory

# Import factories to ensure they are registered/available
from bioetl.composition.factories.storage import StorageBundle, StorageContext
from bioetl.domain.config import RuntimeConfig
from bioetl.domain.ports import LoggerPort, MetricsPort
from bioetl.infrastructure.config._base import Settings
from bioetl.domain.ports.runtime.runner import PipelineCreateRunnerRequest
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter
from tests.integration.pipelines.observability import build_test_observability_bundle

_STARTED_AT = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)


class IntegrationPipelineTestCase:
    """Base class for pipeline integration tests.

    Provides fixtures for:
    - Temporary local storage (Bronze/Silver/Gold/Checkpoints)
    - Settings configuration
    - VCR-enabled HTTP clients (via pytest-vcr on subclasses)
    - Pipeline Runner instantiation
    """

    @pytest.fixture(autouse=True)
    def _setup_storage(self, tmp_path):
        """Setup temporary storage paths and patch StorageFactory."""
        self.storage_root = tmp_path / "storage"
        self.storage_root.mkdir()
        self.data_dir = tmp_path / "data"

        self.bronze_path = str(self.storage_root / "bronze")
        self.silver_path = str(self.storage_root / "silver")
        self.gold_path = str(self.storage_root / "gold")
        self.checkpoints_path = str(self.storage_root / "checkpoints")
        self.json_path = str(self.storage_root / "json")

        # Create directories
        for path in [
            self.bronze_path,
            self.silver_path,
            self.gold_path,
            self.checkpoints_path,
            self.json_path,
            str(self.data_dir / "output"),
        ]:
            os.makedirs(path, exist_ok=True)

        # Patch resolve_storage_paths to always use test paths
        from bioetl.composition.factories.storage import _context_resolution

        original_resolve = _context_resolution.resolve_storage_paths

        def patched_resolve_storage_paths(
            settings, bronze_config, silver_config, gold_config
        ):
            """Always use test paths regardless of test_mode."""
            return (
                False,  # use_yaml_paths = False
                Path(self.bronze_path),
                Path(self.silver_path),
                Path(self.gold_path),
            )

        # Patch Settings class to return test paths
        from bioetl.infrastructure.config._base import Settings
        from unittest.mock import PropertyMock

        type(Settings).bronze_path = PropertyMock(return_value=Path(self.bronze_path))
        type(Settings).silver_path = PropertyMock(return_value=Path(self.silver_path))
        type(Settings).gold_path = PropertyMock(return_value=Path(self.gold_path))

        # Patch bronze cleanup at the class level to prevent file removal during tests
        from bioetl.infrastructure.storage.bronze_writer import BronzeWriter

        original_bronze_cleanup = BronzeWriter.cleanup_old_files

        async def no_op_bronze_cleanup(self, *args, **kwargs):
            return {"files_removed": 0, "bytes_freed": 0, "directories_removed": 0}

        BronzeWriter.cleanup_old_files = no_op_bronze_cleanup

        # Patch create_storage_adapter to force test paths
        from bioetl.composition.factories.storage._helpers import create_storage_adapter

        original_create_adapter = create_storage_adapter

        def patched_create_adapter(*args, **kwargs):
            """Force bronze writer to use test paths."""
            ctx = args[0] if args else kwargs.get("ctx")
            if ctx and hasattr(ctx, "bronze_path"):
                # Force the context to use test paths
                from dataclasses import replace

                ctx = replace(
                    ctx,
                    bronze_path=Path(self.bronze_path),
                    silver_path=Path(self.silver_path),
                    gold_path=Path(self.gold_path),
                )
                if args:
                    args = (ctx,) + args[1:]
                else:
                    kwargs["ctx"] = ctx
            return original_create_adapter(*args, **kwargs)

        # Patch StorageFactory.create to return local paths
        # Patch at multiple import locations to ensure coverage
        with patch(
            "bioetl.composition.factories.storage._helpers.create_storage_adapter",
            side_effect=patched_create_adapter,
        ):
            with patch(
                "bioetl.composition.factories.storage.StorageFactory.create"
            ) as mock_create:
                mock_create.side_effect = self._create_local_storage_context
                with patch(
                    "bioetl.composition.factories.storage.factory.StorageFactory.create"
                ) as mock_create_factory:
                    mock_create_factory.side_effect = self._create_local_storage_context
                    with patch(
                        "bioetl.composition.factories.services.factory.StorageFactory.create"
                    ) as mock_create_services:
                        mock_create_services.side_effect = (
                            self._create_local_storage_context
                        )
                        with patch(
                            "bioetl.composition.factories.services.common_service_wiring.StorageFactory.create"
                        ) as mock_create_wiring:
                            mock_create_wiring.side_effect = (
                                self._create_local_storage_context
                            )
                            with patch.object(
                                _context_resolution,
                                "resolve_storage_paths",
                                patched_resolve_storage_paths,
                            ):
                                yield

        # Restore original bronze cleanup
        BronzeWriter.cleanup_old_files = original_bronze_cleanup

    def _create_local_storage_context(
        self,
        settings: Settings,
        config: PipelineYamlConfig,
        logger: LoggerPort,
        metrics: MetricsPort,
        pipeline_name: str | None = None,
        tracing: Any = None,
        metadata_coordinator: Any = None,
        silver_validator: Any = None,
        **_kwargs: Any,
    ) -> StorageContext:
        """Create a StorageContext pointing to local temp paths."""
        del settings
        del pipeline_name
        del tracing
        del metadata_coordinator
        del silver_validator
        # Create real writers pointing to local paths

        # Determine if we should save JSON (mirroring real factory logic)
        bronze_config = config.sink.get("bronze")
        save_json = bronze_config.save_json if bronze_config else False

        # Create bronze writer with flat_structure=False to match production path structure
        bronze_writer = BronzeWriter(
            base_path=self.bronze_path,
            logger=logger,
            metrics=metrics,
            save_json=save_json,
            json_path=self.json_path if save_json else None,
            flat_structure=False,
            # Lock validation at Application layer
        )

        adapter = StorageBundle(
            bronze_writer=bronze_writer,
            silver_writer=SilverWriter(
                base_path=self.silver_path,
                logger=logger,
                csv_exporter=None,
                # Lock validation at Application layer
            ),
            gold_writer=GoldWriter(
                base_path=self.gold_path,
                logger=logger,
                csv_exporter=None,
                # Lock validation at Application layer
            ),
        )

        from pathlib import Path

        return StorageContext(
            adapter=adapter,
            bronze_path=Path(self.bronze_path),
            silver_path=Path(self.silver_path),
            gold_path=Path(self.gold_path),
            checkpoints_path=Path(self.checkpoints_path),
        )

    @pytest.fixture
    def settings(self, tmp_path):
        """Return generic settings for testing."""
        # Use defaults, usually sufficient as we mock storage
        # Ensure ENV is not prod to avoid acmolecule_idental S3 usage if mock fails (safety net)
        os.environ["BIOETL_ENV"] = "dev"
        # Enable test_mode to use settings paths instead of YAML paths
        # Override data_dir to use temp directory
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        storage_root = tmp_path / "storage"
        storage_root.mkdir(exist_ok=True)

        settings = Settings(test_mode=True, data_dir=str(data_dir))

        # Override _data_dir directly on the instance
        # This will affect all computed properties that depend on it
        settings._data_dir = str(storage_root)

        return settings

    @pytest.fixture
    def runtime_config(self):
        """Return default runtime config."""
        from bioetl.domain.types import RunType

        return RuntimeConfig(
            run_type=RunType.INCREMENTAL,
            heartbeat_interval=10,
            resume=False,
            limit=None,  # Can be overridden in tests
        )

    @pytest.fixture
    def run_id(self):
        return uuid4()

    def create_runner(
        self,
        factory: GenericPipelineFactory,
        settings: Settings,
        runtime_config: RuntimeConfig,
        run_id,
        config_overrides: dict[str, Any] | None = None,
    ) -> PipelineRunner:
        """Create a pipeline runner with the given factory and settings.

        Args:
            factory: The pipeline factory to use.
            settings: Application settings.
            runtime_config: Runtime configuration.
            run_id: UUID for the run.
            config_overrides: Optional dictionary to update the loaded YAML config.
        """
        # Load config via factory (it handles loading)
        # But we might want to override some values (e.g. limit, or sinks)
        from bioetl.infrastructure.config.pipeline_config_api import (
            load_pipeline_config,
        )

        pipeline_config = load_pipeline_config(factory.pipeline_name)

        if config_overrides:
            # Deep update or simple update? Simple for now.
            # config is a Pydantic model. We can use `model_copy(update=...)`
            pipeline_config = pipeline_config.model_copy(update=config_overrides)

        # Create observability bundle for testing
        # Per Unified Observability Contract, metrics must be non-None
        observability = build_test_observability_bundle()

        # Create runner
        # Note: GenericPipelineFactory.create_runner uses BaseServicesFactory,
        # which calls StorageFactory.create, which we patched.
        runner = factory.create_runner(
            PipelineCreateRunnerRequest(
                run_id=run_id,
                runtime=runtime_config,
                started_at=_STARTED_AT,
                settings=settings,
                observability=observability,
                config=pipeline_config,
            )
        )

        return runner

    @staticmethod
    def resolve_delta_table_path(layer_path: str, table_name: str) -> str:
        """Resolve a logical Delta table name to its on-disk directory."""
        return f"{layer_path}/{table_name.replace('.', '/')}"
