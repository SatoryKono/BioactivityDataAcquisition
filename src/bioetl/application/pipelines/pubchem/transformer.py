"""PubChem Compound Transformer.

Transforms raw PubChem compound records into Silver-layer format using
the Compound domain entity for validation and invariant checking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities import Compound
from bioetl.domain.transformations import generate_entity_id

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import MetricsPort, TracingPort
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
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
    ):
        """Initialize PubChem compound transformer.

        Args:
            provider: Data provider identifier.
            tracer: Optional tracing port for distributed tracing (O1 observability).
            metrics: Optional metrics port for duration/error tracking (O1 observability).
            gold_filters: Optional filter configuration for Gold layer.

        """
        super().__init__(
            provider, tracer=tracer, metrics=metrics, gold_filters=gold_filters
        )

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Transform raw PubChem record to Silver format.

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from PubChem.

        Returns:
            SilverRecord if transformation successful, None if skipped.

        Raises:
            TransformationError: If cid is missing.
            ValueError: If Compound entity validation fails.

        """
        # Step 1: Validate required field
        cid = self._get_required_field(record, "cid")

        # Step 2: Build business data dictionary
        business_data: dict[str, Any] = {
            "cid": str(cid),
            "molecular_formula": record.get("molecular_formula"),
            "molecular_weight": record.get("molecular_weight"),
            "canonical_smiles": record.get("canonical_smiles"),
            "isomeric_smiles": record.get("isomeric_smiles"),
            "inchi": record.get("inchi"),
            "inchikey": record.get("inchikey"),
            "iupac_name": record.get("iupac_name"),
        }

        # Step 3: Generate entity_id (RULES.md §2.8)
        entity_id = generate_entity_id(
            record={"cid": cid},
            provider=self.provider,
            id_field="cid",
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
            **business_data,
        )

        # Step 6: Convert to SilverRecord with lineage field renaming
        return cast("SilverRecord", self.entity_to_silver_record(entity))
