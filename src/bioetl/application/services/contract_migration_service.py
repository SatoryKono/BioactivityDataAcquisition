"""Planner-only service for contract migration maintenance workflows."""

from __future__ import annotations

__all__ = [
    "ContractMigrationAction",
    "ContractMigrationActionRecord",
    "ContractMigrationPlan",
    "ContractMigrationPlanSummary",
    "ContractMigrationService",
    "ContractPolicyLoaderProtocol",
    "ContractPolicyProtocol",
    "ContractVersionTransition",
    "ContractVersionTransitionRecord",
    "PipelineInfoLoaderProtocol",
    "RegistryEntriesLoaderProtocol",
]

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.services.contract_migration_models import (
    ContractMigrationAction,
    ContractMigrationActionRecord,
    ContractMigrationPlan,
    ContractMigrationPlanSummary,
    ContractVersionTransition,
    ContractVersionTransitionRecord,
)
from bioetl.application.services.contract_migration_ports import (
    ContractPolicyLoaderProtocol,
    ContractPolicyProtocol,
    PipelineInfoLoaderProtocol,
    RegistryEntriesLoaderProtocol,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


@dataclass
class ContractMigrationService:
    """Build planner-only migration plans from pipeline contract rollout state."""

    logger: LoggerPort
    _pipeline_info_loader: PipelineInfoLoaderProtocol
    _contract_policy_loader: ContractPolicyLoaderProtocol
    _registry_entries_loader: RegistryEntriesLoaderProtocol

    def plan_pipeline(self, pipeline_name: str) -> ContractMigrationPlanSummary:
        """Return the planner-only contract migration plan for one pipeline."""
        self.logger.debug("Planning contract migration", pipeline=pipeline_name)
        pipeline_info = self._pipeline_info_loader(pipeline_name)
        policy = self._contract_policy_loader(
            pipeline_info.provider,
            pipeline_info.entity_type,
        )
        registry_entries = self._registry_entries_loader()
        entry = registry_entries.get(policy.contract_ref)
        registry_entry = entry if isinstance(entry, dict) else {}

        shadow_versions = self._shadow_versions(
            active_version=policy.active_version,
            read_order=policy.read_order,
            write_versions=policy.write_versions,
        )
        transitions = tuple(
            ContractVersionTransitionRecord(
                from_version=policy.active_version,
                to_version=shadow_version,
                migration_guide=self._resolve_migration_guide(
                    registry_entry,
                    from_version=policy.active_version,
                    to_version=shadow_version,
                ),
                affects_hash=policy.affects_hash,
            )
            for shadow_version in shadow_versions
        )
        required_actions = self._required_actions(
            has_shadow_versions=bool(shadow_versions),
            affects_hash=policy.affects_hash,
        )
        plan = ContractMigrationPlanSummary(
            pipeline_name=pipeline_info.name,
            provider=pipeline_info.provider,
            entity_type=pipeline_info.entity_type,
            contract_ref=policy.contract_ref,
            active_version=policy.active_version,
            rollout_mode=policy.rollout_mode,
            read_order=tuple(policy.read_order),
            write_versions=tuple(policy.write_versions),
            shadow_versions=shadow_versions,
            affects_hash=policy.affects_hash,
            supported_versions=self._supported_versions(registry_entry),
            transitions=transitions,
            required_actions=required_actions,
            notes=self._notes(
                active_version=policy.active_version,
                shadow_versions=shadow_versions,
                affects_hash=policy.affects_hash,
            ),
        )
        self.logger.info(
            "Planned contract migration",
            pipeline=pipeline_name,
            contract_ref=plan.contract_ref,
            active_version=plan.active_version,
            shadow_versions=list(plan.shadow_versions),
            affects_hash=plan.affects_hash,
        )
        return plan

    @staticmethod
    def _shadow_versions(
        *,
        active_version: str,
        read_order: list[str],
        write_versions: list[str],
    ) -> tuple[str, ...]:
        ordered: list[str] = []
        for version in [*read_order, *write_versions]:
            if version == active_version or version in ordered:
                continue
            ordered.append(version)
        return tuple(ordered)

    @staticmethod
    def _supported_versions(
        registry_entry: dict[str, object],
    ) -> tuple[str, ...]:
        supported_versions = registry_entry.get("supported_versions")
        if not isinstance(supported_versions, list):
            return ()
        ordered: list[str] = []
        for version in supported_versions:
            normalized = str(version).strip()
            if not normalized or normalized in ordered:
                continue
            ordered.append(normalized)
        return tuple(ordered)

    @staticmethod
    def _resolve_migration_guide(
        registry_entry: dict[str, object],
        *,
        from_version: str,
        to_version: str,
    ) -> str | None:
        guides = registry_entry.get("migration_guides")
        if not isinstance(guides, dict):
            return None
        forward_key = f"{from_version}->{to_version}"
        reverse_key = f"{to_version}->{from_version}"
        for key in (forward_key, reverse_key):
            candidate = guides.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        return None

    @staticmethod
    def _required_actions(
        *,
        has_shadow_versions: bool,
        affects_hash: bool,
    ) -> tuple[ContractMigrationActionRecord, ...]:
        if not has_shadow_versions:
            return ()
        if affects_hash:
            return (
                ContractMigrationActionRecord(
                    code="silver_backfill_rebuild",
                    title="Silver backfill/rebuild",
                    description=(
                        "Rebuild or backfill Silver outputs for the shadow contract "
                        "version before any cutover because hashes change."
                    ),
                ),
                ContractMigrationActionRecord(
                    code="gold_backfill_rebuild",
                    title="Gold backfill/rebuild",
                    description=(
                        "Rebuild or backfill Gold outputs from the selected Silver "
                        "contract version before cutover."
                    ),
                ),
                ContractMigrationActionRecord(
                    code="verification_before_cutover",
                    title="Verification before cutover",
                    description=(
                        "Verify shadow reads/writes and data parity before promoting "
                        "the new contract version."
                    ),
                ),
            )
        return (
            ContractMigrationActionRecord(
                code="verification_before_cutover",
                title="Verification before cutover",
                description=(
                    "Verify shadow reads/writes and contract compatibility before "
                    "promoting the new contract version."
                ),
            ),
        )

    @staticmethod
    def _notes(
        *,
        active_version: str,
        shadow_versions: tuple[str, ...],
        affects_hash: bool,
    ) -> tuple[str, ...]:
        if not shadow_versions:
            return (
                "No shadow contract versions are configured; rollout is in steady-state.",
            )

        notes = [
            (
                "Rollback remains possible while the active contract version stays "
                "present in both read_order and write_versions."
            ),
            (
                "Cutover should switch active_version only after the required actions "
                "and verification complete."
            ),
        ]
        if affects_hash:
            notes.append(
                "This rollout changes content-hash semantics, so historical Silver "
                "and downstream Gold materializations must be rebuilt for cutover."
            )
        else:
            notes.append(
                "This rollout does not change content-hash semantics, so shadow "
                "validation can focus on schema/contract compatibility."
            )
        notes.append(
            f"Current active contract version is {active_version}; shadow versions: "
            + ", ".join(shadow_versions)
            + "."
        )
        return tuple(notes)
