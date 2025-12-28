"""GtoPdb Ligand Transformer.

Transforms raw GtoPdb ligand records into Silver-layer format using
the GtopdbLigand domain entity for validation and invariant checking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities import GtopdbLigand
from bioetl.domain.transformations import generate_entity_id

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import MetricsPort, TracingPort
    from bioetl.domain.types import BronzeRecord, SilverRecord


class GtopdbLigandTransformer(BaseTransformer):
    """Transformer for GtoPdb ligand records.

    Uses GtopdbLigand domain entity for validation and lineage tracking.

    GtoPdb API field mapping:
    - ligandId -> ligand_id
    - name -> name
    - type -> ligand_type
    - approved -> approved
    - smiles -> smiles
    - inchi -> inchi
    - inchiKey -> inchi_key
    - pubchemSid -> pubchem_sid
    - pubchemCid -> pubchem_cid
    - chemblId -> chembl_id
    """

    def __init__(
        self,
        provider: str = "gtopdb",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
    ):
        """Initialize GtoPdb ligand transformer.

        Args:
            provider: Data provider identifier.
            tracer: Optional tracing port for distributed tracing.
            metrics: Optional metrics port for duration/error tracking.
            gold_filters: Optional filter configuration for Gold layer.
        """
        super().__init__(
            provider,
            entity_type="ligand",
            tracer=tracer,
            metrics=metrics,
            gold_filters=gold_filters,
        )

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Transform raw GtoPdb ligand record to Silver format.

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from GtoPdb.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if skipped.

        Raises:
            TransformationError: If ligandId is missing.
            ValueError: If GtopdbLigand entity validation fails.
        """
        # Step 1: Validate required field
        ligand_id = self._get_required_field(record, "ligandId")

        # Step 2: Build business data dictionary with field mapping
        business_data: dict[str, Any] = {
            "ligand_id": int(ligand_id),
            "name": record.get("name"),
            "ligand_type": record.get("type"),
            "approved": self._safe_bool(record.get("approved")),
            "withdrawn": self._safe_bool(record.get("withdrawn")),
            "labelled": self._safe_bool(record.get("labelled")),
            "radioactive": self._safe_bool(record.get("radioactive")),
            # Structural information
            "smiles": record.get("smiles"),
            "inchi": record.get("inchi"),
            "inchi_key": record.get("inchiKey"),
            "iupac_name": record.get("iupacName"),
            # Drug status
            "inn": record.get("inn"),
            "approved_source": record.get("approvedSource"),
            # Species
            "species": record.get("species"),
            # Cross-references
            "pubchem_sid": self._safe_int(record.get("pubchemSid")),
            "pubchem_cid": self._safe_int(record.get("pubchemCid")),
            "chembl_id": record.get("chemblId"),
            "drugbank_id": record.get("drugbankId"),
            "cas_number": record.get("casNumber"),
            # Comments
            "comments": record.get("comments"),
        }

        # Step 3: Generate entity_id
        entity_id = generate_entity_id(
            record={"ligandId": ligand_id},
            provider=self.provider,
            id_field="ligandId",
        )

        # Step 4: Compute content_hash
        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        # Step 5: Create domain entity with lineage metadata
        entity = self._create_entity(
            GtopdbLigand,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )

        # Step 6: Convert to SilverRecord with lineage field renaming
        return cast("SilverRecord", self.entity_to_silver_record(entity))

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        """Safely convert value to int, returning None if invalid."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_bool(value: Any) -> bool | None:
        """Safely convert value to bool, returning None if invalid."""
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "yes", "1")
        return bool(value)
