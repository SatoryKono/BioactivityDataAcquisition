"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import YAML_SUFFIX, _rel_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_contexts import ContractEntryContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_add_contract_policy_artifact",
    "_contract_policy_config_path",
    "_contract_policy_fields",
]


def _contract_policy_config_path(context: ContractEntryContext) -> Path:
    return (
        context.root / "configs" / "contracts" / context.contract_ref.replace(".", "/")
    ).with_suffix(YAML_SUFFIX)


def _contract_policy_fields(contract_config: dict[str, object]) -> dict[str, object]:
    return {
        "contract_config_version": contract_config.get("contract_version"),
        "contract_config_ref": contract_config.get("contract_ref"),
        "soft_fail_threshold": contract_config.get("soft_fail_threshold"),
        "hard_fail_threshold": contract_config.get("hard_fail_threshold"),
        "strict_validation": contract_config.get(
            "strict_dq_validation", contract_config.get("strict_validation")
        ),
        "invalid_record_policy": contract_config.get("invalid_record_policy"),
        "default_disposition_policy": contract_config.get("default_disposition_policy"),
    }


def _add_contract_policy_artifact(
    snapshot: GraphSnapshot,
    *,
    context: ContractEntryContext,
    contract_config_path: Path,
) -> NodeKey:
    relative_path = _rel_path(context.root, contract_config_path)
    return snapshot.add_node(
        "config_artifact",
        relative_path,
        summary=f"Contract policy config for `{context.contract_ref}`.",
        source_path=relative_path,
        source_kind="contract_config",
        last_verified=context.today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
