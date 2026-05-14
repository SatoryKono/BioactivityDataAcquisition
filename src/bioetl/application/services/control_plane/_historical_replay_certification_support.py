"""Support collaborators for historical replay certification workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast

from bioetl.application.services.control_plane.run_ledger_service import (
    RunLedgerService,
)
from bioetl.application.services.control_plane.run_manifest_diagnostics import (
    build_diagnostics_summary,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.ports import RunLedgerPort, RunManifestPort
from bioetl.domain.types import RunID


class HistoricalReplayCertificationProtocol(Protocol):
    """Structural type for snapshot certifications."""

    provider: str
    entity: str
    pipeline_name: str
    query: str | None
    upstream_run_id: str | None
    upstream_manifest_id: str | None


@dataclass(frozen=True, slots=True)
class HistoricalReplayCertificationResult:
    """Bounded result of one historical replay certification workflow."""

    manifest_id: str
    run_id: str
    certification_scope: str
    appended_snapshot_count: int
    replay_occurrence_kind: str
    broader_historical_exact_replay_state: str


@dataclass(frozen=True, slots=True)
class HistoricalReplayCertificationResultAssembler:
    """Assemble bounded certification results from manifest diagnostics."""

    ledger_port: RunLedgerPort

    def build(
        self,
        *,
        manifest: RunManifest,
        certification_scope: str,
    ) -> HistoricalReplayCertificationResult:
        diagnostics = build_diagnostics_summary(
            manifest,
            tuple(self.ledger_port.list_entries(manifest.manifest_id)),
        )
        input_snapshots = diagnostics.get("input_snapshots", [])
        appended_snapshot_count = (
            len(input_snapshots) if isinstance(input_snapshots, list) else 0
        )
        return HistoricalReplayCertificationResult(
            manifest_id=manifest.manifest_id,
            run_id=str(manifest.run_id),
            certification_scope=certification_scope,
            appended_snapshot_count=appended_snapshot_count,
            replay_occurrence_kind=str(
                diagnostics.get("replay_occurrence_kind") or "unknown"
            ),
            broader_historical_exact_replay_state=str(
                diagnostics.get("broader_historical_exact_replay_state") or "unknown"
            ),
        )


@dataclass(frozen=True, slots=True)
class HistoricalReplayCertificationValidator:
    """Validate source/composite certification preconditions."""

    manifest_port: RunManifestPort
    ledger_port: RunLedgerPort

    def load_manifest(
        self,
        *,
        manifest_id: str | None,
        run_id: RunID | None,
    ) -> RunManifest:
        if (manifest_id is None) == (run_id is None):
            raise ValueError("Provide exactly one of manifest_id or run_id")
        manifest = (
            self.manifest_port.get(manifest_id)
            if manifest_id is not None
            else self.manifest_port.get_by_run_id(cast(RunID, run_id))
        )
        if manifest is None:
            raise ValueError("Run manifest was not found")
        return manifest

    @staticmethod
    def validate_source_context(manifest: RunManifest) -> None:
        execution_context = str(manifest.launch_context.get("execution_context") or "")
        if execution_context == "composite" or manifest.provider == "composite":
            raise ValueError("Historical source certification requires source context")

    @staticmethod
    def validate_composite_context(manifest: RunManifest) -> None:
        execution_context = str(manifest.launch_context.get("execution_context") or "")
        if execution_context != "composite" and manifest.provider != "composite":
            raise ValueError(
                "Historical composite certification requires composite context"
            )

    def validate_certification_coverage(
        self,
        *,
        manifest: RunManifest,
        certifications: tuple[HistoricalReplayCertificationProtocol, ...],
    ) -> None:
        if not certifications:
            raise ValueError("At least one certification snapshot is required")
        expected = self._build_expected_source_keys(manifest)
        actual = self._build_actual_source_keys(certifications)
        missing = self._find_missing_source_keys(expected, actual)
        if missing:
            raise ValueError(
                "Historical replay certification is missing sources: "
                + ", ".join(" / ".join(part or "-" for part in key) for key in missing)
            )

    def validate_upstream_certified_lineage(
        self,
        certifications: tuple[HistoricalReplayCertificationProtocol, ...],
    ) -> None:
        for certification in certifications:
            self._validate_upstream_presence(certification)
            upstream_manifest = self._load_upstream_manifest(certification)
            self._validate_upstream_run_id_match(
                certification=certification,
                upstream_manifest=upstream_manifest,
            )
            self._validate_upstream_certification_state(upstream_manifest)

    def resolve_certification_query(
        self,
        *,
        manifest: RunManifest,
        certification: HistoricalReplayCertificationProtocol,
    ) -> str | None:
        query = str(certification.query or "").strip()
        if query:
            return query
        matching_queries = self._find_matching_queries(manifest, certification)
        if len(matching_queries) == 1:
            return matching_queries[0]
        return None

    @staticmethod
    def build_ledger_service(
        *,
        manifest: RunManifest,
        ledger_port: RunLedgerPort,
    ) -> RunLedgerService:
        provenance = manifest.code_provenance
        return RunLedgerService(
            ledger_port=ledger_port,
            manifest_id=manifest.manifest_id,
            run_id=manifest.run_id,
            pipeline_name=manifest.pipeline_name,
            provider=manifest.provider,
            entity=manifest.entity,
            run_type=manifest.run_type.value,
            resolved_config_hash=provenance.resolved_config_hash,
            effective_config_hash=provenance.effective_config_hash,
            contract_ref=provenance.contract_ref,
            contract_version=provenance.contract_version,
            dq_policy_ref=provenance.dq_policy_ref,
            rule_bundle_version=provenance.rule_bundle_version,
            dq_contract_compatibility_hash=provenance.dq_contract_compatibility_hash,
            effective_config_artifact_id=provenance.effective_config_artifact_id,
        )

    @staticmethod
    def _build_expected_source_keys(
        manifest: RunManifest,
    ) -> set[tuple[str, str, str, str | None]]:
        expected = {
            _source_key(
                provider=ref.provider,
                entity=ref.entity,
                pipeline_name=ref.pipeline_name,
                query=ref.query,
            )
            for ref in manifest.source_refs
        }
        if not expected and manifest.provider != "composite":
            expected = {
                _source_key(
                    provider=manifest.provider,
                    entity=manifest.entity,
                    pipeline_name=manifest.pipeline_name,
                    query=None,
                )
            }
        return expected

    @staticmethod
    def _build_actual_source_keys(
        certifications: tuple[HistoricalReplayCertificationProtocol, ...],
    ) -> set[tuple[str, str, str, str | None]]:
        return {
            _source_key(
                provider=item.provider,
                entity=item.entity,
                pipeline_name=item.pipeline_name,
                query=item.query,
            )
            for item in certifications
        }

    @staticmethod
    def _find_missing_source_keys(
        expected: set[tuple[str, str, str, str | None]],
        actual: set[tuple[str, str, str, str | None]],
    ) -> list[tuple[str, str, str, str | None]]:
        actual_without_query = {(a, b, c) for a, b, c, _ in actual}
        return sorted(
            key
            for key in expected
            if key not in actual and key[:3] not in actual_without_query
        )

    @staticmethod
    def _validate_upstream_presence(
        certification: HistoricalReplayCertificationProtocol,
    ) -> None:
        upstream_manifest_id = str(certification.upstream_manifest_id or "").strip()
        upstream_run_id = str(certification.upstream_run_id or "").strip()
        if not upstream_manifest_id or not upstream_run_id:
            raise ValueError(
                "Composite certification requires upstream_run_id and upstream_manifest_id"
            )

    def _load_upstream_manifest(
        self,
        certification: HistoricalReplayCertificationProtocol,
    ) -> RunManifest:
        upstream_manifest_id = str(certification.upstream_manifest_id or "").strip()
        upstream_manifest = self.manifest_port.get(upstream_manifest_id)
        if upstream_manifest is None:
            raise ValueError(
                f"Upstream manifest {upstream_manifest_id!r} was not found"
            )
        return upstream_manifest

    def _validate_upstream_run_id_match(
        self,
        *,
        certification: HistoricalReplayCertificationProtocol,
        upstream_manifest: RunManifest,
    ) -> None:
        upstream_run_id = str(certification.upstream_run_id or "").strip()
        upstream_summary = build_diagnostics_summary(
            upstream_manifest,
            tuple(self.ledger_port.list_entries(upstream_manifest.manifest_id)),
        )
        if str(upstream_summary.get("run_id") or "") != upstream_run_id:
            raise ValueError(
                "Composite certification upstream run_id does not match manifest"
            )

    def _validate_upstream_certification_state(
        self,
        upstream_manifest: RunManifest,
    ) -> None:
        upstream_summary = build_diagnostics_summary(
            upstream_manifest,
            tuple(self.ledger_port.list_entries(upstream_manifest.manifest_id)),
        )
        valid_states = {
            "within_launch_time_snapshot_boundary",
            "within_post_capture_parent_boundary",
            "historical_source_replay_certified",
        }
        if (
            str(upstream_summary.get("broader_historical_exact_replay_state") or "")
            not in valid_states
        ):
            raise ValueError(
                "Composite certification requires certified or snapshot-backed upstream lineage"
            )

    @staticmethod
    def _find_matching_queries(
        manifest: RunManifest,
        certification: HistoricalReplayCertificationProtocol,
    ) -> list[str]:
        return sorted(
            {
                str(ref.query or "").strip()
                for ref in manifest.source_refs
                if _source_ref_matches_certification(ref, certification)
            }
        )


def _source_ref_matches_certification(
    ref: object,
    certification: HistoricalReplayCertificationProtocol,
) -> bool:
    return (
        str(getattr(ref, "provider", "") or "").strip() == certification.provider
        and str(getattr(ref, "entity", "") or "").strip() == certification.entity
        and str(getattr(ref, "pipeline_name", "") or "").strip()
        == certification.pipeline_name
        and str(getattr(ref, "query", "") or "").strip()
    )


def _source_key(
    *,
    provider: object,
    entity: object,
    pipeline_name: object,
    query: object,
) -> tuple[str, str, str, str | None]:
    query_text = str(query or "").strip()
    return (
        str(provider or "").strip(),
        str(entity or "").strip(),
        str(pipeline_name or "").strip(),
        query_text or None,
    )
