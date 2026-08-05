# mypy: disable-error-code="misc"
"""Extra shared ChEMBL models (target component + cell line)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.adapters.chembl._models_common_page import ChemblPageMeta

__all__ = [
    "ChemblCellLineRecord",
    "ChemblCellLineResponse",
    "ChemblTargetComponentRecord",
    "ChemblTargetComponentResponse",
]

_PAGINATION_METADATA_DESCRIPTION = "Pagination metadata"


class ChemblTargetComponentRecord(BaseModel):
    """Individual target component record from ChEMBL API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    component_id: int = Field(description="Component ID")
    component_type: str | None = Field(default=None)
    accession: str | None = Field(default=None, description="UniProt accession")
    sequence: str | None = Field(default=None, description="Protein sequence")
    sequence_md5sum: str | None = Field(default=None)
    description: str | None = Field(default=None)
    organism: str | None = Field(default=None)
    tax_id: int | None = Field(default=None)
    go_slims: list[JsonDict] | None = (  # Any: untyped API JSON record
        Field(  # Any: nested API JSON has heterogeneous values
            default_factory=list
        )
    )  # Any: nested ChEMBL JSON with provider-specific schema
    protein_classifications: (
        list[JsonDict] | None  # Any: untyped API JSON record
    ) = (  # Any: untyped API JSON record
        Field(  # Any: nested API JSON has heterogeneous values
            default_factory=list
        )
    )  # Any: nested ChEMBL JSON with provider-specific schema
    target_component_synonyms: (
        list[JsonDict] | None  # Any: untyped API JSON record
    ) = (  # Any: untyped API JSON record
        Field(  # Any: nested API JSON has heterogeneous values
            default_factory=list
        )
    )  # Any: nested ChEMBL JSON with provider-specific schema
    target_component_xrefs: (
        list[JsonDict] | None  # Any: untyped API JSON record
    ) = (  # Any: untyped API JSON record
        Field(  # Any: nested API JSON has heterogeneous values
            default_factory=list
        )
    )  # Any: nested ChEMBL JSON with provider-specific schema


class ChemblTargetComponentResponse(BaseModel):
    """Complete ChEMBL Target Component API response."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    target_components: list[ChemblTargetComponentRecord] = Field(
        default_factory=list, description="List of target component records"
    )
    page_meta: ChemblPageMeta | None = Field(
        default=None, description=_PAGINATION_METADATA_DESCRIPTION
    )


class ChemblCellLineRecord(BaseModel):
    """Individual cell line record from ChEMBL API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    cell_chembl_id: str = Field(description="ChEMBL ID of the cell line")
    cell_name: str | None = Field(default=None)
    cell_description: str | None = Field(default=None)
    cell_source_organism: str | None = Field(default=None)
    cell_source_tax_id: int | None = Field(default=None)
    cell_source_tissue: str | None = Field(default=None)
    cell_type: str | None = Field(default=None)
    cellosaurus_id: str | None = Field(default=None)
    clo_id: str | None = Field(default=None)
    efo_id: str | None = Field(default=None)


class ChemblCellLineResponse(BaseModel):
    """Complete ChEMBL Cell Line API response."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    cell_lines: list[ChemblCellLineRecord] = Field(
        default_factory=list, description="List of cell line records"
    )
    page_meta: ChemblPageMeta | None = Field(
        default=None, description=_PAGINATION_METADATA_DESCRIPTION
    )
