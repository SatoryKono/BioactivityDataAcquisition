"""Planner-only service for contract migration maintenance workflows."""

from __future__ import annotations

__all__ = [
    "ContractMigrationAction",
    "ContractMigrationActionRecord",
    "ContractMigrationPlan",
    "ContractMigrationPlanSummary",
    "ContractMigrationService",
    "ContractPolicyLoaderPort",
    "ContractPolicyPort",
    "ContractVersionTransition",
    "ContractVersionTransitionRecord",
    "PipelineInfoLoaderPort",
    "RegistryEntriesLoaderPort",
]

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from bioetl.application.services.config_service import PipelineInfo

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


class ContractPolicyPort(Protocol):
    """Minimal contract policy surface required by migration planning."""

    @property
    def contract_ref(self) -> str:
        """Return the canonical contract reference."""
        ...

    @property
    def active_version(self) -> str:
        """Return the currently active contract version."""
        ...

    @property
    def rollout_mode(self) -> str:
        """Return the rollout mode."""
        ...

    @property
    def read_order(self) -> list[str]:
        """Return ordered read versions."""
        ...

    @property
    def write_versions(self) -> list[str]:
        """Return ordered write target versions."""
        ...

    @property
    def affects_hash(self) -> bool:
        """Return whether the rollout changes record hash semantics."""
        ...


class PipelineInfoLoaderPort(Protocol):
    """Callable contract for pipeline identity resolution."""

    def __call__(self, pipeline_name: str) -> PipelineInfo:
        """Resolve provider/entity metadata for one pipeline."""
        ...


class ContractPolicyLoaderPort(Protocol):
    """Callable contract for loading contract policy by provider/entity."""

    def __call__(self, provider: str, entity: str) -> ContractPolicyPort:
        """Load the typed contract policy."""
        ...


class RegistryEntriesLoaderPort(Protocol):
    """Callable contract for retrieving raw registry entries."""

    def __call__(self) -> dict[str, dict[str, object]]:
        """Load registry entries keyed by contract ref."""
        ...


@dataclass(frozen=True, slots=True)
class ContractMigrationActionRecord:
    """One required operator action emitted by the planner."""

    code: str
    title: str
    description: str

    def to_payload(self) -> dict[str, str]:
        """Serialize the action for CLI/reporting output."""
        return {
            "code": self.code,
            "title": self.title,
            "description": self.description,
        }


@dataclass(frozen=True, slots=True)
class ContractVersionTransitionRecord:
    """One active-to-shadow contract transition candidate."""

    from_version: str
    to_version: str
    migration_guide: str | None
    affects_hash: bool

    def to_payload(self) -> dict[str, object]:
        """Serialize the transition for CLI/reporting output."""
        return {
            "from_version": self.from_version,
            "to_version": self.to_version,
            "migration_guide": self.migration_guide,
            "affects_hash": self.affects_hash,
        }


@dataclass(frozen=True, slots=True)
class ContractMigrationPlanSummary:
    """Planner-only migration summary for one logical pipeline."""

    pipeline_name: str
    provider: str
    entity_type: str
    contract_ref: str
    active_version: str
    rollout_mode: str
    read_order: tuple[str, ...]
    write_versions: tuple[str, ...]
    shadow_versions: tuple[str, ...]
    affects_hash: bool
    supported_versions: tuple[str, ...]
    transitions: tuple[ContractVersionTransitionRecord, ...]
    required_actions: tuple[ContractMigrationActionRecord, ...]
    notes: tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        """Serialize the plan for inspection-style CLI output."""
        return {
            "pipeline_name": self.pipeline_name,
            "provider": self.provider,
            "entity_type": self.entity_type,
            "contract_ref": self.contract_ref,
            "active_version": self.active_version,
            "rollout_mode": self.rollout_mode,
            "read_order": list(self.read_order),
            "write_versions": list(self.write_versions),
            "shadow_versions": list(self.shadow_versions),
            "affects_hash": self.affects_hash,
            "supported_versions": list(self.supported_versions),
            "transitions": [item.to_payload() for item in self.transitions],
            "required_actions": [item.to_payload() for item in self.required_actions],
            "notes": list(self.notes),
        }


@dataclass
class ContractMigrationService:
    """Build planner-only migration plans from pipeline contract rollout state."""

    logger: LoggerPort
    _pipeline_info_loader: PipelineInfoLoaderPort
    _contract_policy_loader: ContractPolicyLoaderPort
    _registry_entries_loader: RegistryEntriesLoaderPort

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


ContractMigrationAction = ContractMigrationActionRecord
ContractVersionTransition = ContractVersionTransitionRecord
ContractMigrationPlan = ContractMigrationPlanSummary
