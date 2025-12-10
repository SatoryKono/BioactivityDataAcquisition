"""Domain-level pipeline contracts.

Tabular Data Abstractions:
    This module uses domain-level TabularData instead of pd.DataFrame.
    Infrastructure layer provides PandasAdapter implementations.

    See bioetl.domain.data for protocol definitions.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterable

from bioetl.domain.clients.base.output.contracts import WriteResult
from bioetl.domain.data import TabularData
from bioetl.domain.enums import ErrorAction
from bioetl.domain.errors import PipelineStageError
from bioetl.domain.models import RunContext, StageResult

__all__ = [
    "ErrorPolicyABC",
    "ExtractorABC",
    "LoaderABC",
    "PipelineHookABC",
]


class PipelineHookABC(ABC):
    """Хуки жизненного цикла пайплайна."""

    @abstractmethod
    def on_stage_start(self, stage: str, context: Any) -> None:
        """Вызывается перед началом стадии."""

    @abstractmethod
    def on_stage_end(self, stage: str, result: StageResult) -> None:
        """Вызывается после завершения стадии."""

    @abstractmethod
    def on_error(self, stage: str, error: PipelineStageError) -> None:
        """Вызывается при ошибке."""


class ErrorPolicyABC(ABC):
    """Политика обработки ошибок."""

    @abstractmethod
    def handle(self, error: PipelineStageError, context: Any) -> ErrorAction:
        """Определяет действие при ошибке."""

    @abstractmethod
    def can_retry(self, error: PipelineStageError) -> bool:
        """Проверяет, стоит ли повторять операцию."""


class ExtractorABC(ABC):
    """Component responsible for extracting data from source.

    Uses domain-level TabularData abstraction for extracted data chunks.
    """

    @abstractmethod
    def extract(self, **kwargs: Any) -> Iterable[TabularData]:
        """Extract data from source in chunks.

        Args:
            **kwargs: Source-specific extraction parameters.

        Yields:
            Chunks of tabular data.
        """


class LoaderABC(ABC):
    """Component responsible for loading data to destination.

    Uses domain-level TabularData abstraction for input data.
    """

    @abstractmethod
    def load(
        self,
        data: TabularData,
        output_path: Path,
        context: RunContext,
        *,
        column_order: list[str] | None = None,
    ) -> WriteResult:
        """Load data to destination.

        Args:
            data: Tabular data to load.
            output_path: Target path for output.
            context: Run context with metadata.
            column_order: Optional column ordering.

        Returns:
            WriteResult with operation details.
        """

    @abstractmethod
    def write_metadata(self, meta: dict[str, Any], path: Path) -> None:
        """Write pipeline artifact metadata.

        Args:
            meta: Metadata dictionary.
            path: Target file path.
        """

    @abstractmethod
    def write_qc_report(self, data: TabularData, path: Path) -> None:
        """Write QC report in deterministic order.

        Args:
            data: Tabular data for QC analysis.
            path: Target report path.
        """
