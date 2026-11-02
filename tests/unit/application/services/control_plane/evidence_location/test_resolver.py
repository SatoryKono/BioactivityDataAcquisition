# pyright: reportArgumentType=false
"""Bounded evidence-location resolver unit tests (ports/doubles only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from bioetl.application.services.control_plane.evidence_location import (
    EvidenceLocationLegacyRootPolicy,
    EvidenceLocationResolver,
    EvidenceReadContext,
)
from bioetl.application.services.run_reports.evidence_location_paths import (
    default_evidence_root_alias_registry,
)
from bioetl.domain.control_plane.run_evidence_location import (
    DEFAULT_EVIDENCE_ROOT_ALIAS,
    EvidenceLocationKind,
    EvidenceLocationLookupCode,
    EvidenceLocationLookupResult,
    RunEvidenceLocation,
    build_run_evidence_location,
)

pytestmark = pytest.mark.unit

_SOURCE_A = "a" * 64
_SOURCE_B = "b" * 64
_RUN_A = "ac0b4e22-6a6e-5b7e-818e-106aeaf41390"
_RUN_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
_WF = "3dc8ffe4-305b-5d4b-a945-fe8e78f03828"


def _location(**overrides: object) -> RunEvidenceLocation:
    payload: dict[str, object] = {
        "kind": EvidenceLocationKind.PIPELINE,
        "owner": "chembl_assay",
        "run_id": _RUN_A,
        "workflow_run_id": _WF,
        "runtime_source_id": _SOURCE_A,
        "root_alias": DEFAULT_EVIDENCE_ROOT_ALIAS,
        "relative_data_root": "workflow-a/chembl_assay",
    }
    payload.update(overrides)
    return build_run_evidence_location(**payload)  # type: ignore[arg-type]


@dataclass
class _FakeLocationStore:
    records: dict[tuple[str, str, str], RunEvidenceLocation] = field(
        default_factory=dict
    )

    def register(self, location: RunEvidenceLocation) -> None:
        key = (str(location.kind), location.owner, location.run_id)
        self.records[key] = location

    def lookup(
        self,
        *,
        kind: EvidenceLocationKind | str,
        owner: str,
        run_id: str,
        expected_runtime_source_id: str | None = None,
    ) -> EvidenceLocationLookupResult:
        key = (str(kind), owner, run_id)
        location = self.records.get(key)
        if location is None:
            return EvidenceLocationLookupResult(
                code=EvidenceLocationLookupCode.LOCATION_MISSING
            )
        if (
            expected_runtime_source_id is not None
            and location.runtime_source_id != expected_runtime_source_id
        ):
            return EvidenceLocationLookupResult(
                code=EvidenceLocationLookupCode.IDENTITY_CONFLICT,
                location=location,
                detail="runtime_source_id_mismatch",
            )
        return EvidenceLocationLookupResult(
            code=EvidenceLocationLookupCode.FOUND,
            location=location,
        )


@dataclass
class _FakeReadContext:
    data_root: Path
    pipeline_manifests: dict[UUID, object] = field(default_factory=dict)
    workflow_manifests: dict[UUID, object] = field(default_factory=dict)
    replay_results: dict[int, dict[str, bool]] = field(default_factory=dict)

    def get_manifest_by_run_id(self, run_id: UUID) -> object | None:
        return self.pipeline_manifests.get(run_id)

    def get_workflow_manifest_by_run_id(self, run_id: UUID) -> object | None:
        return self.workflow_manifests.get(run_id)

    def verify_replay_objects(self, manifest: object) -> dict[str, bool]:
        return self.replay_results.get(id(manifest), {})


@dataclass
class _FakeOpener:
    opens: list[tuple[Path, Path]] = field(default_factory=list)
    contexts: dict[Path, _FakeReadContext] = field(default_factory=dict)

    def open(
        self,
        data_root: Path,
        *,
        trusted_alias_base: Path,
    ) -> EvidenceReadContext:
        root = Path(data_root).resolve()
        self.opens.append((root, Path(trusted_alias_base).resolve()))
        return self.contexts.setdefault(root, _FakeReadContext(data_root=root))


def _resolver(
    tmp_path: Path,
    *,
    legacy: EvidenceLocationLegacyRootPolicy = (
        EvidenceLocationLegacyRootPolicy.ALLOW_STANDARD_ALIAS_BASE
    ),
) -> tuple[EvidenceLocationResolver, _FakeLocationStore, Path, _FakeOpener]:
    data_root = (tmp_path / "data").resolve()
    data_root.mkdir()
    store = _FakeLocationStore()
    opener = _FakeOpener()
    aliases = default_evidence_root_alias_registry(dashboard_data_root=data_root)
    resolver = EvidenceLocationResolver(
        locations=store,
        aliases=aliases,
        opener=opener,
        legacy_root_policy=legacy,
    )
    return resolver, store, data_root, opener


def test_two_data_roots_resolve_independently(tmp_path: Path) -> None:
    resolver, store, data_root, opener = _resolver(tmp_path)
    root_a = (data_root / "workflow-a" / "chembl_assay").resolve()
    root_b = (data_root / "workflow-b" / "chembl_assay").resolve()
    store.register(_location(run_id=_RUN_A, relative_data_root="workflow-a/chembl_assay"))
    store.register(_location(run_id=_RUN_B, relative_data_root="workflow-b/chembl_assay"))

    resolved_a = resolver.resolve(kind="pipeline", owner="chembl_assay", run_id=_RUN_A)
    resolved_b = resolver.resolve(kind="pipeline", owner="chembl_assay", run_id=_RUN_B)
    assert resolved_a.code is EvidenceLocationLookupCode.FOUND
    assert resolved_b.code is EvidenceLocationLookupCode.FOUND
    assert resolved_a.data_root == root_a
    assert resolved_b.data_root == root_b
    assert [root for root, _base in opener.opens] == [root_a, root_b]


def test_identity_conflict_fails_closed_without_foreign_fallback(
    tmp_path: Path,
) -> None:
    resolver, store, _data_root, opener = _resolver(tmp_path)
    store.register(_location())
    result = resolver.resolve(
        kind="pipeline",
        owner="chembl_assay",
        run_id=_RUN_A,
        expected_runtime_source_id=_SOURCE_B,
    )
    assert result.code is EvidenceLocationLookupCode.IDENTITY_CONFLICT
    assert result.context is None
    assert result.data_root is None
    assert opener.opens == []


def test_legacy_missing_opens_only_standard_alias_base(tmp_path: Path) -> None:
    resolver, _store, data_root, opener = _resolver(tmp_path)
    isolated = (data_root / "workflow-a" / "chembl_assay").resolve()
    result = resolver.resolve(kind="pipeline", owner="chembl_assay", run_id=_RUN_A)
    assert result.code is EvidenceLocationLookupCode.LOCATION_MISSING
    assert result.used_legacy_standard_root is True
    assert result.data_root == data_root
    assert result.context is not None
    assert result.context.data_root == data_root
    assert result.context.data_root != isolated
    assert opener.opens == [(data_root, data_root)]


def test_legacy_policy_require_explicit_record_stays_closed(tmp_path: Path) -> None:
    resolver, _store, _data_root, opener = _resolver(
        tmp_path,
        legacy=EvidenceLocationLegacyRootPolicy.REQUIRE_EXPLICIT_RECORD,
    )
    result = resolver.resolve(kind="pipeline", owner="chembl_assay", run_id=_RUN_A)
    assert result.code is EvidenceLocationLookupCode.LOCATION_MISSING
    assert result.context is None
    assert result.data_root is None
    assert opener.opens == []


def test_resolve_does_not_register_via_read_port(tmp_path: Path) -> None:
    resolver, store, _data_root, _opener = _resolver(tmp_path)
    before = dict(store.records)
    resolver.resolve(kind="pipeline", owner="chembl_assay", run_id=_RUN_A)
    assert store.records == before
    assert (
        store.lookup(kind="pipeline", owner="chembl_assay", run_id=_RUN_A).code
        is EvidenceLocationLookupCode.LOCATION_MISSING
    )


def test_manifest_missing_stays_distinct_after_resolve(tmp_path: Path) -> None:
    resolver, store, _data_root, _opener = _resolver(tmp_path)
    store.register(_location())
    resolved = resolver.resolve(kind="pipeline", owner="chembl_assay", run_id=_RUN_A)
    assert resolved.is_open
    manifest_lookup = resolver.load_manifest(resolved, run_id=UUID(_RUN_A))
    assert manifest_lookup.code is EvidenceLocationLookupCode.MANIFEST_MISSING


def test_explicit_dot_relative_uses_standard_root(tmp_path: Path) -> None:
    resolver, store, data_root, _opener = _resolver(
        tmp_path,
        legacy=EvidenceLocationLegacyRootPolicy.REQUIRE_EXPLICIT_RECORD,
    )
    store.register(_location(relative_data_root="."))
    resolved = resolver.resolve(kind="pipeline", owner="chembl_assay", run_id=_RUN_A)
    assert resolved.code is EvidenceLocationLookupCode.FOUND
    assert resolved.data_root == data_root
    assert resolved.used_legacy_standard_root is True


def test_workflow_location_reads_workflow_manifest_port(tmp_path: Path) -> None:
    resolver, store, data_root, opener = _resolver(tmp_path)
    store.register(
        _location(
            kind=EvidenceLocationKind.WORKFLOW,
            owner="workflow-a",
            run_id=_WF,
            workflow_run_id=None,
            relative_data_root=".",
        )
    )
    context = _FakeReadContext(data_root=data_root)
    workflow_manifest: Any = object()
    context.workflow_manifests[UUID(_WF)] = workflow_manifest
    opener.contexts[data_root] = context

    resolved = resolver.resolve(
        kind=EvidenceLocationKind.WORKFLOW,
        owner="workflow-a",
        run_id=_WF,
    )
    manifest_lookup = resolver.load_manifest(resolved, run_id=UUID(_WF))
    assert manifest_lookup.code is EvidenceLocationLookupCode.FOUND
    assert context.pipeline_manifests == {}
