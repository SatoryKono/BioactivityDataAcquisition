# MRO/override residual on mixin or client hierarchies.
"""UniProt Target transformer.

Transforms raw UniProt protein records into Silver-layer format using
the UniprotTarget domain entity for validation and invariant checking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.base_transformer import (
    BaseTransformer,
    TransformationError,
)
from bioetl.application.core.base_transformer.errors import FilteredOutError
from bioetl.application.core.pre_silver_adapter_mixin import (
    PreSilverAdapterMixin,
)
from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.pipelines.common.publication_transformer_context import (
    install_runtime_transformer_init,
)
from bioetl.application.pipelines.uniprot.transformer_business_data_mixin import (
    UniProtBusinessDataMixin,
)
from bioetl.domain.entities import UniprotTarget

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord

__all__ = ["UniProtProteinTransformer"]


class UniProtProteinTransformer(  # pyright: ignore[reportIncompatibleMethodOverride]
    PreSilverAdapterMixin, BaseTransformer, UniProtBusinessDataMixin
):
    """Transformer for UniProt protein records."""

    entity_class = UniprotTarget

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Transform raw UniProt record to Silver format."""
        self._reject_inactive_record(record)
        try:
            accession = str(self._get_required_field(record, "primaryAccession"))
            entry_name = self._get_entry_name(record)
            business_data = self._build_business_data(record, accession, entry_name)
            return self._transform_identity_business_data(
                context=context,
                source_id=accession,
                identity_field="accession",
                index=index,
                business_data=business_data,
            )
        except (FilteredOutError, ValueError) as e:
            context.logger.warning(
                "Skipping UniProt record: validation failed",
                error=str(e),
                index=index,
            )
            return None

    async def transform_pre_silver(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> PreSilverRecord | None:
        """Build an intermediate UniProt payload for application finalization."""
        self._reject_inactive_record(record)
        try:
            accession = str(self._get_required_field(record, "primaryAccession"))
            entry_name = self._get_entry_name(record)
            business_data = self._build_business_data(record, accession, entry_name)
            return self._stage_identity_business_data(
                source_id=accession,
                identity_field="accession",
                business_data=business_data,
            )
        except (FilteredOutError, ValueError) as e:
            context.logger.warning(
                "Skipping UniProt record: validation failed",
                error=str(e),
                index=index,
            )
            return None

    def _reject_inactive_record(self, record: BronzeRecord) -> None:
        """Keep deletion tombstones in Bronze without treating them as proteins."""
        if record.get("entryType") == "Inactive":
            raise FilteredOutError(
                "UniProt entry is inactive",
                details={
                    "entry_type": "Inactive",
                    "accession": record.get("primaryAccession"),
                    "inactive_reason": record.get("inactiveReason"),
                },
            )

    def _get_entry_name(self, record: BronzeRecord) -> str:
        """Extract entry name (uniProtkbId) as required field."""
        entry_name = record.get("uniProtkbId")
        if not entry_name:
            raise TransformationError(
                "Missing required field: uniProtkbId", field="uniProtkbId"
            )
        return str(entry_name)


install_runtime_transformer_init(
    UniProtProteinTransformer,
    "uniprot",
    "protein",
)
