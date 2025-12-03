"""
Metadata builder service for pipeline outputs.
"""
from typing import Any

from bioetl.domain.models import RunContext
from bioetl.infrastructure.output.contracts import WriteResult


class MetadataBuilder:
    """
    Строитель метаданных для результатов пайплайна.
    """

    def build(
        self, context: RunContext, result: WriteResult
    ) -> dict[str, Any]:
        """
        Создает словарь метаданных.

        Args:
            context: Контекст запуска.
            result: Результат записи.
        """
        meta = {
            "run_id": context.run_id,
            "entity": context.entity_name,
            "provider": context.provider,
            "timestamp": context.started_at.isoformat(),
            "row_count": result.row_count,
            "checksum": result.checksum,
            "files": [result.path.name],
        }
        meta.update(context.metadata)
        return meta

    def build_dry_run(
        self, context: RunContext, row_count: int
    ) -> dict[str, Any]:
        """
        Создает метаданные для dry run.
        """
        meta = {
            "run_id": context.run_id,
            "entity": context.entity_name,
            "provider": context.provider,
            "timestamp": context.started_at.isoformat(),
            "row_count": row_count,
            "dry_run": True,
        }
        meta.update(context.metadata)
        return meta
