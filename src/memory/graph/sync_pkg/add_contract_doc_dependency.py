"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _as_mapping, _rel_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.dashboard_metrics import _path_contains_any_token
from memory.graph.sync_pkg.default_batch_size import CONTRACT_REGISTRY_RELATIVE_PATH
from memory.graph.sync_pkg.graph_contexts import ContractEntryContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.link_contract_provider import _link_contract_provider

__all__ = [
    "_add_contract_doc_dependency",
    "_add_contract_entry_surface",
    "_contract_dependency_doc_path",
]


def _add_contract_doc_dependency(
    snapshot: GraphSnapshot,
    *,
    context: ContractEntryContext,
    doc_path: str,
    summary: str,
    source_kind: str,
) -> NodeKey:
    return snapshot.add_node(
        "doc_artifact",
        doc_path,
        summary=summary.format(contract_ref=context.contract_ref),
        source_path=doc_path,
        source_kind=source_kind,
        last_verified=context.today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )


def _contract_dependency_doc_path(
    root: Path,
    doc_path: str,
    anchor_fields: list[str],
) -> Path | None:
    resolved_doc = root / doc_path
    if not resolved_doc.is_file() or not _path_contains_any_token(
        resolved_doc, anchor_fields
    ):
        return None
    return resolved_doc


def _add_contract_entry_surface(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    registry_artifact: NodeKey,
    *,
    contract_ref: str,
    raw_entry: dict[str, object],
    today: str,
) -> ContractEntryContext:
    identity = _as_mapping(raw_entry.get("identity"))
    registry_path = root / CONTRACT_REGISTRY_RELATIVE_PATH
    contract = snapshot.add_node(
        "contract_surface",
        contract_ref,
        summary=f"Published contract surface `{contract_ref}`.",
        source_path=_rel_path(root, registry_path),
        source_kind="contract_registry",
        status=raw_entry.get("status"),
        contract_version=identity.get("contract_version"),
        compatibility_level=identity.get("compatibility_level"),
        schema_hash=identity.get("schema_hash"),
        dq_policy_ref=raw_entry.get("dq_policy_ref") or identity.get("dq_policy_ref"),
        rule_bundle_version=raw_entry.get("rule_bundle_version")
        or identity.get("rule_bundle_version"),
        owners=raw_entry.get("owners"),
        supported_versions=raw_entry.get("supported_versions"),
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(
        project, "HAS_CONTRACT", contract, provenance="impact_contracts"
    )
    snapshot.add_relation(
        contract, "BACKED_BY", registry_artifact, provenance="impact_contracts"
    )
    _link_contract_provider(snapshot, contract_ref, contract)
    return ContractEntryContext(
        root=root,
        registry_path=registry_path,
        today=today,
        contract_ref=contract_ref,
        contract=contract,
        raw_entry=raw_entry,
    )
