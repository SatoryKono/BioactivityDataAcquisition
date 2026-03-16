"""Delta metadata version resolution for PostrunService."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, StorageMaintenancePort


class PostrunMetadataVersionResolver:
    """Resolve Delta table version via injected storage port.

    All Delta Lake access is delegated to the ``StorageMaintenancePort``
    implementation, keeping the application layer free of infrastructure
    dependencies (ARCH-001).
    """

    def __init__(
        self,
        *,
        logger: LoggerPort,
        runtime: object,
        storage: StorageMaintenancePort,
        warning_allowlist: tuple[type[BaseException], ...],
    ) -> None:
        self._logger = logger
        self._runtime = runtime
        self._storage = storage
        self._warning_allowlist = warning_allowlist

    def resolve_delta_version(self, table_path: str, *, layer: str) -> int | None:
        """Resolve Delta table version for lineage metadata.

        Args:
            table_path: Filesystem path to the Delta table directory.
            layer: Medallion layer name (e.g., ``'silver'``, ``'gold'``) used in log messages.

        Returns:
            Integer Delta table version, or None if the table does not exist or
            resolution fails and strict validation is disabled.
        """
        try:
            return self._storage.get_table_version(table_path, layer=layer)
        except self._warning_allowlist as error:
            if self._is_strict_validation_enabled():
                self._logger.error(
                    "delta_version_resolution_failed",
                    layer=layer,
                    table_path=table_path,
                    error_type=type(error).__name__,
                    error=str(error),
                    reason="delta_version_resolution_failed_strict_mode",
                    reason_code="POSTRUN_DELTA_VERSION_RESOLUTION_FAILED_STRICT",
                    strict_mode=True,
                )
                raise
            self._logger.warning(
                "delta_version_resolution_failed",
                layer=layer,
                table_path=table_path,
                error_type=type(error).__name__,
                error=str(error),
                reason="delta_version_resolution_failed_warning_mode",
                reason_code="POSTRUN_DELTA_VERSION_RESOLUTION_FAILED_WARNING",
                strict_mode=False,
            )
            return None

    def _is_strict_validation_enabled(self) -> bool:
        return getattr(self._runtime, "strict_validation", False) is True


__all__ = ["PostrunMetadataVersionResolver"]
