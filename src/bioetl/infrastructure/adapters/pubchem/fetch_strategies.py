"""PubChem fetch strategies."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.pubchem.client import PubChemClient


class PubChemFetchStrategies:
    """Strategies for fetching compound data from PubChem."""

    def __init__(self, client: "PubChemClient", logger: "LoggerPort") -> None:
        """Initialize strategies.

        Args:
            client: PubChem API client
            logger: Logger instance
        """
        self.client = client
        self.logger = logger

    def fetch_by_cid(self, cid: str) -> dict[str, Any] | None:
        """Fetch by Compound ID."""
        try:
            return self.client.get_compound_by_cid(cid)
        except Exception as e:
            self.logger.warning("pubchem_cid_fetch_failed", cid=cid, error=str(e))
            return None

    def fetch_by_name(self, name: str) -> dict[str, Any] | None:
        """Fetch by name."""
        try:
            return self.client.get_compound_by_name(name)
        except Exception as e:
            self.logger.warning("pubchem_name_fetch_failed", name=name, error=str(e))
            return None

    def fetch_by_inchikey(self, inchikey: str) -> dict[str, Any] | None:
        """Fetch by InChIKey."""
        # 1. Try direct API lookup
        try:
            compound = self.client.get_compound_by_inchikey(inchikey)
            if compound:
                return compound
        except Exception as e:
            self.logger.debug(
                "pubchem_inchikey_direct_failed", inchikey=inchikey, error=str(e)
            )

        # 2. Fallback: Search PUG REST for CIDs
        return self._fetch_via_cids(inchikey)

    def _fetch_via_cids(self, inchikey: str) -> dict[str, Any] | None:
        """Fetch compound via CIDs lookup."""
        try:
            cids = self.client.search_cids_by_inchikey(inchikey)
            if not cids:
                return None

            # Use the first CID
            best_cid = str(cids[0])
            self.logger.info(
                "pubchem_inchikey_resolved_to_cid", inchikey=inchikey, cid=best_cid
            )
            return self.client.get_compound_by_cid(best_cid)

        except Exception as e:
            self.logger.warning(
                "pubchem_inchikey_fallback_failed", inchikey=inchikey, error=str(e)
            )
            return None

    def fetch_by_smiles(self, smiles: str) -> dict[str, Any] | None:
        """Fetch by SMILES."""
        try:
            cids = self.client.search_cids_by_smiles(smiles)
            if not cids:
                return None

            best_cid = str(cids[0])
            return self.client.get_compound_by_cid(best_cid)

        except Exception as e:
            self.logger.warning(
                "pubchem_smiles_fetch_failed", smiles=smiles, error=str(e)
            )
            return None

    def health_check(self) -> bool:
        """Perform a health check for the fetch strategies."""
        # Since this class relies on the client which should have its own health check,
        # we can perform a minimal check or just return True if initialized.
        # Ideally, we might check if the client is responsive.
        return True
