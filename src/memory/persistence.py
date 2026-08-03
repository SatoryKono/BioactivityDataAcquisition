"""Central persistence-mode contract for the project memory subsystem."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

MEMORY_MODE_ENV_VAR = "BIOETL_AI_MEMORY_MODE"


class PersistenceMode(StrEnum):
    """Supported persistent-memory operating modes."""

    OFF = "off"
    READ_ONLY = "read-only"
    READ_WRITE = "read-write"


class PersistenceDisabledError(PermissionError):
    """Raised when a write is forbidden by the active persistence mode."""


@dataclass(frozen=True, slots=True)
class PersistencePolicy:
    """Resolved capabilities for an explicit memory persistence mode."""

    mode: PersistenceMode

    @property
    def can_read(self) -> bool:
        """Whether existing persistent memory may be read."""
        return self.mode is not PersistenceMode.OFF

    @property
    def can_write(self) -> bool:
        """Whether persistent memory may be changed."""
        return self.mode is PersistenceMode.READ_WRITE

    def require_read(self) -> None:
        """Raise when persistent reads are disabled."""
        if not self.can_read:
            raise PersistenceDisabledError("persistent memory reads are disabled")

    def require_write(self) -> None:
        """Raise when persistent writes are disabled."""
        if not self.can_write:
            raise PersistenceDisabledError(
                f"persistent memory writes are disabled in {self.mode.value} mode"
            )


_MODE_ALIASES = {
    "off": PersistenceMode.OFF,
    "disabled": PersistenceMode.OFF,
    "read-only": PersistenceMode.READ_ONLY,
    "readonly": PersistenceMode.READ_ONLY,
    "ro": PersistenceMode.READ_ONLY,
    "read-write": PersistenceMode.READ_WRITE,
    "readwrite": PersistenceMode.READ_WRITE,
    "rw": PersistenceMode.READ_WRITE,
}


def resolve_persistence_policy(
    value: str | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> PersistencePolicy:
    """Resolve the memory mode deterministically, rejecting unknown values."""
    environment = os.environ if environ is None else environ
    raw_value = value if value is not None else environment.get(MEMORY_MODE_ENV_VAR)
    normalized = (raw_value or PersistenceMode.READ_WRITE.value).strip().lower()
    try:
        mode = _MODE_ALIASES[normalized]
    except KeyError as exc:
        allowed = ", ".join(mode.value for mode in PersistenceMode)
        raise ValueError(
            f"invalid {MEMORY_MODE_ENV_VAR} value; expected one of: {allowed}"
        ) from exc
    return PersistencePolicy(mode=mode)
