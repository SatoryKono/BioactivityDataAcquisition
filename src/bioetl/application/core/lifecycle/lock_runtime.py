"""Pure/runtime helpers for lock lifecycle coordination."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.config import LockConfig
from bioetl.domain.locking import FencingToken, LockContext
from bioetl.domain.types import RunID, RunType

if TYPE_CHECKING:
    from bioetl.domain.ports import LockPort


def build_lock_config(
    *,
    provider: str,
    entity_type: str,
    run_type: RunType,
    lock_ttl: int,
    wait_for_lock: bool,
    wait_timeout: int,
    heartbeat_interval: int,
) -> LockConfig:
    """Construct the lock configuration used by the lock-coordination flow."""
    return LockConfig.for_pipeline(
        provider=provider,
        entity_type=entity_type,
        run_type=run_type,
        lock_ttl=lock_ttl,
        wait_for_lock=wait_for_lock,
        wait_timeout=wait_timeout,
        heartbeat_interval=heartbeat_interval,
    )


def build_lock_context(
    *,
    config: LockConfig,
    run_id: RunID,
    acquired_at: float | None,
    fencing_token: FencingToken | None,
) -> LockContext | None:
    """Build the writer-facing lock context when a lock is currently held."""
    if acquired_at is None:
        return None
    return LockContext(
        key=config.lock_key,
        owner_id=run_id,
        exclusive=config.exclusive,
        acquired_at=acquired_at,
        fencing_token=fencing_token,
    )


async def validate_lock_ownership(
    *,
    lock_port: LockPort,
    config: LockConfig,
    run_id: RunID,
    fencing_token: FencingToken | None,
) -> bool:
    """Validate current lock ownership using fencing tokens when available."""
    if fencing_token is None:
        result = await lock_port.validate_owner(config.lock_key, run_id)
        return bool(result)
    result = await lock_port.validate_fencing_token(config.lock_key, fencing_token)
    return bool(result)


__all__ = [
    "build_lock_config",
    "build_lock_context",
    "validate_lock_ownership",
]
