"""PubChem fetch strategies."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, AsyncIterator

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
    from bioetl.infrastructure.adapters.pubchem.entity_mapper import PubChemEntityMapper


class PubChemFetchStrategies:
    """Strategies for fetching compound data from PubChem."""

    def __init__(
        self,
        logger: LoggerPort,
        rate_limiter: TokenBucket,
        circuit_breaker: CircuitBreaker,
        mapper: PubChemEntityMapper,
        run_in_executor: Any,
        provider_name: str = "pubchem",
        request_collector: APIRequestCollector | None = None,
    ) -> None:
        """Initialize strategies."""
        # Use protected members to match test expectations (weird, but tests access _logger)
        self._logger = logger
        self._rate_limiter = rate_limiter
        self._circuit_breaker = circuit_breaker
        self._mapper = mapper
        self._run_in_executor = run_in_executor
        self._provider_name = provider_name
        self.request_collector = request_collector

        # Internal PubChemPy reference
        import pubchempy as pcp
        self.pcp = pcp

    async def fetch_by_cids(
        self, cids: list[str] | None = None, limit: int | None = None, batch_size: int = 50
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch compounds by CIDs in batches."""
        if not cids:
            return

        valid_cids = self._parse_valid_cids(cids)
        if not valid_cids:
            return

        processed_count = 0

        # Batch processing
        for i in range(0, len(valid_cids), batch_size):
            if limit is not None and processed_count >= limit:
                break

            batch = valid_cids[i : i + batch_size]

            # Adjust last batch if limit would be exceeded
            if limit is not None and processed_count + len(batch) > limit:
                batch = batch[: limit - processed_count]

            if not batch:
                 break

            try:
                await self._rate_limiter.acquire()

                compounds = await self._circuit_breaker.call(
                    self._run_in_executor,
                    self.pcp.get_compounds,
                    batch,
                    "cid",
                )

                for compound in compounds:
                    if limit is not None and processed_count >= limit:
                        break
                    yield self._mapper.to_dict(compound)
                    processed_count += 1

                if self.request_collector:
                    self.request_collector.add_success(
                        method="GET",
                        url=f"cid_batch_{i}",
                        status_code=200,
                        response_bytes=1000 * len(compounds),
                    )

            except Exception as e:
                self._logger.warning("cid_batch_fetch_failed", batch_indices=f"{i}-{i+len(batch)}", error=str(e))
                if self.request_collector:
                     self.request_collector.add_error(
                        method="GET",
                        url=f"cid_batch_{i}",
                        error_type=type(e).__name__,
                        error_msg=str(e),
                     )

    async def fetch_by_query(
        self, query: str, limit: int | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch compounds by query."""
        if not query:
            return

        try:
            await self._rate_limiter.acquire()

            compounds = await self._circuit_breaker.call(
                self._run_in_executor,
                self.pcp.get_compounds,
                query,
                "name",
                limit=limit
            )

            count = 0
            for compound in compounds:
                 if limit is not None and count >= limit:
                     break
                 if hasattr(self._mapper, 'compound_to_dict'):
                     yield self._mapper.compound_to_dict(compound)
                 else:
                     yield self._mapper.to_dict(compound)
                 count += 1

        except Exception as e:
            self._logger.warning("pubchem_query_fetch_failed", query=query, error=str(e))

    async def fetch_by_smiles(
        self, smiles: list[str] | str, limit: int | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch by SMILES."""
        if not smiles:
            return

        if isinstance(smiles, str):
            smiles_list = [smiles]
        else:
            smiles_list = smiles

        # Filter empty strings and None
        smiles_list = [s for s in smiles_list if s and s.strip()]

        if not smiles_list:
            return

        count = 0
        for smi in smiles_list:
            if limit is not None and count >= limit:
                break

            try:
                await self._rate_limiter.acquire()
                compounds = await self._circuit_breaker.call(
                    self._run_in_executor,
                    self.pcp.get_compounds,
                    smi,
                    "smiles"
                )

                if compounds:
                    yield self._mapper.to_dict(compounds[0])
                    count += 1
            except Exception as e:
                 self._logger.warning("smiles_fetch_failed", smiles=smi, error=str(e))

    async def fetch_by_inchikey(
        self, inchikeys: list[str], limit: int | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch by InChIKey."""
        count = 0
        for key in inchikeys:
            if limit is not None and count >= limit:
                break

            try:
                await self._rate_limiter.acquire()
                compounds = await self._circuit_breaker.call(
                     self._run_in_executor,
                     self.pcp.get_compounds,
                     key,
                     "inchikey"
                )
                if compounds:
                     yield self._mapper.to_dict(compounds[0])
                     count += 1
            except Exception as e:
                self._logger.debug("pubchem_inchikey_direct_failed", inchikey=key, error=str(e))

    async def fetch_substances(
        self, query: str | None, limit: int | None
    ) -> AsyncIterator[dict[str, Any]]:
         """Fetch substances."""
         if not query:
             raise ValueError("Query is required")

         try:
            await self._rate_limiter.acquire()
            substances = await self._circuit_breaker.call(
                self._run_in_executor,
                self.pcp.get_substances,
                query,
                "name",
                limit=limit
            )
            count = 0
            for substance in substances:
                if limit is not None and count >= limit:
                    break
                if hasattr(self._mapper, 'substance_to_dict'):
                    yield self._mapper.substance_to_dict(substance)
                else:
                    yield self._mapper.to_dict(substance)
                count += 1
         except Exception as e:
             self._logger.warning("pubchem_substance_fetch_failed", query=query, error=str(e))

    async def fetch_assays(
        self, query: str | None, limit: int | None
    ) -> AsyncIterator[dict[str, Any]]:
         """Fetch assays."""
         if not query:
             raise ValueError("Query is required")

         try:
            await self._rate_limiter.acquire()
            assays = await self._circuit_breaker.call(
                self._run_in_executor,
                self.pcp.get_assays,
                query,
                "name",
                limit=limit
            )
            count = 0
            for assay in assays:
                if limit is not None and count >= limit:
                    break
                # Use assay_to_dict if available/mocked
                if hasattr(self._mapper, 'assay_to_dict'):
                    yield self._mapper.assay_to_dict(assay)
                else:
                     yield {"aid": assay.aid}
                count += 1
         except Exception as e:
             self._logger.warning("pubchem_assay_fetch_failed", query=query, error=str(e))

    def _parse_valid_cids(self, cids: list[str]) -> list[int]:
        """Parse valid CIDs from strings."""
        valid = []
        for cid in cids:
            try:
                val = int(cid)
                if val > 0:
                    valid.append(val)
                else:
                     self._logger.warning("invalid_cid_format", cid=cid)
            except (ValueError, TypeError):
                self._logger.warning("invalid_cid_format", cid=cid)
        return valid
