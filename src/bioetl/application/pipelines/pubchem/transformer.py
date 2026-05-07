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
from bioetl.application.core.pre_silver_adapter_mixin import (
    PreSilverAdapterMixin,
)
from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.pipelines.pubchem._compound_business_data import (
    build_compound_business_data,
)
from bioetl.domain.entities import PubchemMolecule
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.behavior import EntityIdentityGenerator
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.ports import MetricsPort, PiiHasherPort, TracingPort
    from bioetl.domain.types import BronzeRecord, SilverRecord


class PubChemCompoundTransformer(PreSilverAdapterMixin, BaseTransformer):
    """Transformer for PubChem compound records.

    Uses PubchemMolecule domain entity (canonical name) for validation
    and lineage tracking. Records without structural identifiers
    (SMILES/InChI) are skipped per entity invariant validation.
    """

    entity_class = PubchemMolecule

    def __init__(
        self,
        provider: str = "pubchem",
        entity_type: str = "compound",
        silver_filters: SilverFilterConfig | None = None,
        gold_filters: GoldFilterConfig | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        identity_service: EntityIdentityGenerator | None = None,
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
        return cast(
            "SilverRecord",
            self._finalize_prepared_business_data(
                context=context,
                source_id=str(cid),
                identity_record={"molecule_id": cid},
                index=index,
                business_data=cast(JsonDict, business_data),
            ),
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
        return self._build_pre_silver_from_business_data(
            source_id=str(cid),
            identity_record={"molecule_id": cid},
            business_data=cast(JsonDict, business_data),
        )

    def _build_compound_business_data(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> tuple[object, dict[str, object]] | None:
        """Build PubChem business data prior to hash finalization."""
        prepared = build_compound_business_data(
            record,
            validate_inchi_key=self.validate_value_object,
            serialize_json_list=self.serialize_json_list,
        )
        if prepared is None:
            context.logger.warning(
                "Skipping PubChem compound: missing compound identifier",
                index=index,
            )
            return None
        return prepared
