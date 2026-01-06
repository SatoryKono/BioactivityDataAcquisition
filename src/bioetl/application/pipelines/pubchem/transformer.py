"""PubChem Compound Transformer.

Transforms raw PubChem compound records into Silver-layer format using
the Compound domain entity for validation and invariant checking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities import Compound
from bioetl.domain.services import IdentityService

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import MetricsPort, PiiHasherPort, TracingPort
    from bioetl.domain.types import BronzeRecord, SilverRecord


class PubChemCompoundTransformer(BaseTransformer):
    """Transformer for PubChem compound records.

    Uses Compound domain entity for validation and lineage tracking.
    Records without structural identifiers (SMILES/InChI) are skipped
    per entity invariant validation.
    """

    def __init__(
        self,
        provider: str = "pubchem",
        entity_type: str = "compound",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
    ):
        """Initialize PubChem compound transformer.

        Args:
            provider: Data provider identifier. Defaults to 'pubchem'.
            entity_type: Entity type for metrics labels. Defaults to 'compound'.
            tracer: Optional tracing port for distributed tracing (O1 observability).
            metrics: Optional metrics port for duration/error tracking (O1 observability).
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
            pii_hasher: Optional PII hasher. Not typically used for compounds
                (no PII in chemical data), but included for API consistency.

        """
        super().__init__(
            provider,
            entity_type=entity_type,
            tracer=tracer,
            metrics=metrics,
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
        )

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Transform raw PubChem record to Silver format.

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from PubChem.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if skipped.

        Raises:
            TransformationError: If cid is missing.
            ValueError: If Compound entity validation fails.

        """
        # Step 1: Validate required field
        cid = self._get_required_field(record, "cid")

        # Step 2: Build business data dictionary
        # Note: molecular_weight is converted to string to match Silver schema
        mol_weight = record.get("molecular_weight")
        business_data: dict[str, Any] = {
            "cid": str(cid),
            "molecular_formula": record.get("molecular_formula"),
            "molecular_weight": str(mol_weight) if mol_weight is not None else None,
            "canonical_smiles": record.get("canonical_smiles"),
            "isomeric_smiles": record.get("isomeric_smiles"),
            "inchi": record.get("inchi"),
            "inchikey": record.get("inchikey"),
            "iupac_name": record.get("iupac_name"),
        }

        # Step 3: Generate entity_id using IdentityService (RULES.md §2.8)
        entity_id = self.compute_entity_id(
            source_id=str(cid),
            record={"cid": cid},
        )

        # Step 4: Compute content_hash (RULES.md §2.8.1)
        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        # Step 5: Create domain entity with lineage metadata
        # ValueError is raised if invariants fail (e.g., no structural identifiers)
        entity = self._create_entity(
            Compound,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )

        # Step 6: Convert to SilverRecord with lineage field renaming
        return cast("SilverRecord", self.entity_to_silver_record(entity))
