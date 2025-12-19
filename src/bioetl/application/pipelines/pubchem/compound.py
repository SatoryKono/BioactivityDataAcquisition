"""PubChem Compound Pipeline Implementation."""
from __future__ import annotations

from typing import Any, cast

from bioetl.application.core.base import BasePipeline
from bioetl.domain.context import PipelineContext
from bioetl.domain.transformations import generate_content_hash, generate_entity_id
from bioetl.domain.types import BronzeRecord, SilverRecord, Watermark


class PubChemCompoundPipeline(BasePipeline):
    """Pipeline for processing PubChem compounds."""

    # create method removed (DRY)

    async def transform_bronze_to_silver(
        self, context: PipelineContext, record: BronzeRecord
    ) -> SilverRecord | None:
        """Transform raw PubChem record to Silver format."""
        cid = record.get("cid")
        if not cid:
            return None

        normalized = {
            "cid": str(cid),
            "molecular_formula": record.get("molecular_formula"),
            "molecular_weight": record.get("molecular_weight"),
            "canonical_smiles": record.get("canonical_smiles"),
            "isomeric_smiles": record.get("isomeric_smiles"),
            "inchi": record.get("inchi"),
            "inchikey": record.get("inchikey"),
            "iupac_name": record.get("iupac_name"),
        }

        # Генерация entity_id согласно RULES.md §2.8
        entity_id = generate_entity_id(
            record={"cid": cid},
            provider=self.provider,
            id_field="cid",
        )
        normalized["entity_id"] = entity_id

        # Генерация content_hash согласно RULES.md §2.8.1
        content_hash = generate_content_hash(normalized, self.provider)
        normalized["content_hash"] = content_hash

        return cast("SilverRecord", normalized)

    def extract_watermark(
        self, context: PipelineContext, record: dict[str, Any]
    ) -> Watermark:
        """Extract CID as watermark (обёртка Watermark)."""
        return Watermark.from_offset(int(record.get("cid", 0)))
