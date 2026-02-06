"""PubChem fetch strategy implementations (Infrastructure Layer)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.pubchem.client import PubChemClient


class FetchStrategy(ABC):
    """Abstract base class for fetch strategies."""

    def __init__(self, client: PubChemClient, logger: LoggerPort) -> None:
        """Initialize strategy.

        Args:
            client: PubChem API client.
            logger: Logger instance.
        """
        self.client = client
        self.logger = logger

    @abstractmethod
    def fetch(self, identifier: str) -> dict[str, Any] | None:
        """Fetch compound data by identifier."""
        pass


class CidFetchStrategy(FetchStrategy):
    """Strategy to fetch by CID directly."""

    def fetch(self, identifier: str) -> dict[str, Any] | None:
        """Fetch compound by CID."""
        try:
            return self.client.get_compound_by_cid(identifier)
        except Exception as e:
            self.logger.warning(
                "pubchem_cid_fetch_failed",
                cid=identifier,
                error=str(e),
            )
            return None


class NameFetchStrategy(FetchStrategy):
    """Strategy to fetch by name (synonym)."""

    def fetch(self, identifier: str) -> dict[str, Any] | None:
        """Fetch compound by name."""
        try:
            return self.client.get_compound_by_name(identifier)
        except Exception as e:
            self.logger.warning(
                "pubchem_name_fetch_failed",
                name=identifier,
                error=str(e),
            )
            return None


class InchiKeyFetchStrategy(FetchStrategy):
    """Strategy to fetch by InChIKey."""

    def fetch(self, identifier: str) -> dict[str, Any] | None:
        """Fetch compound by InChIKey."""
        # 1. Try direct API lookup
        try:
            compound = self.client.get_compound_by_inchikey(identifier)
            if compound:
                return compound
        except Exception as e:
            self.logger.debug(
                "pubchem_inchikey_direct_failed",
                inchikey=identifier,
                error=str(e),
            )

        # 2. Fallback: Search PUG REST for CIDs, then fetch first CID
        return self._fetch_via_cids(identifier)

    def _fetch_via_cids(self, inchikey: str) -> dict[str, Any] | None:
        """Fetch compound via CIDs lookup."""
        try:
            cids = self.client.search_cids_by_inchikey(inchikey)
            if not cids:
                return None

            # Use the first CID
            best_cid = str(cids[0])
            self.logger.info(
                "pubchem_inchikey_resolved_to_cid",
                inchikey=inchikey,
                cid=best_cid,
            )
            return self.client.get_compound_by_cid(best_cid)

        except Exception as e:
            self.logger.warning(
                "pubchem_inchikey_fallback_failed",
                inchikey=inchikey,
                error=str(e),
            )
            return None


class SmilesFetchStrategy(FetchStrategy):
    """Strategy to fetch by SMILES."""

    def fetch(self, identifier: str) -> dict[str, Any] | None:
        """Fetch compound by SMILES."""
        # SMILES lookup in PUG REST is typically done via POST or long-poll,
        # but basic support exists via GET for simple SMILES.
        # Implementation depends on client capabilities.
        try:
            # Assuming client has this method or we implement similar to InChIKey
            # For now, let's assume we search CIDs first
            cids = self.client.search_cids_by_smiles(identifier)
            if not cids:
                return None

            best_cid = str(cids[0])
            return self.client.get_compound_by_cid(best_cid)

        except Exception as e:
            self.logger.warning(
                "pubchem_smiles_fetch_failed",
                smiles=identifier,
                error=str(e),
            )
            return None
