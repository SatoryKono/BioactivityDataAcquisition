"""Private support collaborators for historical replay certification workflows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from bioetl.application.services.control_plane.ledger.service import (
    RunLedgerService,
)
from bioetl.application.services.control_plane.replay._historical_certification_models import (
    HistoricalReplayCertificationProtocol as HistoricalReplayCertificationProtocol,
)
from bioetl.application.services.control_plane.replay._historical_certification_models import (
    HistoricalReplayCertificationResult as HistoricalReplayCertificationResult,
)
from bioetl.application.services.control_plane.replay._historical_certification_models import (
    HistoricalReplayCertificationResultAssembler as HistoricalReplayCertificationResultAssembler,
)
from bioetl.application.services.control_plane.replay._historical_certification_models import (
    _source_key,
)
from bioetl.application.services.control_plane.replay._historical_certification_upstream import (
    load_upstream_manifest,
    validate_upstream_certification_state,
    validate_upstream_presence,
    validate_upstream_run_id_match,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.ports import RunLedgerPort, RunManifestPort
from bioetl.domain.types import RunID

__all__ = [
    "HistoricalReplayCertificationProtocol",
    "HistoricalReplayCertificationResult",
    "HistoricalReplayCertificationResultAssembler",
    "HistoricalReplayCertificationValidator",
]


@dataclass(frozen=True, slots=True)
class HistoricalReplayCertificationValidator:
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
            validate_upstream_presence(certification)
            upstream_manifest = load_upstream_manifest(
                manifest_port=self.manifest_port,
                certification=certification,
            )
            validate_upstream_run_id_match(
                certification=certification,
                upstream_manifest=upstream_manifest,
            )
            validate_upstream_certification_state(
                ledger_port=self.ledger_port,
                upstream_manifest=upstream_manifest,
            )

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
        if len(matching_queries) > 1:
            raise ValueError(
                "Historical replay certification query is ambiguous for "
                f"{certification.provider}/{certification.entity}/"
                f"{certification.pipeline_name}: {', '.join(matching_queries)}"
            )
        return None

    @staticmethod
    def build_ledger_service(
        *,
        manifest: RunManifest,
        ledger_port: RunLedgerPort,
        entry_id_factory: Callable[[], str],
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
            _entry_id_factory=entry_id_factory,
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
        actual_unscoped = {
            (provider, entity, pipeline)
            for provider, entity, pipeline, query in actual
            if query is None
        }
        return sorted(
            key
            for key in expected
            if key not in actual and key[:3] not in actual_unscoped
        )

    @staticmethod
    def _find_matching_queries(
        manifest: RunManifest,
        certification: HistoricalReplayCertificationProtocol,
    ) -> list[str]:
        matching_queries = [
            ref.query
            for ref in manifest.source_refs
            if ref.provider == certification.provider
            and ref.entity == certification.entity
            and ref.pipeline_name == certification.pipeline_name
            and ref.query
        ]
        return sorted({query for query in matching_queries if query is not None})
