"""Concrete loader implementation for file-based outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from bioetl.application.pipelines.contracts import LoaderABC
from bioetl.domain.clients.base.output.contracts import OutputWriterABC, WriteResult


class FileLoaderImpl(LoaderABC):
    """Loader that delegates persistence to OutputWriterABC."""

    def __init__(self, output_writer: OutputWriterABC) -> None:
        self._output_writer = output_writer

    def load(
        self,
        df: pd.DataFrame,
        output_path: Path,
        context: Any,
        column_order: list[str] | None = None,
    ) -> WriteResult:
        return self._output_writer.write_result(
            df=df,
            output_path=output_path,
            entity_name=context.entity_name,
            run_context=context,
            column_order=column_order,
        )


__all__ = ["FileLoaderImpl"]
