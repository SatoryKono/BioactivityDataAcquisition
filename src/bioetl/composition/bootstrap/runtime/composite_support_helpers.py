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
    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.config.settings_api import Settings

FIELD_GROUP_CONFIG_DIR = Path("configs/composites/field_groups")


def _load_field_group_registry(
    composite_name: str,
    logger: LoggerPort,
) -> FieldGroupRegistry | None:
    """Load field group registry for composite pipeline if config exists.

    Resolves the entity name from the composite pipeline name, looks for a
    YAML config file in the canonical field groups directory, and loads the
    registry. Returns None silently when no config is found so callers can
    treat missing field group configs as an opt-out.

    Args:
        composite_name: Composite pipeline name (e.g., 'composite_publication').
        logger: Structured logger used to emit debug/info/warning events.

    Returns:
        Populated FieldGroupRegistry if a config file exists, None otherwise.
    """
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
    metrics: MetricsPort,
) -> DQReportService:
    """Create DQ report service for composite pipelines.

    Builds a DQReportService wired with a DQReportWriter that writes reports
    to the canonical DQ output path under data_dir.

    Args:
        logger: Structured logger forwarded to both the writer and service.
        settings: Global settings providing data_dir for report output paths.
        metrics: Metrics port used for DQ lifecycle counters.

    Returns:
        DQReportService ready for composite pipeline DQ report generation.
    """
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
        metrics=metrics,
    )
