"""
Metadata builder service for pipeline outputs.
"""

from pathlib import Path
from typing import Any

from bioetl.domain.configs import QcConfig
from bioetl.domain.models import RunContext
from bioetl.infrastructure.output.contracts import WriteResult


def build_base_metadata(
    context: RunContext,
    *,
    row_count: int,
    dry_run: bool = False,
    include_metadata: bool = True,
) -> dict[str, Any]:
    """
    Формирует базовый словарь метаданных.

    Args:
        context: Контекст запуска.
        row_count: Количество строк результата.
        dry_run: Признак dry-run.
        include_metadata: Добавлять ли пользовательские метаданные из контекста.
    """
    meta = {
        "run_id": context.run_id,
        "entity": context.entity_name,
        "provider": context.provider,
        "timestamp": context.started_at.isoformat(),
        "hash_version": "v1_blake2b_256",
        "row_count": row_count,
    }

    if dry_run:
        meta["dry_run"] = True

    if include_metadata:
        meta.update(context.metadata)

    return meta


def build_run_metadata(
    context: RunContext,
    result: WriteResult,
    *,
    qc_artifacts: list[Path] | None = None,
    qc_checksums: dict[str, str] | None = None,
    qc_config: QcConfig | None = None,
) -> dict[str, Any]:
    """
    Создает словарь метаданных.

    Args:
        context: Контекст запуска.
        result: Результат записи.
    """
    files = [result.path.name]
    qc_artifacts = qc_artifacts or []
    qc_checksums = qc_checksums or {}
    qc_config = qc_config or QcConfig()

    files.extend(path.name for path in qc_artifacts)

    meta = build_base_metadata(
        context, row_count=result.row_count, include_metadata=False
    )
    meta.update(
        {
            "checksum": result.checksum,
            # For backward compatibility and explicitness, keep hash alongside checksum.
            "hash": result.checksum,
            "files": sorted(files),
            "checksums": {
                result.path.name: result.checksum,
                **qc_checksums,
            },
            "qc_artifacts": {
                path.name: {
                    "path": path.name,
                    "checksum": qc_checksums.get(path.name),
                }
                for path in sorted(qc_artifacts, key=lambda p: p.name)
            },
            "qc_config": {
                "enable_quality_report": qc_config.enable_quality_report,
                "enable_correlation_report": qc_config.enable_correlation_report,
                "min_coverage": qc_config.min_coverage,
            },
        }
    )
    meta.update(context.metadata)
    return meta


def build_dry_run_metadata(context: RunContext, row_count: int) -> dict[str, Any]:
    """
    Создает метаданные для dry run.
    """
    return build_base_metadata(
        context, row_count=row_count, dry_run=True, include_metadata=True
    )
