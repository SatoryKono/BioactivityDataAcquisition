"""DTOs for contract migration planning workflows."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "ContractMigrationAction",
    "ContractMigrationActionRecord",
    "ContractMigrationPlan",
    "ContractMigrationPlanSummary",
    "ContractVersionTransition",
    "ContractVersionTransitionRecord",
]


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


ContractMigrationAction = ContractMigrationActionRecord
ContractVersionTransition = ContractVersionTransitionRecord
ContractMigrationPlan = ContractMigrationPlanSummary
