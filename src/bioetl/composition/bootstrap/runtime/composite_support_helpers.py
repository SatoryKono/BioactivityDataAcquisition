"""Helper factories for composite runtime support services."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.infrastructure.config.field_group_loader import (
    FieldGroupLoadError,
    load_field_groups,
)

if TYPE_CHECKING:
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.composite.field_groups import FieldGroupRegistry
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.config import Settings

FIELD_GROUP_CONFIG_DIR = Path("configs/composites/field_groups")


def _load_field_group_registry(
    composite_name: str,
    logger: LoggerPort,
) -> FieldGroupRegistry | None:
    """Load field group registry for composite pipeline if config exists."""
    entity = (
        composite_name.replace("composite_", "")
        if "_" in composite_name
        else composite_name
    )
    config_path = FIELD_GROUP_CONFIG_DIR / f"{entity}.yaml"
    if not config_path.exists():
        logger.debug(
            "No field group config found, skipping",
            config_path=str(config_path),
        )
        return None

    try:
        registry = load_field_groups(config_path)
        logger.info(
            "Loaded field group registry",
            config_path=str(config_path),
            groups=len(registry.groups),
            fields=registry.field_count,
            columns=registry.column_count,
        )
        return registry
    except (FieldGroupLoadError, FileNotFoundError) as error:
        logger.warning(
            "Failed to load field group config, continuing without it",
            error=str(error),
            config_path=str(config_path),
        )
        return None


def _create_dq_report_service(
    logger: LoggerPort,
    settings: Settings,
) -> DQReportService:
    """Create DQ report service for composite pipelines."""
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.infrastructure.export.dq_report_writer import DQReportWriter

    reports_base_path = Path(settings.data_dir) / "output" / "reports" / "dq"
    report_writer = DQReportWriter(
        base_path=reports_base_path,
        logger=logger,
    )
    return DQReportService(
        logger=logger,
        report_writer=report_writer,
    )
