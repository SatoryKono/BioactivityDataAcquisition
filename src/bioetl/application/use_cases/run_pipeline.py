"""Use case for running ETL pipeline.

Encapsulates all logic:
- Configuration loading
- Path resolution
- Orchestrator creation
- Pipeline execution
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from bioetl.application.orchestrator import PipelineOrchestrator
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.models import RunResult
from bioetl.domain.provider_registry import ProviderRegistryFactory

if TYPE_CHECKING:
    from bioetl.application.pipelines.contracts import PipelineContainerABC
    from bioetl.domain.configs.contracts import PipelineConfigLoaderProtocol
    from bioetl.domain.provider_registry import ProviderRegistryLoaderABC


class InterfaceDisabledError(Exception):
    """Requested interface is disabled in configuration."""

    def __init__(self, interface: str) -> None:
        super().__init__(f"{interface} interface is disabled by configuration")
        self.interface = interface


@dataclass(frozen=True)
class RunPipelineRequest:
    """Pipeline execution request."""

    pipeline_name: str
    profile: str = "default"
    dry_run: bool = False
    limit: int | None = None
    config_path: Path | None = None
    output_path: Path | None = None
    require_rest_interface: bool = False

    def get_pipeline_id(self) -> str:
        """Convert pipeline name to ID in provider.entity format.

        Pipeline name in entity_provider format is converted to provider.entity.
        If there are multiple underscores, the last one is used for separation
        (e.g., drug_indication_chembl → chembl.drug_indication).
        """
        try:
            entity, provider = self.pipeline_name.rsplit("_", 1)
        except ValueError:
            entity = self.pipeline_name
            provider = "chembl"
        return f"{provider}.{entity}"


@dataclass(frozen=True)
class RunPipelineResponse:
    """Pipeline execution result."""

    run_id: str
    success: bool
    row_count: int
    duration_sec: float
    output_path: Path | None
    errors: list[str] = field(default_factory=list)

    @classmethod
    def from_run_result(cls, result: RunResult) -> "RunPipelineResponse":
        """Create response from pipeline execution result."""
        return cls(
            run_id=str(result.run_id),
            success=result.success,
            row_count=result.row_count,
            duration_sec=result.duration_sec,
            output_path=result.output_path,
            errors=list(result.errors),
        )


class RunPipelineUseCase:
    """Use case for running ETL pipeline.

    Encapsulates all logic:
    - Configuration loading
    - Path resolution
    - Orchestrator creation
    - Pipeline execution

    Example:
        use_case = RunPipelineUseCase(
            config_loader=config_loader,
            container_factory=build_default_container,
            provider_loader_factory=create_provider_loader,
        )

        request = RunPipelineRequest(
            pipeline_name="activity_chembl",
            limit=100,
            dry_run=True,
        )

        response = use_case.execute(request)
        if response.success:
            print(f"Processed {response.row_count} rows")
    """

    def __init__(
        self,
        config_loader: "PipelineConfigLoaderProtocol",
        container_factory: Callable[..., "PipelineContainerABC"],
        provider_loader_factory: Callable[[], "ProviderRegistryLoaderABC"],
        provider_registry_factory: ProviderRegistryFactory,
        configs_root: Path | None = None,
    ) -> None:
        """Initialize use case with required dependencies.

        Args:
            config_loader: Pipeline configuration loader.
            container_factory: Factory for creating dependency container.
            provider_loader_factory: Factory for creating provider loader.
            provider_registry_factory: Factory for creating provider registries.
            configs_root: Configuration root directory.
        """
        self._config_loader = config_loader
        self._container_factory = container_factory
        self._provider_loader_factory = provider_loader_factory
        self._provider_registry_factory = provider_registry_factory
        self._configs_root = configs_root

    def execute(self, request: RunPipelineRequest) -> RunPipelineResponse:
        """Execute pipeline and return result.

        Args:
            request: Request with execution parameters.

        Returns:
            Pipeline execution result.

        Raises:
            InterfaceDisabledError: If required interface is disabled.
        """
        # 1. Load configuration
        config = self._load_config(request)

        # 2. Validate interface availability
        self._validate_interface_enabled(config, request)

        # 3. Apply overrides
        if request.output_path:
            config = self._apply_output_override(config, request.output_path)

        # 4. Create and run orchestrator
        orchestrator = self._create_orchestrator(request.pipeline_name, config)
        result = orchestrator.run_pipeline(
            dry_run=request.dry_run,
            limit=request.limit,
        )

        return RunPipelineResponse.from_run_result(result)

    def _load_config(self, request: RunPipelineRequest) -> PipelineConfig:
        """Load configuration from file or by ID.

        Args:
            request: Request with configuration parameters.

        Returns:
            Loaded pipeline configuration.
        """
        if request.config_path:
            return self._config_loader.get_from_path(
                request.config_path,
                profile=request.profile,
                profiles_root=self._get_profiles_root(),
            )

        return self._config_loader.get_by_id(
            request.get_pipeline_id(),
            profile=request.profile,
            base_dir=self._configs_root,
        )

    def _validate_interface_enabled(
        self, config: PipelineConfig, request: RunPipelineRequest
    ) -> None:
        """Verify that required interface is enabled in configuration.

        Args:
            config: Pipeline configuration.
            request: Request with interface flags.

        Raises:
            InterfaceDisabledError: If required interface is disabled.
        """
        if request.require_rest_interface:
            if not config.features.rest_interface_enabled:
                raise InterfaceDisabledError("REST")

    def _apply_output_override(
        self, config: PipelineConfig, output_path: Path
    ) -> PipelineConfig:
        """Apply output path override.

        Args:
            config: Original configuration.
            output_path: New output path.

        Returns:
            Configuration with updated output path.
        """
        output_path.mkdir(parents=True, exist_ok=True)
        new_sink = config.sink.model_copy(update={"output_path": str(output_path)})
        return config.model_copy(update={"sink": new_sink})

    def _create_orchestrator(
        self, pipeline_name: str, config: PipelineConfig
    ) -> PipelineOrchestrator:
        """Create orchestrator for pipeline execution.

        Args:
            pipeline_name: Pipeline name.
            config: Pipeline configuration.

        Returns:
            Configured orchestrator.
        """
        return PipelineOrchestrator(
            pipeline_name=pipeline_name,
            config=config,
            provider_registry_factory=self._provider_registry_factory,
            provider_loader_factory=self._provider_loader_factory,
            container_factory=self._container_factory,
        )

    def _get_profiles_root(self) -> Path | None:
        """Return path to profiles directory.

        Returns:
            Path to profiles directory or None.
        """
        if self._configs_root:
            return self._configs_root / "profiles"
        return None


__all__ = [
    "InterfaceDisabledError",
    "RunPipelineRequest",
    "RunPipelineResponse",
    "RunPipelineUseCase",
]
