"""Adapters for output services."""
from pathlib import Path
import pandas as pd

from bioetl.domain.models import RunContext
from bioetl.infrastructure.output.contracts import OutputServiceABC, WriteResult
from bioetl.infrastructure.output.unified_writer import UnifiedOutputWriter


class UnifiedOutputServiceAdapter(OutputServiceABC):
    """Адаптер UnifiedOutputWriter к интерфейсу OutputServiceABC."""

    def __init__(self, writer: UnifiedOutputWriter) -> None:
        self._writer = writer

    def write_result(
        self,
        df: pd.DataFrame,
        output_path: Path,
        entity_name: str,
        run_context: RunContext,
    ) -> WriteResult:
        return self._writer.write_result(
            df=df,
            output_path=output_path,
            entity_name=entity_name,
            run_context=run_context,
        )
