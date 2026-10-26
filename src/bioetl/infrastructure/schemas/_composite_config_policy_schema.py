# mypy: disable-error-code="misc,untyped-decorator"
"""Typed normalized anchor and join-key policies for composite YAML.

These blocks are part of the composite file contract. Quality checks read them
from the validated schema. They are not fields of domain ``CompositeConfig``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "NormalizedAnchorPolicySchema",
    "NormalizedJoinKeyPolicySchema",
    "PubchemCompoundAnchorSchema",
    "PubchemCompoundJoinBoundarySchema",
    "PublicationIdentityJoinPolicySchema",
    "UniprotIdMappingAnchorSchema",
    "UniprotIdMappingJoinBoundarySchema",
]


class PubchemCompoundJoinBoundarySchema(BaseModel):
    """PubChem anchors retained for validation but not used as join keys."""

    model_config = ConfigDict(extra="forbid")

    active_join_keys: list[str] = Field(
        ..., min_length=1, description="Anchors that may participate in joins"
    )
    retained_validation_anchors: list[str] = Field(
        ...,
        min_length=1,
        description="Anchors kept for validation without becoming join keys",
    )
    activation_condition: str = Field(
        ..., min_length=1, description="When the PubChem join boundary becomes active"
    )
    rationale: str = Field(..., min_length=1, description="Why this boundary exists")


class PubchemCompoundAnchorSchema(BaseModel):
    """PubChem compound entry inside normalized_anchor_policy."""

    model_config = ConfigDict(extra="forbid")

    join_boundary: PubchemCompoundJoinBoundarySchema


class UniprotIdMappingJoinBoundarySchema(BaseModel):
    """UniProt idmapping chain from a source anchor to a downstream pipeline."""

    model_config = ConfigDict(extra="forbid")

    source_anchor: str = Field(..., min_length=1, description="Upstream join anchor")
    normalized_output_anchor: str = Field(
        ..., min_length=1, description="Normalized anchor emitted for the next stage"
    )
    required_status: str = Field(
        ...,
        min_length=1,
        description="Mapping status required before the chain continues",
    )
    downstream_pipeline: str = Field(
        ..., min_length=1, description="Pipeline that consumes the normalized anchor"
    )
    rationale: str = Field(..., min_length=1, description="Why this boundary exists")


class UniprotIdMappingAnchorSchema(BaseModel):
    """UniProt idmapping entry inside normalized_anchor_policy."""

    model_config = ConfigDict(extra="forbid")

    join_boundary: UniprotIdMappingJoinBoundarySchema


class NormalizedAnchorPolicySchema(BaseModel):
    """Declared normalized-anchor policy for one composite file."""

    model_config = ConfigDict(extra="forbid")

    pubchem_compound: PubchemCompoundAnchorSchema
    uniprot_idmapping: UniprotIdMappingAnchorSchema


class PublicationIdentityJoinPolicySchema(BaseModel):
    """Publication identifier join order. Empty lists mean the policy does not apply."""

    model_config = ConfigDict(extra="forbid")

    primary_join_keys: list[str] = Field(
        default_factory=list, description="Canonical identifier join keys"
    )
    fallback_join_keys: list[str] = Field(
        default_factory=list,
        description="Fallback join keys used only after identifiers",
    )
    rationale: str = Field(..., min_length=1, description="Why this join order exists")


class NormalizedJoinKeyPolicySchema(BaseModel):
    """Declared normalized join-key policy for one composite file."""

    model_config = ConfigDict(extra="forbid")

    publication_identity: PublicationIdentityJoinPolicySchema
