"""PubChem Molecule Transformer.

Transforms raw PubChem compound records into Silver-layer format using
the PubchemMolecule domain entity for validation and invariant checking.

.. versionchanged:: 2.0.0
    Uses PubchemMolecule (canonical) instead of Compound (deprecated).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities import PubchemMolecule
from bioetl.domain.services import IdentityService
from bioetl.domain.transformations import safe_float, safe_int
from bioetl.domain.validation import validate_molecular_weight, validate_non_negative
from bioetl.domain.value_objects import InChIKey

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import (
        DataNormalizationPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.types import BronzeRecord, SilverRecord


class PubChemCompoundTransformer(BaseTransformer):
    """Transformer for PubChem compound records.

    Uses PubchemMolecule domain entity (canonical name) for validation
    and lineage tracking. Records without structural identifiers
    (SMILES/InChI) are skipped per entity invariant validation.
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
        data_normalizer: DataNormalizationPort | None = None,
    ):
        """Initialize PubChem compound transformer.

        Args:
            provider: Data provider identifier. Defaults to 'pubchem'.
            entity_type: Entity type for metrics labels. Defaults to 'compound'.
            tracer: Optional tracing port for distributed tracing (O1 observability).
            metrics: Optional metrics port for duration/error tracking (O1 observability).
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
            pii_hasher: Optional PII hasher. Not typically used for molecules
                (no PII in chemical data), but included for API consistency.
            data_normalizer: Data normalization service for text normalization.

        """
        super().__init__(
            provider,
            entity_type=entity_type,
            tracer=tracer,
            metrics=metrics,
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            data_normalizer=data_normalizer,
        )

    def _extract_computed_descriptors(
        self, record: BronzeRecord
    ) -> dict[str, float | int | None]:
        """Extract and validate computed molecular descriptors."""
        return {
            "xlogp": safe_float(record.get("xlogp")),  # Can be negative
            "tpsa": validate_non_negative(record.get("tpsa")),
            "complexity": validate_non_negative(record.get("complexity")),
            "charge": safe_int(record.get("charge")),  # Can be negative
        }

    def _extract_atom_bond_counts(self, record: BronzeRecord) -> dict[str, int | None]:
        """Extract and validate atom/bond count properties."""
        return {
            "heavy_atom_count": safe_int(record.get("heavy_atom_count")),
            "h_bond_donor_count": safe_int(record.get("h_bond_donor_count")),
            "h_bond_acceptor_count": safe_int(record.get("h_bond_acceptor_count")),
            "rotatable_bond_count": safe_int(record.get("rotatable_bond_count")),
        }

    def _extract_stereochemistry(self, record: BronzeRecord) -> dict[str, int | None]:
        """Extract and validate stereochemistry counts."""
        return {
            "atom_stereo_count": safe_int(record.get("atom_stereo_count")),
            "defined_atom_stereo_count": safe_int(
                record.get("defined_atom_stereo_count")
            ),
            "undefined_atom_stereo_count": safe_int(
                record.get("undefined_atom_stereo_count")
            ),
            "bond_stereo_count": safe_int(record.get("bond_stereo_count")),
            "defined_bond_stereo_count": safe_int(
                record.get("defined_bond_stereo_count")
            ),
            "undefined_bond_stereo_count": safe_int(
                record.get("undefined_bond_stereo_count")
            ),
            "isotope_atom_count": safe_int(record.get("isotope_atom_count")),
            "covalent_unit_count": safe_int(record.get("covalent_unit_count")),
        }

    def _extract_3d_properties(
        self, record: BronzeRecord
    ) -> dict[str, float | int | None]:
        """Extract and validate 3D molecular properties."""
        return {
            "volume_3d": validate_non_negative(record.get("volume_3d")),
            "conformer_count_3d": safe_int(record.get("conformer_count_3d")),
            "feature_acceptor_count_3d": safe_int(
                record.get("feature_acceptor_count_3d")
            ),
            "feature_donor_count_3d": safe_int(record.get("feature_donor_count_3d")),
            "feature_anion_count_3d": safe_int(record.get("feature_anion_count_3d")),
            "feature_cation_count_3d": safe_int(record.get("feature_cation_count_3d")),
            "feature_ring_count_3d": safe_int(record.get("feature_ring_count_3d")),
            "feature_hydrophobe_count_3d": safe_int(
                record.get("feature_hydrophobe_count_3d")
            ),
            "effective_rotor_count_3d": validate_non_negative(
                record.get("effective_rotor_count_3d")
            ),
            "conformer_rmsd_3d": validate_non_negative(record.get("conformer_rmsd_3d")),
        }

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

        """
        cid = self._get_required_field(record, "cid")

        # Build business data with all physicochemical properties
        business_data: dict[str, Any] = {
            "cid": str(cid),
            "canonical_smiles": record.get("canonical_smiles"),
            "isomeric_smiles": record.get("isomeric_smiles"),
            "inchi": record.get("inchi"),
            "inchikey": self.validate_value_object(InChIKey, record.get("inchikey")),
            "molecular_formula": record.get("molecular_formula"),
            "iupac_name": record.get("iupac_name"),
            "molecular_weight": validate_molecular_weight(
                record.get("molecular_weight")
            ),
            "exact_mass": validate_non_negative(record.get("exact_mass")),
            **self._extract_computed_descriptors(record),
            **self._extract_atom_bond_counts(record),
            **self._extract_stereochemistry(record),
            **self._extract_3d_properties(record),
        }

        entity_id = self.compute_entity_id(source_id=str(cid), record={"cid": cid})
        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        entity = self._create_entity(
            PubchemMolecule,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )

        return cast("SilverRecord", self.entity_to_silver_record(entity))
