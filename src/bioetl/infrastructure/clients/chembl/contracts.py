from abc import abstractmethod
from typing import Any

from bioetl.infrastructure.clients.base.contracts import SourceClientABC


class ChemblDataClientABC(SourceClientABC):
    """
    Контракт клиента ChEMBL.
    """
    
    @abstractmethod
    def request_activity(self, **filters: Any) -> Any:
        """Запрос к эндпоинту activity."""

    @abstractmethod
    def request_assay(self, **filters: Any) -> Any:
        """Запрос к эндпоинту assay."""

    @abstractmethod
    def request_target(self, **filters: Any) -> Any:
        """Запрос к эндпоинту target."""
    
    @abstractmethod
    def request_document(self, **filters: Any) -> Any:
        """Запрос к эндпоинту document."""
        
    @abstractmethod
    def request_molecule(self, **filters: Any) -> Any:
        """Запрос к эндпоинту molecule."""

