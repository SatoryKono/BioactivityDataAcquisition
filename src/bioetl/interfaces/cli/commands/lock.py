"""Lock management commands for BioETL CLI.

Implements lock release and inspection commands.
Note: Uses in-memory locking - operations only affect current process.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast
from uuid import UUID

from bioetl.domain.types import RunID
from bioetl.interfaces.cli.commands.domains.shared.click_options import (
    typed_click_group,
    typed_click_option,
    typed_group_command,
)
from bioetl.interfaces.cli.formatters import echo_error, echo_info, echo_warning

if TYPE_CHECKING:
    from bioetl.application.services.ops.lock_service import LockService

__all__ = [
    "COMMANDS",
    "check_command",
    "lock",
    "release_command",
]


@typed_click_group()
def lock() -> None:
    """Manage pipeline locks."""


def get_lock_service() -> LockService:
    """Load the lock service through composition on demand."""
    from bioetl.composition.control_plane_service_access import (
        get_lock_service as _impl,
    )

    return _impl()


@typed_group_command(lock, "release")
@typed_click_option("--pipeline", required=True, help="Pipeline name (lock key)")
@typed_click_option("--run-id", required=True, help="Run ID that holds the lock")
@typed_click_option("--exclusive", is_flag=True, help="Release exclusive lock")
def release_command(pipeline: str, run_id: str, exclusive: bool) -> None:
    """Release a pipeline lock.

    Use this to clean up stale locks from crashed processes.
    Only works if the specified run-id holds the lock.

    Examples:

        bioetl lock release --pipeline chembl_activity --run-id abc123

        bioetl lock release --pipeline chembl_activity --run-id abc123 --exclusive

    Args:
        pipeline: Pipeline.
        run_id: Pipeline run identifier.
        exclusive: Whether to exclusive.
    """
    try:
        parsed_run_id = cast(RunID, UUID(run_id))
    except ValueError:
        echo_error("Invalid run-id", "Must be a valid UUID")
        return

    service = get_lock_service()

    async def _run() -> None:
        released = await service.release_lock(
            pipeline_id=pipeline,
            owner_id=parsed_run_id,
            exclusive=exclusive,
        )

        if released:
            echo_info(f"Lock released for {pipeline}")
        else:
            echo_warning(f"Lock not released (not held by run-id {run_id})")

    asyncio.run(_run())


@typed_group_command(lock, "check")
@typed_click_option("--pipeline", required=True, help="Pipeline name (lock key)")
@typed_click_option("--run-id", required=True, help="Run ID to check")
def check_command(pipeline: str, run_id: str) -> None:
    """Check if a lock is held by a specific run-id.

    Examples:

        bioetl lock check --pipeline chembl_activity --run-id abc123

    Args:
        pipeline: Pipeline.
        run_id: Pipeline run identifier.
    """
    try:
        parsed_run_id = cast(RunID, UUID(run_id))
    except ValueError:
        echo_error("Invalid run-id", "Must be a valid UUID")
        return

    service = get_lock_service()

    async def _run() -> None:
        is_held = await service.check_lock(
            pipeline_id=pipeline,
            owner_id=parsed_run_id,
        )

        if is_held:
            echo_info(f"Lock for {pipeline} IS held by run-id {run_id}")
        else:
            echo_info(f"Lock for {pipeline} is NOT held by run-id {run_id}")

    asyncio.run(_run())


COMMANDS = (release_command, check_command)
