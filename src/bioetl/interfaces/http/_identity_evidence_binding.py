"""Bind identity anchors to the same trusted exact-run root as validation."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import cast

from bioetl.application.services.evidence_location.resolver import (
    EvidenceLocationResolver,
    EvidenceReadContext,
)
from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.interfaces.http._health_server_control_plane_evidence_scope import (
    EvidenceScopeHost,
    _selected_validation_pipeline,
    _validate_bound_manifest,
)
from bioetl.interfaces.http._health_server_control_plane_scope import _IdentityScope
from bioetl.interfaces.http.control_plane_identity.types import LedgerEntryProvider


@dataclass(frozen=True, slots=True)
class _SelectedIdentityLedger:
    context: EvidenceReadContext
    run_id: str
    manifest_id: str

    def list_entries(self, manifest_id: str) -> list[RunLedgerEntry]:
        """Read only the selected run, including its contained successor chain."""
        if manifest_id != self.manifest_id:
            raise ValueError("Identity ledger manifest does not match selected run")
        return list(self.context.get_ledger_entries_by_run_id(self.run_id))


def bind_identity_evidence(
    host: EvidenceScopeHost, scope: _IdentityScope
) -> tuple[_IdentityScope, LedgerEntryProvider | None]:
    """Keep legacy hosts supported; configured locators never fall back globally."""
    resolver = getattr(host, "_evidence_location_resolver", None)
    if (
        not isinstance(resolver, EvidenceLocationResolver)
        or scope.selected_run_id is None
    ):
        return scope, cast(
            LedgerEntryProvider | None, getattr(host, "_run_ledger_port", None)
        )
    pipeline = _selected_validation_pipeline(host, scope)
    resolved = resolver.resolve(
        kind="pipeline",
        owner=pipeline,
        run_id=scope.selected_run_id,
        expected_runtime_source_id=getattr(host, "_runtime_source_id", None),
    )
    if resolved.context is None or resolved.code.value in {
        "identity_conflict",
        "location_invalid",
    }:
        raise ValueError("Selected identity evidence location is unavailable")
    manifest = resolved.context.get_manifest_by_run_id(scope.selected_run_id)
    if manifest is None and scope.resolved_manifest is None:
        return scope, None
    manifest = _validate_bound_manifest(manifest, scope=scope, pipeline=pipeline)
    return replace(scope, resolved_manifest=manifest), _SelectedIdentityLedger(
        context=resolved.context,
        run_id=scope.selected_run_id,
        manifest_id=manifest.manifest_id,
    )
