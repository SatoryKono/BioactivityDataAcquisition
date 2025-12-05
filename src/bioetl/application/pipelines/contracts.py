"""
Contracts for pipeline components.
"""
from abc import ABC, abstractmethod
from typing import Any, Iterable

import pandas as pd


class ExtractorABC(ABC):
    """
    Component responsible for extracting data from source.
    """

    @abstractmethod
    def extract(self, **kwargs: Any) -> Iterable[pd.DataFrame]:
        """
        Yields chunks of data.
        """


class LoaderABC(ABC):
    """
    Component responsible for loading data to destination.
    """

    @abstractmethod
    def load(self, df: pd.DataFrame, **kwargs: Any) -> None:
        """
        Loads data to destination.
        """

