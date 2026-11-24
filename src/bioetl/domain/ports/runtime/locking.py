"""Locking port for runtime coordination.

This port defines lock ownership and liveness checks used by pipeline runtime
coordination. In the current Local-Only profile, implementations are
process-local; the port remains an extension point for broader coordination
backends if the deployment profile changes.

Terminology note: older project docs used broader lock wording for this
surface. The runtime semantics are unchanged; only wording was clarified.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bioetl.domain.locking import FencingToken
from bioetl.domain.types import RunID

__all__ = [
    "LockPort",
]


@runtime_checkable
class LockPort(Protocol):
    """Port for runtime locking.

    The protocol models lock acquisition, liveness, and ownership validation
    for pipeline execution coordination.

    Implementations must make acquisition non-reentrant per key, including
    for the current owner, and must not release another owner's lock. These
    guarantees apply within the coordination scope of the implementation.
    A successful pre-write validation is a point-in-time check, not an atomic
    guarantee that ownership persists through a subsequent storage write.
    """

    async def acquire(
        self,
        key: str,
        owner_id: RunID,
        ttl: int | None = None,
        wait: bool = False,
        wait_timeout: int = 300,
        exclusive: bool = False,
    ) -> FencingToken | None:
        """Acquire a lock.

        Args:
            key: The unique key for the lock.
            owner_id: The ID of the run attempting to acquire the lock.
            ttl: Time-to-live for the lock in seconds. When ``ttl`` is ``None``,
                the adapter does not schedule TTL expiry (lock held until
                explicit release or process teardown). When ``ttl`` is a positive
                int, adapters that support TTL expire the lock after that many
                seconds of wall time.
            wait: If True, wait for the lock to be released if it's already held,
                including when it is held by the same owner.
            wait_timeout: Maximum time to wait for the lock in seconds.
            exclusive: If True, acquire an exclusive lock.

        Returns:
            FencingToken if the lock was acquired, None otherwise.
            The token contains a monotonically increasing sequence number
            that can be used for fencing validation.
        """
        ...

    async def release(
        self,
        key: str,
        owner_id: RunID,
        exclusive: bool = False,
    ) -> bool:
        """Release a lock.

        Args:
            key: The unique key for the lock.
            owner_id: The ID of the run releasing the lock.
            exclusive: If True, release an exclusive lock.

        Returns:
            True if the lock was released, False if missing or held by another
            owner.
        """
        ...

    async def heartbeat(
        self,
        key: str,
        owner_id: RunID,
        exclusive: bool = False,
    ) -> bool:
        """Refresh a lock's TTL to prevent it from expiring.

        Args:
            key: The unique key for the lock.
            owner_id: The ID of the run refreshing the lock.
            exclusive: If True, refresh an exclusive lock.

        Returns:
            True if the heartbeat was successful, False otherwise.
        """
        ...

    async def validate_owner(
        self,
        key: str,
        owner_id: RunID,
    ) -> bool:
        """Validate that the given owner_id holds the lock.

        This is the Safety Guard: before writing to storage, the writer
        MUST validate that it still holds the lock. A successful check cannot
        prevent ownership changing between validation and the subsequent write;
        storage-enforced fencing is needed to reject writes in that interval.

        Args:
            key: The unique key for the lock.
            owner_id: The ID of the run to validate.

        Returns:
            True if owner_id currently holds the lock, False otherwise.
        """
        ...

    async def validate_fencing_token(
        self,
        key: str,
        token: FencingToken,
    ) -> bool:
        """Validate that the given fencing token is still valid for the lock.

        Writers SHOULD validate the token before writes to detect stale lock
        holders. As with owner validation, this is a point-in-time check, not
        an atomic fence on a subsequent storage write.

        Args:
            key: The unique key for the lock.
            token: Fencing token issued by acquire().

        Returns:
            True if the fencing token is valid for the current lock holder.
        """
        ...

    async def aclose(self) -> None:
        """Gracefully close the lock connection and release resources."""
        ...
