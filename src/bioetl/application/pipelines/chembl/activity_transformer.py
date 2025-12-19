"""ChEMBL Activity Transformer.

Transforms Bronze records to Silver format (Activity entity inflation).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from bioetl.domain.entities import Activity
from bioetl.domain.transformations import (
    generate_content_hash,
    generate_entity_id,
    safe_float,
    safe_int,
)
from bioetl.domain.types import BronzeRecord, SilverRecord

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext


def _serialize_json(value: Any) -> str | None:
    """Serialize complex values (dict/list) to JSON string."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


class ActivityTransformer:
    """Transforms ChEMBL bronze records to silver."""

    def __init__(self, provider: str = "chembl"):
        self.provider = provider

    async def transform(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Transform raw ChEMBL activity to normalized format using Domain Entity."""
        activity_id = record.get("activity_id")
        molecule_id = record.get("molecule_chembl_id")

        if not activity_id or not molecule_id:
            return None

        # 1. Prepare data for Entity inflation
        try:
            entity_id = generate_entity_id(
                record={"activity_id": str(activity_id)},
                provider=self.provider,
                id_field="activity_id",
            )

            # Map ALL raw fields to Entity fields
            business_data: dict[str, Any] = {
                # Primary identifier
                "activity_id": str(activity_id),
                # Core identifiers
                "molecule_chembl_id": str(molecule_id),
                "target_chembl_id": record.get("target_chembl_id"),
                "assay_chembl_id": record.get("assay_chembl_id"),
                "document_chembl_id": record.get("document_chembl_id"),
                "record_id": safe_int(record.get("record_id")),
                "src_id": safe_int(record.get("src_id")),
                # Molecule data
                "canonical_smiles": record.get("canonical_smiles"),
                "molecule_pref_name": record.get("molecule_pref_name"),
                "parent_molecule_chembl_id": record.get("parent_molecule_chembl_id"),
                # Target data
                "target_pref_name": record.get("target_pref_name"),
                "target_organism": record.get("target_organism"),
                "target_tax_id": record.get("target_tax_id"),
                # Assay data
                "assay_type": record.get("assay_type"),
                "assay_description": record.get("assay_description"),
                "assay_variant_accession": record.get("assay_variant_accession"),
                "assay_variant_mutation": record.get("assay_variant_mutation"),
                # BAO annotations
                "bao_endpoint": record.get("bao_endpoint"),
                "bao_format": record.get("bao_format"),
                "bao_label": record.get("bao_label"),
                # Raw activity values
                "type": record.get("type"),
                "value": safe_float(record.get("value")),
                "units": record.get("units"),
                "relation": record.get("relation"),
                "upper_value": safe_float(record.get("upper_value")),
                "text_value": record.get("text_value"),
                # Standardized activity values
                "standard_type": record.get("standard_type"),
                "standard_value": safe_float(record.get("standard_value")),
                "standard_units": record.get("standard_units"),
                "standard_relation": record.get("standard_relation"),
                "standard_upper_value": safe_float(record.get("standard_upper_value")),
                "standard_text_value": record.get("standard_text_value"),
                "standard_flag": safe_int(record.get("standard_flag")),
                # Derived metrics
                "pchembl_value": safe_float(record.get("pchembl_value")),
                "ligand_efficiency": _serialize_json(record.get("ligand_efficiency")),
                # Units ontology
                "qudt_units": record.get("qudt_units"),
                "uo_units": record.get("uo_units"),
                # Document data
                "document_journal": record.get("document_journal"),
                "document_year": safe_int(record.get("document_year")),
                # Quality annotations
                "activity_comment": record.get("activity_comment"),
                "data_validity_comment": record.get("data_validity_comment"),
                "data_validity_description": record.get("data_validity_description"),
                "potential_duplicate": safe_int(record.get("potential_duplicate")),
                # Action and properties
                "action_type": record.get("action_type"),
                "activity_properties": _serialize_json(record.get("activity_properties")),
                "toid": safe_int(record.get("toid")),
            }

            # Generate content hash based on business data (exclude None values)
            content_hash = generate_content_hash(
                {k: v for k, v in business_data.items() if v is not None},
                self.provider,
            )

            entity = Activity(
                entity_id=entity_id,
                content_hash=content_hash,
                run_id=context.run_id,
                run_type=context.run_type,
                source_batch_id="UNKNOWN",
                **business_data,
            )

        except ValueError as e:
            context.logger.warning(
                "entity_validation_failed", error=str(e), activity_id=activity_id
            )
            return None

        # 2. Convert Entity to SilverRecord for storage (all 52 fields)
        silver_record: dict[str, Any] = {
            # System fields
            "entity_id": entity.entity_id,
            "content_hash": entity.content_hash,
            # Primary identifier
            "activity_id": entity.activity_id,
            # Core identifiers
            "molecule_chembl_id": entity.molecule_chembl_id,
            "target_chembl_id": entity.target_chembl_id,
            "assay_chembl_id": entity.assay_chembl_id,
            "document_chembl_id": entity.document_chembl_id,
            "record_id": entity.record_id,
            "src_id": entity.src_id,
            # Molecule data
            "canonical_smiles": entity.canonical_smiles,
            "molecule_pref_name": entity.molecule_pref_name,
            "parent_molecule_chembl_id": entity.parent_molecule_chembl_id,
            # Target data
            "target_pref_name": entity.target_pref_name,
            "target_organism": entity.target_organism,
            "target_tax_id": entity.target_tax_id,
            # Assay data
            "assay_type": entity.assay_type,
            "assay_description": entity.assay_description,
            "assay_variant_accession": entity.assay_variant_accession,
            "assay_variant_mutation": entity.assay_variant_mutation,
            # BAO annotations
            "bao_endpoint": entity.bao_endpoint,
            "bao_format": entity.bao_format,
            "bao_label": entity.bao_label,
            # Raw activity values
            "type": entity.type,
            "value": entity.value,
            "units": entity.units,
            "relation": entity.relation,
            "upper_value": entity.upper_value,
            "text_value": entity.text_value,
            # Standardized activity values
            "standard_type": entity.standard_type,
            "standard_value": entity.standard_value,
            "standard_units": entity.standard_units,
            "standard_relation": entity.standard_relation,
            "standard_upper_value": entity.standard_upper_value,
            "standard_text_value": entity.standard_text_value,
            "standard_flag": entity.standard_flag,
            # Derived metrics
            "pchembl_value": entity.pchembl_value,
            "ligand_efficiency": entity.ligand_efficiency,
            # Units ontology
            "qudt_units": entity.qudt_units,
            "uo_units": entity.uo_units,
            # Document data
            "document_journal": entity.document_journal,
            "document_year": entity.document_year,
            # Quality annotations
            "activity_comment": entity.activity_comment,
            "data_validity_comment": entity.data_validity_comment,
            "data_validity_description": entity.data_validity_description,
            "potential_duplicate": entity.potential_duplicate,
            # Action and properties
            "action_type": entity.action_type,
            "activity_properties": entity.activity_properties,
            "toid": entity.toid,
            # Lineage metadata
            "_run_id": str(entity.run_id),
            "_run_type": str(entity.run_type.value),
            "_source_batch_id": str(entity.source_batch_id),
            "_ingestion_ts": entity.ingestion_ts.isoformat(),
        }

        return cast(SilverRecord, silver_record)
