"""Delta metadata version resolution for PostrunService."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from bioetl.application.core.postrun._failure_policy import (
    PostrunFailureHandlingMixin,
    PostrunFailurePolicySpec,
)

if TYPE_CHECKING:
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.ports import LoggerPort, StorageMaintenancePort


class PostrunMetadataVersionResolver(PostrunFailureHandlingMixin):
    """Resolve Delta table version via injected storage port.

    All Delta Lake access is delegated to the ``StorageMaintenancePort``
    implementation, keeping the application layer free of infrastructure
    dependencies (ARCH-001).
    """

    _FAILURE_POLICY = PostrunFailurePolicySpec(
        event="delta_version_resolution_failed",
        strict_reason="delta_version_resolution_failed_strict_mode",
        strict_reason_code="POSTRUN_DELTA_VERSION_RESOLUTION_FAILED_STRICT",
        warning_reason="delta_version_resolution_failed_warning_mode",
        warning_reason_code="POSTRUN_DELTA_VERSION_RESOLUTION_FAILED_WARNING",
    )

    def __init__(
        self,
        *,
        logger: LoggerPort,
        runtime: RuntimeConfig,
        storage: StorageMaintenancePort,
        warning_allowlist: tuple[type[BaseException], ...],
    ) -> None:
        self._logger = logger
        self._runtime = runtime
        self._storage = storage
        self._warning_allowlist = warning_allowlist

    def resolve_delta_version(
        self, table_path: str, *, layer: Literal["silver", "gold"]
    ) -> int | None:
        """Resolve Delta table version for lineage metadata.

        Args:
            table_path: Filesystem path to the Delta table directory.
            layer: Medallion layer name (e.g., ``'silver'``, ``'gold'``) used in log messages.

        Returns:
            Integer Delta table version, or None if the table does not exist or
            resolution fails and strict validation is disabled.
        """
        try:
            table_version: int | None = self._storage.get_table_version(
                table_path,
                layer=layer,
            )
            return table_version
        except self._warning_allowlist as error:
            self._handle_allowlisted_failure(
                error,
                log_fields={
                    "layer": layer,
                    "table_path": table_path,
                },
            )
            return None


__all__ = ["PostrunMetadataVersionResolver"]
