# mypy: disable-error-code="misc"
"""Structure and sequence UniProt response models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.adapters.uniprot._uniprot_model_annotations import (
    UniProtEvidence,
)

__all__ = [
    "UniProtCrossReference",
    "UniProtExtraAttributes",
    "UniProtFeature",
    "UniProtFeatureLocation",
    "UniProtSequence",
]


class UniProtFeatureLocation(BaseModel):
    """Location of a feature."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    start: JsonDict | None = Field(  # Any: untyped API JSON record
        default=None, description="Start position"
    )  # Any: nested API JSON has heterogeneous values
    end: JsonDict | None = Field(  # Any: untyped API JSON record
        default=None, description="End position"
    )  # Any: nested API JSON has heterogeneous values


class UniProtFeature(BaseModel):
    """Protein feature (domain, site, etc.)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    type: str = Field(description="Feature type")
    location: UniProtFeatureLocation | None = Field(
        default=None, description="Feature location"
    )
    description: str | None = Field(default=None, description="Feature description")
    evidences: list[UniProtEvidence] | None = Field(
        default_factory=list, description="Supporting evidence"
    )
    feature_id: str | None = Field(
        default=None, alias="featureId", description="Feature ID"
    )


class UniProtCrossReference(BaseModel):
    """Cross-reference to external database."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    database: str = Field(description="Database name")
    id: str = Field(description="External ID")
    properties: list[dict[str, str]] | None = Field(
        default_factory=list, description="Additional properties"
    )


class UniProtSequence(BaseModel):
    """Protein sequence information."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    value: str = Field(description="Amino acid sequence")
    length: int = Field(description="Sequence length")
    mol_weight: int = Field(alias="molWeight", description="Molecular weight in Da")
    crc64: str | None = Field(default=None, description="CRC64 checksum")
    md5: str | None = Field(default=None, description="MD5 checksum")


class UniProtExtraAttributes(BaseModel):
    """Extra attributes for the entry."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    uni_parc_id: str | None = Field(
        default=None, alias="uniParcId", description="UniParc ID"
    )
