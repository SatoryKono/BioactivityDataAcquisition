"""PubChem Molecule Transformer.

Transforms raw PubChem compound records into Silver-layer format using
the PubchemMolecule domain entity for validation and invariant checking.

.. versionchanged:: 2.0.0
    Uses PubchemMolecule (canonical) instead of Compound (deprecated).
"""

from __future__ import annotations

__all__ = ["PubChemCompoundTransformer"]


from typing import TYPE_CHECKING, cast

from bioetl.application.core.base_transformer import (
    BaseTransformer,
    TransformerDependencyContext,
)
from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.domain.entities import PubchemMolecule
from bioetl.domain.transformations import safe_float, safe_int
from bioetl.domain.types import JsonDict
from bioetl.domain.validation import validate_molecular_weight, validate_non_negative
from bioetl.domain.value_objects import InChIKey

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.ports import MetricsPort, PiiHasherPort, TracingPort
    from bioetl.domain.services import IdentityService
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
        silver_filters: SilverFilterConfig | None = None,
        gold_filters: GoldFilterConfig | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        dependencies: TransformerDependencyContext | None = None,
    ) -> None:
        """Initialize PubChem compound transformer.

        Args:
            provider: Data provider identifier. Defaults to 'pubchem'.
            entity_type: Entity type for metrics labels. Defaults to 'compound'.
            silver_filters: Optional filter configuration for Silver layer.
            gold_filters: Optional filter configuration for Gold layer.
            dependencies: Explicit collaborator bundle.

        """
        super().__init__(
            provider,
            entity_type=entity_type,
            silver_filters=silver_filters,
            gold_filters=gold_filters,
            tracer=tracer,
            metrics=metrics,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            dependencies=dependencies,
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
            # Steric quadrupole moments can be negative (charge distribution)
            "x_steric_quadrupole_3d": safe_float(record.get("x_steric_quadrupole_3d")),
            "y_steric_quadrupole_3d": safe_float(record.get("y_steric_quadrupole_3d")),
            "z_steric_quadrupole_3d": safe_float(record.get("z_steric_quadrupole_3d")),
            "feature_count_3d": safe_int(record.get("feature_count_3d")),
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
        prepared = self._build_compound_business_data(context, record, index)
        if prepared is None:
            return None
        cid, business_data = prepared
        normalizer = RecordNormalizationProcessor(
            provider=self.provider,
            entity_type=self.entity_type,
        )
        normalized_business_data = normalizer.normalize_business_data(business_data)
        entity_id = self.compute_entity_id(
            source_id=str(cid), record={"molecule_id": cid}
        )
        content_hash = self.compute_content_hash(
            normalized_business_data,
            exclude_none=True,
        )

        silver_record = self._build_pre_silver_record(
            context,
            entity_id,
            content_hash,
            index,
            normalized_business_data,
        )
        return normalizer.project_normalization_findings(
            silver_record,
            context=context,
            index=index,
        )

    async def transform_pre_silver(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> PreSilverRecord | None:
        """Build an intermediate PubChem payload for application finalization."""
        prepared = self._build_compound_business_data(context, record, index)
        if prepared is None:
            return None
        cid, business_data = prepared
        entity_id = self.compute_entity_id(
            source_id=str(cid), record={"molecule_id": cid}
        )
        return PreSilverRecord(
            entity_id=entity_id,
            business_data=business_data,
            build_silver_record=self._build_pre_silver_json_record,
            apply_structural_policy=self._apply_pre_silver_structural_policy,
            apply_silver_filter=self._apply_pre_silver_filter,
        )

    def _build_compound_business_data(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> tuple[object, dict[str, object]] | None:
        """Build PubChem business data prior to hash finalization."""
        cid = record.get("cid")
        if cid is None:
            cid = record.get("molecule_id")
        if cid is None:
            context.logger.warning(
                "Skipping PubChem compound: missing compound identifier",
                index=index,
            )
            return None

        business_data: dict[str, object] = {
            "molecule_id": str(cid),
            "canonical_smiles": record.get("canonical_smiles"),
            "isomeric_smiles": record.get("isomeric_smiles"),
            "inchi": record.get("inchi"),
            "inchi_key": self.validate_value_object(
                InChIKey, record.get("inchikey") or record.get("inchi_key")
            ),
            "molecular_formula": record.get("molecular_formula"),
            "iupac_name": record.get("iupac_name"),
            "molecular_weight": validate_molecular_weight(
                record.get("molecular_weight")
            ),
            "exact_mass": validate_non_negative(record.get("exact_mass")),
            "monoisotopic_mass": validate_non_negative(record.get("monoisotopic_mass")),
            **self._extract_computed_descriptors(record),
            **self._extract_atom_bond_counts(record),
            **self._extract_stereochemistry(record),
            **self._extract_3d_properties(record),
        }
        return cid, business_data

    def _build_pre_silver_record(
        self,
        context: PipelineContext,
        entity_id: str,
        content_hash: str,
        index: int,
        business_data: JsonDict,
    ) -> SilverRecord:
        """Build a finalized Silver record from normalized compound business data."""
        entity = self._create_entity(
            PubchemMolecule,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )

        return cast("SilverRecord", self.entity_to_silver_record(entity))

    def _build_pre_silver_json_record(
        self,
        context: PipelineContext,
        entity_id: str,
        content_hash: str,
        index: int,
        business_data: JsonDict,
    ) -> JsonDict:
        """Adapt finalized Silver-record construction to the PreSilverRecord protocol."""
        return cast(
            JsonDict,
            self._build_pre_silver_record(
                context,
                entity_id,
                content_hash,
                index,
                business_data,
            ),
        )

    def _apply_pre_silver_structural_policy(
        self,
        context: PipelineContext,
        record: JsonDict,
        index: int,
    ) -> JsonDict | None:
        """Adapt structural policy application to the PreSilverRecord protocol."""
        return cast(
            JsonDict | None,
            self._apply_structural_policy(
                context,
                cast("SilverRecord", record),
                index,
            ),
        )

    def _apply_pre_silver_filter(
        self,
        context: PipelineContext,
        record: JsonDict,
        index: int,
    ) -> None:
        """Adapt silver-filter application to the PreSilverRecord protocol."""
        self._apply_silver_filter(
            context,
            cast("SilverRecord", record),
            index,
        )
