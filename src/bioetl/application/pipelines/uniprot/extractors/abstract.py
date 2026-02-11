"""Abstract base class for UniProt extractors."""

from abc import ABC, abstractmethod
from typing import Any


class AbstractExtractor(ABC):
    """Base class for all UniProt extractors."""

    @abstractmethod
    def extract(self, entry: Any) -> Any:
        """Extract data from a UniProt entry.

        Args:
            entry: The source data entry (XML element or dict).

        Returns:
            Extracted data structure.
        """
        pass
