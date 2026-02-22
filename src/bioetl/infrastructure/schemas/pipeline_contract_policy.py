"""Typed model for pipeline contract policies.

Policy files live under configs/contracts/pipelines/{provider}/{entity}.yaml and
capture keys/hash/rename directives externalized from transformer and factory code.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PipelineContractPolicy(BaseModel):
    """Contract policy for provider/entity pipeline behavior."""

    model_config = ConfigDict(extra="forbid")

    primary_key: list[str] = Field(min_length=1)
    merge_keys: list[str] = Field(min_length=1)
    hash_include: list[str] = Field(default_factory=list)
    hash_exclude: list[str] = Field(default_factory=list)
    rename_map: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_merge_keys_subset(self) -> PipelineContractPolicy:
        """Ensure merge_keys is not disjoint from primary key definition."""
        pk_set = set(self.primary_key)
        mk_set = set(self.merge_keys)
        if pk_set.isdisjoint(mk_set):
            raise ValueError("merge_keys must overlap with primary_key")
        return self
