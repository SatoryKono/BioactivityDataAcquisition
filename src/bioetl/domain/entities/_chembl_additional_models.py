# mypy: disable-error-code="misc"
"""Additional ChEMBL DTO models for adapter-facing typed fetches."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TissueRecord(BaseModel):
    """Tissue DTO aligned with the canonical ChEMBL tissue pipeline surface."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tissue_id: str = Field(min_length=1, description="Unique tissue ChEMBL ID")
    pref_name: str = Field(min_length=1, description="Preferred tissue name")
    bto_id: str | None = Field(default=None, description="BRENDA Tissue Ontology ID")
    caloha_id: str | None = Field(default=None, description="CALOHA tissue ID")
    efo_id: str | None = Field(
        default=None, description="Experimental Factor Ontology ID"
    )
    uberon_id: str | None = Field(default=None, description="UBERON anatomy ID")


class CompoundLinkRecord(BaseModel):
    """Compound-record DTO linking one molecule occurrence to one publication."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    record_id: int = Field(description="Unique compound-record surrogate key")
    molecule_id: str = Field(min_length=1, description="Linked molecule ChEMBL ID")
    publication_id: str = Field(min_length=1, description="Linked publication ChEMBL ID")
    compound_key: str | None = Field(
        default=None, description="Provider-native compound key"
    )
    compound_name: str | None = Field(
        default=None, description="Provider-native compound name"
    )
    src_id: int = Field(description="ChEMBL source identifier")
    src_compound_id: str | None = Field(
        default=None, description="Source compound identifier"
    )


class PublicationSimilarityRecord(BaseModel):
    """Publication-similarity DTO aligned with the Silver pipeline contract."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sim_id: int = Field(description="Deterministic similarity identifier")
    doc_1: int = Field(description="Primary document numeric identifier")
    doc_2: int = Field(description="Secondary document numeric identifier")
    pubmed_id1: str | None = Field(default=None, description="Primary PubMed ID")
    pubmed_id2: str | None = Field(default=None, description="Secondary PubMed ID")
    tid_tani: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Target-identifier similarity score",
    )
    mol_tani: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Molecule similarity score"
    )
    avg_tani: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Average similarity score"
    )
    max_tani: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Maximum similarity score"
    )


__all__ = [
    "CompoundLinkRecord",
    "PublicationSimilarityRecord",
    "TissueRecord",
]
