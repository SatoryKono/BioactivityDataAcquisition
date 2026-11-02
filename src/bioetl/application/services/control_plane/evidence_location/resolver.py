"""Bounded evidence-location resolver (RF-003).

Resolves one ownership key to a trusted data root and opens a read-only
context via an injected factory. Does not write location records, mutate
evidence, or invent READY / objects verdicts from the locator alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from bioetl.application.services.control_plane.evidence_location.resolver_types import (
    EvidenceLocationLegacyRootPolicy,
    EvidenceLocationResolveResult,
    EvidenceReadContext,
    EvidenceReadContextFactoryProtocol,
)
from bioetl.application.services.run_reports.evidence_location_paths import (
    EvidenceRootAliasRegistry,
)
from bioetl.domain.control_plane.run_evidence_location import (
    DEFAULT_EVIDENCE_ROOT_ALIAS,
    EvidenceLocationInvalidError,
    EvidenceLocationKind,
    EvidenceLocationLookupCode,
    EvidenceLocationLookupResult,
    RunEvidenceLocation,
)
from bioetl.domain.ports import RunEvidenceLocationReadPort
from bioetl.domain.types import RunID

__all__ = [
    "EvidenceLocationLegacyRootPolicy",
    "EvidenceLocationResolveResult",
    "EvidenceLocationResolver",
    "EvidenceReadContext",
    "EvidenceReadContextFactoryProtocol",
]


def _is_workflow_kind(kind: EvidenceLocationKind | str | None) -> bool:
    """True for enum or string workflow kind (callers may pass either form)."""
    if kind is None:
        return False
    if isinstance(kind, EvidenceLocationKind):
        return kind is EvidenceLocationKind.WORKFLOW
    return str(kind).strip().lower() == EvidenceLocationKind.WORKFLOW.value


@dataclass(frozen=True, slots=True)
class EvidenceLocationResolver:
    """Application resolver over ``RunEvidenceLocationReadPort`` + alias map."""

    locations: RunEvidenceLocationReadPort
    aliases: EvidenceRootAliasRegistry
    opener: EvidenceReadContextFactoryProtocol
    legacy_root_policy: EvidenceLocationLegacyRootPolicy = (
        EvidenceLocationLegacyRootPolicy.ALLOW_STANDARD_ALIAS_BASE
    )

    def resolve(
        self,
        *,
        kind: EvidenceLocationKind | str,
        owner: str,
        run_id: str,
        expected_runtime_source_id: str | None = None,
    ) -> EvidenceLocationResolveResult:
        """Resolve one ownership key to a bounded read context.

        Read path never registers, repairs, or rewrites location/evidence bytes.
        Foreign source identity and invalid locators fail closed with no fallback
        to another run's data root.
        """
        lookup = self.locations.lookup(
            kind=kind,
            owner=owner,
            run_id=run_id,
            expected_runtime_source_id=expected_runtime_source_id,
        )
        if lookup.code is EvidenceLocationLookupCode.FOUND:
            assert lookup.location is not None
            result = self._open_from_location(lookup, requested_kind=kind)
        elif lookup.code is EvidenceLocationLookupCode.LOCATION_MISSING:
            result = self._open_legacy_or_missing(lookup, requested_kind=kind)
        else:
            # identity_conflict / location_invalid — fail closed
            result = EvidenceLocationResolveResult(
                lookup=lookup,
                requested_kind=kind,
                detail=lookup.detail,
            )
        # Rebuild instead of ``dataclasses.replace`` so the return type stays
        # ``EvidenceLocationResolveResult`` (Sonar rejects DataclassInstance).
        return EvidenceLocationResolveResult(
            lookup=result.lookup,
            requested_run_id=str(run_id),
            requested_kind=result.requested_kind,
            data_root=result.data_root,
            context=result.context,
            used_legacy_standard_root=result.used_legacy_standard_root,
            detail=result.detail,
        )

    def load_manifest(
        self,
        result: EvidenceLocationResolveResult,
        *,
        run_id: object,
    ) -> EvidenceLocationLookupResult:
        """Post-resolve manifest layer; keeps ``manifest_missing`` distinct."""
        if result.requested_run_id is None or str(run_id) != result.requested_run_id:
            return EvidenceLocationLookupResult(
                code=EvidenceLocationLookupCode.IDENTITY_CONFLICT,
                location=result.location,
                detail="manifest_run_id_mismatch",
            )
        if result.context is None:
            return EvidenceLocationLookupResult(
                code=(
                    result.code
                    if result.code is not EvidenceLocationLookupCode.FOUND
                    else EvidenceLocationLookupCode.LOCATION_MISSING
                ),
                location=result.location,
                detail=result.detail or "context_not_open",
            )
        try:
            typed_run_id = RunID(UUID(str(run_id)))
            if _is_workflow_kind(result.requested_kind):
                manifest = result.context.get_workflow_manifest_by_run_id(typed_run_id)
            else:
                manifest = result.context.get_manifest_by_run_id(typed_run_id)
        except (EvidenceLocationInvalidError, OSError, TypeError, ValueError) as exc:
            return EvidenceLocationLookupResult(
                code=EvidenceLocationLookupCode.LOCATION_INVALID,
                location=result.location,
                detail=str(exc),
            )
        if manifest is None:
            return EvidenceLocationLookupResult(
                code=EvidenceLocationLookupCode.MANIFEST_MISSING,
                location=result.location,
                detail="manifest_not_in_resolved_root",
            )
        return EvidenceLocationLookupResult(
            code=EvidenceLocationLookupCode.FOUND,
            location=result.location,
            detail="manifest_present",
        )

    def _open_context(
        self,
        *,
        root_alias: str,
        relative_data_root: str,
    ) -> EvidenceReadContext:
        """Resolve alias roots and open a trusted read context."""
        trusted_base = self.aliases.absolute_base(root_alias)
        data_root = self.aliases.resolve_data_root(
            root_alias=root_alias,
            relative_data_root=relative_data_root,
        )
        return self.opener.open(
            data_root,
            trusted_alias_base=trusted_base,
        )

    def _open_from_location(
        self,
        lookup: EvidenceLocationLookupResult,
        *,
        requested_kind: EvidenceLocationKind | str,
    ) -> EvidenceLocationResolveResult:
        location = lookup.location
        assert location is not None
        try:
            context = self._open_context(
                root_alias=location.root_alias,
                relative_data_root=location.relative_data_root,
            )
        except (EvidenceLocationInvalidError, OSError, ValueError) as exc:
            return EvidenceLocationResolveResult(
                lookup=EvidenceLocationLookupResult(
                    code=EvidenceLocationLookupCode.LOCATION_INVALID,
                    location=location,
                    detail=str(exc),
                ),
                requested_kind=requested_kind,
                detail=str(exc),
            )
        return EvidenceLocationResolveResult(
            lookup=lookup,
            requested_kind=requested_kind,
            data_root=context.data_root,
            context=context,
            used_legacy_standard_root=location.relative_data_root == ".",
        )

    def _open_legacy_or_missing(
        self,
        lookup: EvidenceLocationLookupResult,
        *,
        requested_kind: EvidenceLocationKind | str,
    ) -> EvidenceLocationResolveResult:
        if (
            self.legacy_root_policy
            is not EvidenceLocationLegacyRootPolicy.ALLOW_STANDARD_ALIAS_BASE
        ):
            return EvidenceLocationResolveResult(
                lookup=lookup,
                requested_kind=requested_kind,
            )
        try:
            context = self._open_context(
                root_alias=DEFAULT_EVIDENCE_ROOT_ALIAS,
                relative_data_root=".",
            )
        except (EvidenceLocationInvalidError, OSError, ValueError) as exc:
            return EvidenceLocationResolveResult(
                lookup=lookup,
                requested_kind=requested_kind,
                detail=str(exc),
            )
        return EvidenceLocationResolveResult(
            lookup=lookup,
            requested_kind=requested_kind,
            data_root=context.data_root,
            context=context,
            used_legacy_standard_root=True,
            detail="legacy_standard_alias_base",
        )
