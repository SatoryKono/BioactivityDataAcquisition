"""Validation service contracts for application layer."""
from abc import ABC, abstractmethod
import pandas as pd


class ValidationServiceABC(ABC):
    """Validate DataFrame payloads using registered schemas.

    Implementations should delegate to domain validation logic and enforce
    stable schema selection for each entity.
    """

    @abstractmethod
    def validate(self, df: pd.DataFrame, entity_name: str) -> pd.DataFrame:
        """Validate and return DataFrame for given entity."""
