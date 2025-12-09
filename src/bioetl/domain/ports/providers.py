"""Contracts for field providers."""

from typing import Protocol


class DefaultFieldProviderABC(Protocol):
    """Interface for providing default fields for entity extraction."""

    def get_default_fields(self, entity: str) -> list[str]:
        """
        Get default fields for a given entity.

        Args:
            entity: The entity name (e.g., 'assay', 'activity').

        Returns:
            List of field names to request from the source.
        """
        ...
