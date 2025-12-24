"""PubChem Compound Transformer."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.transformations import generate_entity_id

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord


class PubChemCompoundTransformer(BaseTransformer):
    """Transformer for PubChem compound records."""

    def __init__(self, provider: str = "pubchem"):
        super().__init__(provider)

    async def _transform_impl(
        self,
        _context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Transform raw PubChem record to Silver format."""
        # Validate required field
        cid = self._get_required_field(record, "cid")

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
        content_hash = self.compute_content_hash(normalized, exclude_none=False)
        normalized["content_hash"] = content_hash

        return cast("SilverRecord", normalized)
