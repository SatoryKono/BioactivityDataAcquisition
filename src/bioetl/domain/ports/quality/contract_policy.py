"""Port for pipeline contract policy access.

Defines the minimal contract-policy shape used by application
transformers for field renaming and content-hash field selection.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable

__all__ = ["ContractPolicyProtocol"]


@runtime_checkable
class ContractPolicyProtocol(Protocol):
    """Protocol for pipeline contract policy objects.

    Implementations may come from infrastructure schemas or test doubles,
    but application code depends only on this port.
    """

    @property
    def primary_key(self) -> Sequence[str]:
        """Return primary key fields."""
        ...

    @property
    def merge_keys(self) -> Sequence[str]:
        """Return merge key fields."""
        ...

    @property
    def hash_include(self) -> Sequence[str]:
        """Return explicit include fields for content hash calculation."""
        ...

    @property
    def hash_exclude(self) -> Sequence[str]:
        """Return fields excluded from content hash calculation."""
        ...

    @property
    def rename_map(self) -> Mapping[str, str]:
        """Return source-to-target field rename mapping."""
        ...
