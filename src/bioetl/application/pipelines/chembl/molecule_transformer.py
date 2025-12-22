"""ChEMBL Molecule Transformer.

Transforms Bronze records to Silver format (Molecule entity inflation).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, cast

from bioetl.domain.entities import Molecule
from bioetl.domain.transformations import (
    generate_content_hash,
    generate_entity_id,
    safe_int,
)

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord


def _serialize_json(value: Any) -> str | None:
    """Serialize complex values (dict/list) to JSON string."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


class MoleculeTransformer:
    """Transforms ChEMBL bronze molecule records to silver."""

    def __init__(self, provider: str = "chembl"):
        self.provider = provider

    async def transform(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Transform raw ChEMBL molecule to normalized format using Domain Entity."""
        molecule_chembl_id = record.get("molecule_chembl_id")

        if not molecule_chembl_id:
            return None

        try:
            entity_id = generate_entity_id(
                record={"molecule_chembl_id": str(molecule_chembl_id)},
                provider=self.provider,
                id_field="molecule_chembl_id",
            )

            business_data: dict[str, Any] = {
                # Primary identifier
                "molecule_chembl_id": str(molecule_chembl_id),
                # Core metadata
                "pref_name": record.get("pref_name"),
                "molecule_type": record.get("molecule_type"),
                "structure_type": record.get("structure_type"),
                "max_phase": safe_int(record.get("max_phase")),
                "first_approval": safe_int(record.get("first_approval")),
                # Flags
                "oral": record.get("oral"),
                "parenteral": record.get("parenteral"),
                "topical": record.get("topical"),
                "black_box_warning": safe_int(record.get("black_box_warning")),
                "natural_product": safe_int(record.get("natural_product")),
                "first_in_class": safe_int(record.get("first_in_class")),
                "prodrug": safe_int(record.get("prodrug")),
                "therapeutic_flag": record.get("therapeutic_flag"),
                "withdrawn_flag": record.get("withdrawn_flag"),
                "inorganic_flag": safe_int(record.get("inorganic_flag")),
                "polymer_flag": safe_int(record.get("polymer_flag")),
                # Complex fields (JSON serialized)
                "molecule_hierarchy": _serialize_json(record.get("molecule_hierarchy")),
                "molecule_properties": _serialize_json(record.get("molecule_properties")),
                "molecule_structures": _serialize_json(record.get("molecule_structures")),
                "molecule_synonyms": _serialize_json(record.get("molecule_synonyms")),
                "cross_references": _serialize_json(record.get("cross_references")),
                "atc_classifications": _serialize_json(record.get("atc_classifications")),
            }

            content_hash = generate_content_hash(
                business_data,
                self.provider,
                exclude_none=True,
            )

            entity = Molecule(
                entity_id=entity_id,
                content_hash=content_hash,
                run_id=context.run_id,
                run_type=context.run_type,
                source_batch_id=None,
                **business_data,
            )

        except ValueError as e:
            context.logger.warning(
                "entity_validation_failed",
                error=str(e),
                molecule_chembl_id=molecule_chembl_id,
            )
            return None

        # Convert Entity to SilverRecord for storage
        silver_record = entity.__dict__.copy()

        # Handle lineage fields renaming and formatting
        silver_record["_run_id"] = str(silver_record.pop("run_id"))
        silver_record["_run_type"] = str(silver_record.pop("run_type").value)
        silver_record["_source_batch_id"] = str(silver_record.pop("source_batch_id"))
        silver_record["_ingestion_ts"] = silver_record.pop("ingestion_ts").isoformat()

        return cast("SilverRecord", silver_record)
