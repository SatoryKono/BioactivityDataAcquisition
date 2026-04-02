"""Typed model for pipeline contract policies.

Policy data lives in configs/entities/{provider}/{entity}.yaml
(section "contracts"). It captures keys/hash/rename directives plus
contract-rollout metadata used by versioned-read/write runtime flows.
"""

from __future__ import annotations

__all__ = ["PipelineContractPolicy", "PipelineContractRollout"]

from pydantic import BaseModel, ConfigDict, Field, model_validator

from bioetl.domain.types.contract_rollout import ContractRolloutPolicy


class PipelineContractRollout(BaseModel):
    """Typed rollout metadata nested under ``contracts.rollout``."""

    model_config = ConfigDict(extra="forbid")

    mode: str = Field(default="single")
    read_order: list[str] = Field(default_factory=list)
    write_versions: list[str] = Field(default_factory=list)
    affects_hash: bool = False


class PipelineContractPolicy(BaseModel):
    """Contract policy for provider/entity pipeline behavior."""

    model_config = ConfigDict(extra="forbid")

    primary_key: list[str] = Field(min_length=1)
    merge_keys: list[str] = Field(min_length=1)
    hash_include: list[str] = Field(default_factory=list)
    hash_exclude: list[str] = Field(default_factory=list)
    rename_map: dict[str, str] = Field(default_factory=dict)
    contract_ref: str = Field(default="")
    active_version: str = Field(default="")
    rollout: PipelineContractRollout = Field(
        default_factory=PipelineContractRollout
    )

    @property
    def rollout_mode(self) -> str:
        """Compatibility accessor for rollout mode."""
        return self.rollout.mode

    @property
    def read_order(self) -> list[str]:
        """Compatibility accessor for ordered read versions."""
        return list(self.rollout.read_order)

    @property
    def write_versions(self) -> list[str]:
        """Compatibility accessor for ordered write versions."""
        return list(self.rollout.write_versions)

    @property
    def affects_hash(self) -> bool:
        """Compatibility accessor for hash-affecting rollout flag."""
        return self.rollout.affects_hash

    def to_contract_rollout_policy(self) -> ContractRolloutPolicy:
        """Convert to a pure runtime rollout value object."""
        return ContractRolloutPolicy(
            contract_ref=self.contract_ref,
            active_version=self.active_version,
            mode=self.rollout.mode,
            read_order=tuple(self.rollout.read_order),
            write_versions=tuple(self.rollout.write_versions),
            affects_hash=self.rollout.affects_hash,
        )

    @model_validator(mode="after")
    def validate_merge_keys_subset(self) -> PipelineContractPolicy:
        """Ensure merge_keys is not disjoint from primary key definition."""
        pk_set = set(self.primary_key)
        mk_set = set(self.merge_keys)
        if pk_set.isdisjoint(mk_set):
            raise ValueError("merge_keys must overlap with primary_key")
        return self

    @model_validator(mode="after")
    def validate_rollout_policy(self) -> PipelineContractPolicy:
        """Validate rollout metadata for versioned contract handling."""
        self._validate_mode_and_refs()
        self._validate_active_version_presence()
        self._validate_no_duplicates()
        self._validate_single_mode_consistency()
        return self

    def _validate_mode_and_refs(self) -> None:
        """Validate rollout mode and basic reference non-emptiness."""
        allowed_modes = {"single", "dual_read", "dual_write", "dual_read_write"}
        if self.rollout.mode not in allowed_modes:
            allowed = ", ".join(sorted(allowed_modes))
            raise ValueError(
                f"rollout.mode must be one of {allowed}, got {self.rollout.mode!r}"
            )
        if not self.contract_ref.strip():
            raise ValueError("contract_ref must be a non-empty string")
        if not self.active_version.strip():
            raise ValueError("active_version must be a non-empty string")

    def _validate_active_version_presence(self) -> None:
        """Ensure active_version is present in both read and write sets."""
        if self.active_version not in self.rollout.read_order:
            raise ValueError("active_version must be present in rollout.read_order")
        if self.active_version not in self.rollout.write_versions:
            raise ValueError(
                "active_version must be present in rollout.write_versions"
            )

    def _validate_no_duplicates(self) -> None:
        """Ensure read/write orders contain no duplicate versions."""
        if len(self.rollout.read_order) != len(set(self.rollout.read_order)):
            raise ValueError("rollout.read_order must not contain duplicate versions")
        if len(self.rollout.write_versions) != len(set(self.rollout.write_versions)):
            raise ValueError(
                "rollout.write_versions must not contain duplicate versions"
            )

    def _validate_single_mode_consistency(self) -> None:
        """Validate strict equality for single rollout mode."""
        if self.rollout.mode == "single":
            if self.rollout.read_order != [self.active_version]:
                raise ValueError(
                    "single rollout.mode requires read_order == [active_version]"
                )
            if self.rollout.write_versions != [self.active_version]:
                raise ValueError(
                    "single rollout.mode requires write_versions == [active_version]"
                )
