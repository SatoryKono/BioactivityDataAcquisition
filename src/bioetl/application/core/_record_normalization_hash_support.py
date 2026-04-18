"""Private content-hash helpers for RecordNormalizationProcessor."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.config import ContentHashVersionPolicy
from bioetl.domain.transformations import generate_content_hash

if TYPE_CHECKING:
    from bioetl.application.core.config import ContentHashPolicyByVersion
    from bioetl.domain.types import JsonDict


class RecordNormalizationHashSupportMixin:
    """Own rollout-aware content-hash policy resolution for normalized records."""

    content_hash_policy_by_version: ContentHashPolicyByVersion | None
    content_hash_include_fields: frozenset[str]
    content_hash_exclude_fields: frozenset[str]
    profile: object
    provider: str

    def _should_project_hashes_by_version(self) -> bool:
        policy = self.content_hash_policy_by_version
        return policy is not None and policy.requires_projected_hashes

    def compute_content_hash(
        self,
        record: JsonDict,
        *,
        contract_version: str | None = None,
    ) -> str:
        include_fields, exclude_fields = self._resolve_hash_policy(
            contract_version=contract_version
        )
        return str(
            generate_content_hash(
                record,
                self.provider,
                exclude_none=True,
                include_fields=include_fields,
                exclude_fields=exclude_fields,
                set_like_fields=(
                    None if self.profile is None else set(self.profile.set_like_fields)
                ),
            )
        )

    def compute_content_hashes_by_version(self, record: JsonDict) -> dict[str, str]:
        if not self._should_project_hashes_by_version():
            return {}
        assert self.content_hash_policy_by_version is not None
        return {
            policy.version: self.compute_content_hash(
                record,
                contract_version=policy.version,
            )
            for policy in self.content_hash_policy_by_version.policies
        }

    def _profile_hash_fields(self) -> tuple[frozenset[str], frozenset[str]]:
        if self.profile is None:
            return frozenset(), frozenset()
        return self.profile.hash_included_fields, self.profile.hash_excluded_fields

    def _select_hash_policy(
        self,
        *,
        contract_version: str | None,
    ) -> ContentHashVersionPolicy | None:
        if self.content_hash_policy_by_version is None:
            return None
        target_version = (
            contract_version or self.content_hash_policy_by_version.active_version
        )
        return (
            self.content_hash_policy_by_version.for_version(target_version)
            or self.content_hash_policy_by_version.active_policy
        )

    def _resolve_hash_include_fields(
        self,
        *,
        profile_include: frozenset[str],
        policy: ContentHashVersionPolicy | None,
    ) -> set[str] | None:
        if policy is not None and policy.include_fields:
            include_source = policy.include_fields
        else:
            include_source = profile_include or self.content_hash_include_fields
        return set(include_source) if include_source else None

    def _resolve_hash_exclude_fields(
        self,
        *,
        profile_exclude: frozenset[str],
        policy: ContentHashVersionPolicy | None,
    ) -> set[str]:
        return (
            set(self.content_hash_exclude_fields)
            | set(profile_exclude)
            | (set(policy.exclude_fields) if policy is not None else set())
            | {"entity_id", "content_hash", "_content_hashes_by_version"}
        )

    def _resolve_hash_policy(
        self,
        *,
        contract_version: str | None,
    ) -> tuple[set[str] | None, set[str]]:
        profile_include, profile_exclude = self._profile_hash_fields()
        policy = self._select_hash_policy(contract_version=contract_version)
        return (
            self._resolve_hash_include_fields(
                profile_include=profile_include,
                policy=policy,
            ),
            self._resolve_hash_exclude_fields(
                profile_exclude=profile_exclude,
                policy=policy,
            ),
        )
