"""Use case для запуска ETL-пайплайна.

Инкапсулирует всю логику:
- Загрузка конфигурации
- Разрешение путей
- Создание orchestrator
- Запуск пайплайна
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from bioetl.application.orchestrator import PipelineOrchestrator
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.models import RunResult

if TYPE_CHECKING:
    from bioetl.application.pipelines.contracts import PipelineContainerABC
    from bioetl.domain.configs.contracts import PipelineConfigLoaderProtocol
    from bioetl.domain.provider_registry import ProviderRegistryLoaderABC


class InterfaceDisabledError(Exception):
    """Запрошенный интерфейс отключён в конфигурации."""

    def __init__(self, interface: str) -> None:
        super().__init__(f"{interface} interface is disabled by configuration")
        self.interface = interface


@dataclass(frozen=True)
class RunPipelineRequest:
    """Запрос на выполнение пайплайна."""

    pipeline_name: str
    profile: str = "default"
    dry_run: bool = False
    limit: int | None = None
    config_path: Path | None = None
    output_path: Path | None = None
    require_rest_interface: bool = False

    def get_pipeline_id(self) -> str:
        """Преобразует имя пайплайна в ID формата provider.entity.

        Имя пайплайна в формате entity_provider преобразуется в provider.entity.
        Если в имени несколько подчёркиваний, используется последнее для
        разделения (например, drug_indication_chembl → chembl.drug_indication).
        """
        try:
            entity, provider = self.pipeline_name.rsplit("_", 1)
        except ValueError:
            entity = self.pipeline_name
            provider = "chembl"
        return f"{provider}.{entity}"


@dataclass(frozen=True)
class RunPipelineResponse:
    """Результат выполнения пайплайна."""

    run_id: str
    success: bool
    row_count: int
    duration_sec: float
    output_path: Path | None
    errors: list[str] = field(default_factory=list)

    @classmethod
    def from_run_result(cls, result: RunResult) -> "RunPipelineResponse":
        """Создаёт ответ из результата выполнения пайплайна."""
        return cls(
            run_id=str(result.run_id),
            success=result.success,
            row_count=result.row_count,
            duration_sec=result.duration_sec,
            output_path=result.output_path,
            errors=list(result.errors),
        )


class RunPipelineUseCase:
    """Use case для запуска ETL-пайплайна.

    Инкапсулирует всю логику:
    - Загрузка конфигурации
    - Разрешение путей
    - Создание orchestrator
    - Запуск пайплайна

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
        configs_root: Path | None = None,
    ) -> None:
        """Инициализирует use case с необходимыми зависимостями.

        Args:
            config_loader: Загрузчик конфигураций пайплайнов.
            container_factory: Фабрика для создания контейнера зависимостей.
            provider_loader_factory: Фабрика для создания загрузчика провайдеров.
            configs_root: Корневая директория конфигураций.
        """
        self._config_loader = config_loader
        self._container_factory = container_factory
        self._provider_loader_factory = provider_loader_factory
        self._configs_root = configs_root

    def execute(self, request: RunPipelineRequest) -> RunPipelineResponse:
        """Выполняет пайплайн и возвращает результат.

        Args:
            request: Запрос с параметрами запуска.

        Returns:
            Результат выполнения пайплайна.

        Raises:
            InterfaceDisabledError: Если требуемый интерфейс отключён.
        """
        # 1. Загрузка конфигурации
        config = self._load_config(request)

        # 2. Проверка доступности интерфейса
        self._validate_interface_enabled(config, request)

        # 3. Применение переопределений
        if request.output_path:
            config = self._apply_output_override(config, request.output_path)

        # 4. Создание и запуск orchestrator
        orchestrator = self._create_orchestrator(request.pipeline_name, config)
        result = orchestrator.run_pipeline(
            dry_run=request.dry_run,
            limit=request.limit,
        )

        return RunPipelineResponse.from_run_result(result)

    def _load_config(self, request: RunPipelineRequest) -> PipelineConfig:
        """Загружает конфигурацию из файла или по ID.

        Args:
            request: Запрос с параметрами конфигурации.

        Returns:
            Загруженная конфигурация пайплайна.
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
        """Проверяет, что требуемый интерфейс включён в конфигурации.

        Args:
            config: Конфигурация пайплайна.
            request: Запрос с флагами интерфейсов.

        Raises:
            InterfaceDisabledError: Если требуемый интерфейс отключён.
        """
        if request.require_rest_interface:
            if not config.features.rest_interface_enabled:
                raise InterfaceDisabledError("REST")

    def _apply_output_override(
        self, config: PipelineConfig, output_path: Path
    ) -> PipelineConfig:
        """Применяет переопределение пути вывода.

        Args:
            config: Исходная конфигурация.
            output_path: Новый путь для вывода.

        Returns:
            Конфигурация с обновлённым путём вывода.
        """
        output_path.mkdir(parents=True, exist_ok=True)
        new_sink = config.sink.model_copy(update={"output_path": str(output_path)})
        return config.model_copy(update={"sink": new_sink})

    def _create_orchestrator(
        self, pipeline_name: str, config: PipelineConfig
    ) -> PipelineOrchestrator:
        """Создаёт оркестратор для выполнения пайплайна.

        Args:
            pipeline_name: Имя пайплайна.
            config: Конфигурация пайплайна.

        Returns:
            Настроенный оркестратор.
        """
        return PipelineOrchestrator(
            pipeline_name=pipeline_name,
            config=config,
            provider_loader_factory=self._provider_loader_factory,
            container_factory=self._container_factory,
        )

    def _get_profiles_root(self) -> Path | None:
        """Возвращает путь к директории профилей.

        Returns:
            Путь к директории профилей или None.
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
