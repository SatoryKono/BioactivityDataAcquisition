"""Import high-signal relations from the expanded knowledge-graph snapshot."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict, deque
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from memory.resources import MEMORY_ROOT

GENERATOR_VERSION = 1
DEFAULT_PROJECTION_DIR = MEMORY_ROOT / "graph" / "projections"
DEFAULT_INDEX_DIR = MEMORY_ROOT / "graph" / "indexes"
PIPELINE_NODE_TYPES = {"Pipeline", "CompositePipeline"}
SEMANTIC_GRAPH_EDGE_RELATIONS = {
    "configured_by": "defined_by",
    "writes_to": "writes_to",
    "reads_from": "reads_from",
    "orchestrates": "orchestrates",
}
ADR_REF_PATTERN = re.compile(r"\bADR-(\d{3})\b", re.IGNORECASE)
ADR_LIFECYCLE_FIELDS = ("supersedes", "superseded by", "amends", "amended by")
RUNBOOK_EXCLUDED_STEMS = frozenset({"index"})
CONFIGS_DIR_PREFIX = "configs/"
ADR_DOC_GLOB = "ADR-*.md"
_PATH_REF_PREFIXES = ("src/", "configs/", "tests/", "docs/")
_PATH_REF_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-/"
)


def default_expanded_graph_path(root: Path) -> Path:
    """Return the conventional expanded graph snapshot input path."""
    return (
        root
        / "src"
        / "memory"
        / "graph"
        / "projections"
        / "bioetl_knowledge_graph_expanded.json"
    )


def load_expanded_graph(path: Path) -> dict[str, Any]:
    """Load an expanded graph snapshot and validate its coarse shape."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("expanded graph snapshot must be a JSON object")
    if not isinstance(payload.get("nodes"), dict) or not isinstance(
        payload.get("edges"), dict
    ):
        raise ValueError("expanded graph snapshot must contain object nodes and edges")
    return payload


def iter_file_reference_records(
    payload: dict[str, Any],
    *,
    source_snapshot: str,
) -> list[dict[str, Any]]:
    """Return normalized ``file -> references_file -> file`` relation records."""
    nodes: dict[str, dict[str, Any]] = payload["nodes"]
    edges: dict[str, dict[str, Any]] = payload["edges"]
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    snapshot_generated_at = str(meta.get("generated_at") or "unknown")
    records: list[dict[str, Any]] = []

    for edge_id, edge in edges.items():
        if edge.get("edge_type") != "references_file":
            continue
        source_node = nodes.get(str(edge.get("source"))) or {}
        target_node = nodes.get(str(edge.get("target"))) or {}
        source_path = _node_source_path(source_node)
        target_path = _node_source_path(target_node)
        if not source_path or not target_path:
            continue
        records.append(
            {
                "id": f"{source_path}|references_file|{target_path}",
                "source_id": str(edge.get("source") or ""),
                "source_path": source_path,
                "target_id": str(edge.get("target") or ""),
                "target_path": target_path,
                "relation": "references_file",
                "confidence": "derived",
                "provenance": "bioetl_knowledge_graph_expanded.references_file",
                "source_snapshot": source_snapshot,
                "source_generated_at": snapshot_generated_at,
                "edge_id": str(edge_id),
                "description": str(edge.get("description") or ""),
                "evidence": edge.get("meta")
                if isinstance(edge.get("meta"), dict)
                else {},
            }
        )
    records.sort(key=lambda item: (item["source_path"], item["target_path"]))
    return records


def iter_module_reference_records(
    payload: dict[str, Any],
    *,
    source_snapshot: str,
) -> list[dict[str, Any]]:
    """Return normalized ``module -> references -> module`` relation records."""
    nodes: dict[str, dict[str, Any]] = payload["nodes"]
    edges: dict[str, dict[str, Any]] = payload["edges"]
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    snapshot_generated_at = str(meta.get("generated_at") or "unknown")
    records: list[dict[str, Any]] = []

    for edge_id, edge in edges.items():
        record = _module_reference_record(
            edge_id=edge_id,
            edge=edge,
            nodes=nodes,
            source_snapshot=source_snapshot,
            snapshot_generated_at=snapshot_generated_at,
        )
        if record is not None:
            records.append(record)
    records.sort(key=lambda item: (item["source_name"], item["target_name"]))
    return records


def _module_reference_record(
    *,
    edge_id: str,
    edge: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    source_snapshot: str,
    snapshot_generated_at: str,
) -> dict[str, Any] | None:
    if edge.get("edge_type") != "references":
        return None
    source_id = str(edge.get("source") or "")
    target_id = str(edge.get("target") or "")
    source_node = nodes.get(source_id) or {}
    target_node = nodes.get(target_id) or {}
    if source_node.get("node_type") != "Module":
        return None
    if target_node.get("node_type") != "Module":
        return None
    source_name = _node_module_name(source_node, source_id)
    target_name = _node_module_name(target_node, target_id)
    if not source_name or not target_name:
        return None
    return {
        "id": f"{source_name}|references|{target_name}",
        "source_id": source_id,
        "source_name": source_name,
        "source_path": _node_source_path(source_node),
        "target_id": target_id,
        "target_name": target_name,
        "target_path": _node_source_path(target_node),
        "relation": "references",
        "confidence": "derived",
        "provenance": "bioetl_knowledge_graph_expanded.references",
        "source_snapshot": source_snapshot,
        "source_generated_at": snapshot_generated_at,
        "edge_id": str(edge_id),
        "description": str(edge.get("description") or ""),
        "evidence": edge.get("meta") if isinstance(edge.get("meta"), dict) else {},
    }


def iter_entity_relation_records(
    payload: dict[str, Any],
    *,
    source_snapshot: str,
    repo_root: Path | None = None,
) -> list[dict[str, Any]]:
    """Return normalized high-signal entity relation records."""
    records = [
        *iter_graph_semantic_relation_records(
            payload,
            source_snapshot=source_snapshot,
        )
    ]
    if repo_root is not None:
        records.extend(
            iter_pipeline_artifact_relation_records(
                payload,
                source_snapshot=source_snapshot,
            )
        )
        records.extend(
            iter_pipeline_test_relation_records(
                payload,
                repo_root=repo_root,
                source_snapshot=source_snapshot,
            )
        )
        records.extend(
            iter_config_test_relation_records(
                payload,
                repo_root=repo_root,
                source_snapshot=source_snapshot,
            )
        )
        records.extend(
            iter_pipeline_doc_relation_records(
                payload,
                repo_root=repo_root,
                source_snapshot=source_snapshot,
            )
        )
        records.extend(
            iter_adr_constraint_relation_records(
                repo_root=repo_root,
                source_snapshot=source_snapshot,
            )
        )
        records.extend(
            iter_doc_config_constraint_relation_records(
                repo_root=repo_root,
                source_snapshot=source_snapshot,
            )
        )
        records.extend(
            iter_adr_lifecycle_relation_records(
                repo_root=repo_root,
                source_snapshot=source_snapshot,
            )
        )
        records.extend(
            iter_runbook_failure_mode_relation_records(
                repo_root=repo_root,
                source_snapshot=source_snapshot,
            )
        )
    return _dedupe_entity_records(records)


def iter_graph_semantic_relation_records(
    payload: dict[str, Any],
    *,
    source_snapshot: str,
) -> list[dict[str, Any]]:
    """Import existing expanded graph edges into the generic entity relation index."""
    nodes: dict[str, dict[str, Any]] = payload["nodes"]
    edges: dict[str, dict[str, Any]] = payload["edges"]
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    snapshot_generated_at = str(meta.get("generated_at") or "unknown")
    records: list[dict[str, Any]] = []

    for edge_id, edge in edges.items():
        edge_type = str(edge.get("edge_type") or "")
        relation = SEMANTIC_GRAPH_EDGE_RELATIONS.get(edge_type)
        if relation is None:
            continue
        source_id = str(edge.get("source") or "")
        target_id = str(edge.get("target") or "")
        source_node = nodes.get(source_id) or {}
        target_node = nodes.get(target_id) or {}
        if not _is_supported_graph_semantic_edge(edge_type, source_node, target_node):
            continue
        records.append(
            _entity_relation_record(
                source_node=source_node,
                source_id=source_id,
                target_node=target_node,
                target_id=target_id,
                relation=relation,
                confidence="derived",
                provenance=f"bioetl_knowledge_graph_expanded.{edge_type}",
                source_snapshot=source_snapshot,
                source_generated_at=snapshot_generated_at,
                edge_id=str(edge_id),
                evidence=edge.get("meta") if isinstance(edge.get("meta"), dict) else {},
                description=str(edge.get("description") or ""),
            )
        )
    return records


def _is_supported_graph_semantic_edge(
    edge_type: str,
    source_node: dict[str, Any],
    target_node: dict[str, Any],
) -> bool:
    source_type = str(source_node.get("node_type") or "")
    target_type = str(target_node.get("node_type") or "")
    if edge_type == "configured_by":
        return source_type in PIPELINE_NODE_TYPES and target_type == "Config"
    if edge_type in {"writes_to", "reads_from"}:
        return source_type in PIPELINE_NODE_TYPES
    if edge_type == "orchestrates":
        return target_type in PIPELINE_NODE_TYPES
    return False


def iter_pipeline_test_relation_records(
    payload: dict[str, Any],
    *,
    repo_root: Path,
    source_snapshot: str,
) -> list[dict[str, Any]]:
    """Derive ``pipeline -> tested_by -> test`` relations from test matrix config."""
    test_matrix_path = repo_root / "configs" / "quality" / "test_matrix.yaml"
    if not test_matrix_path.is_file():
        return []
    matrix = yaml.safe_load(test_matrix_path.read_text(encoding="utf-8")) or {}
    ownership = matrix.get("entity_test_ownership")
    if not isinstance(ownership, dict):
        return []
    pipeline_nodes = _pipeline_nodes_by_name(payload)
    records: list[dict[str, Any]] = []
    for entity_ref, test_paths in sorted(ownership.items()):
        if not isinstance(entity_ref, str) or not isinstance(test_paths, list):
            continue
        pipeline_name = entity_ref.replace(".", "_")
        source_node = pipeline_nodes.get(pipeline_name)
        if source_node is None:
            continue
        for test_path in sorted(
            str(path) for path in test_paths if isinstance(path, str)
        ):
            records.append(
                _path_target_relation_record(
                    source_node=source_node,
                    source_id=str(source_node.get("id") or f"pipeline:{pipeline_name}"),
                    target_path=test_path,
                    target_kind="Test",
                    target_id=f"test:{test_path}",
                    relation="tested_by",
                    confidence="derived",
                    provenance="configs/quality/test_matrix.entity_test_ownership",
                    source_snapshot=source_snapshot,
                    evidence={
                        "test_matrix_path": "configs/quality/test_matrix.yaml",
                        "entity_ref": entity_ref,
                    },
                )
            )
    return records


def iter_config_test_relation_records(
    payload: dict[str, Any],
    *,
    repo_root: Path,
    source_snapshot: str,
) -> list[dict[str, Any]]:
    """Derive ``config -> tested_by -> test`` from entity test ownership."""
    test_matrix_path = repo_root / "configs" / "quality" / "test_matrix.yaml"
    if not test_matrix_path.is_file():
        return []
    matrix = yaml.safe_load(test_matrix_path.read_text(encoding="utf-8")) or {}
    ownership = matrix.get("entity_test_ownership")
    if not isinstance(ownership, dict):
        return []
    pipeline_nodes = _pipeline_nodes_by_name(payload)
    records: list[dict[str, Any]] = []
    for entity_ref, test_paths in sorted(ownership.items()):
        if not isinstance(entity_ref, str) or not isinstance(test_paths, list):
            continue
        pipeline_name = entity_ref.replace(".", "_")
        source_node = pipeline_nodes.get(pipeline_name)
        if source_node is None:
            continue
        config_path = _node_source_path(source_node)
        if not config_path.startswith(CONFIGS_DIR_PREFIX):
            continue
        for test_path in sorted(
            str(path) for path in test_paths if isinstance(path, str)
        ):
            records.append(
                _path_relation_record(
                    source_path=config_path,
                    source_kind="Config",
                    source_id=_path_entity_id(config_path),
                    source_name=config_path,
                    target_path=test_path,
                    target_kind="Test",
                    target_id=f"test:{test_path}",
                    target_name=test_path,
                    relation="tested_by",
                    confidence="derived",
                    provenance="configs/quality/test_matrix.entity_test_ownership",
                    source_snapshot=source_snapshot,
                    evidence={
                        "test_matrix_path": "configs/quality/test_matrix.yaml",
                        "entity_ref": entity_ref,
                        "pipeline_name": pipeline_name,
                    },
                )
            )
    return records


def iter_pipeline_doc_relation_records(
    payload: dict[str, Any],
    *,
    repo_root: Path,
    source_snapshot: str,
) -> list[dict[str, Any]]:
    """Derive ``pipeline -> described_by -> doc`` relations from canonical docs."""
    records: list[dict[str, Any]] = []
    for source_node in _pipeline_nodes_by_name(payload).values():
        source_id = str(source_node.get("id") or "")
        for doc_path in _pipeline_doc_paths(source_node, repo_root):
            records.append(
                _path_target_relation_record(
                    source_node=source_node,
                    source_id=source_id,
                    target_path=doc_path,
                    target_kind="Doc",
                    target_id=f"doc:{doc_path}",
                    relation="described_by",
                    confidence="inferred",
                    provenance="docs/04-reference.pipeline_path_convention",
                    source_snapshot=source_snapshot,
                    evidence={"matching_strategy": "provider_entity_doc_path"},
                )
            )
    return records


def iter_pipeline_artifact_relation_records(
    payload: dict[str, Any],
    *,
    source_snapshot: str,
) -> list[dict[str, Any]]:
    """Derive ``pipeline -> emits_artifact -> artifact`` from write edges."""
    nodes: dict[str, dict[str, Any]] = payload["nodes"]
    edges: dict[str, dict[str, Any]] = payload["edges"]
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    snapshot_generated_at = str(meta.get("generated_at") or "unknown")
    records: list[dict[str, Any]] = []
    for edge_id, edge in edges.items():
        record = _pipeline_artifact_relation_record(
            edge_id=edge_id,
            edge=edge,
            nodes=nodes,
            source_snapshot=source_snapshot,
            snapshot_generated_at=snapshot_generated_at,
        )
        if record is not None:
            records.append(record)
    return records


def iter_adr_constraint_relation_records(
    *,
    repo_root: Path,
    source_snapshot: str,
) -> list[dict[str, Any]]:
    """Derive ``ADR -> constrains -> path`` relations from explicit path refs."""
    decisions_dir = repo_root / "docs" / "02-architecture" / "decisions"
    if not decisions_dir.is_dir():
        return []
    records: list[dict[str, Any]] = []
    for adr_path in sorted(decisions_dir.glob(ADR_DOC_GLOB)):
        relative_adr_path = adr_path.relative_to(repo_root).as_posix()
        text = adr_path.read_text(encoding="utf-8")
        for target_path in sorted(_explicit_path_refs(text)):
            if target_path == relative_adr_path:
                continue
            records.append(
                {
                    "id": f"adr:{relative_adr_path}|constrains|{_path_entity_id(target_path)}",
                    "source_id": f"adr:{relative_adr_path}",
                    "source_name": adr_path.stem,
                    "source_kind": "ADR",
                    "source_path": relative_adr_path,
                    "target_id": _path_entity_id(target_path),
                    "target_name": target_path,
                    "target_kind": _path_entity_kind(target_path),
                    "target_path": target_path,
                    "relation": "constrains",
                    "confidence": "inferred",
                    "provenance": "docs/02-architecture/decisions.path_refs",
                    "source_snapshot": source_snapshot,
                    "source_generated_at": "unknown",
                    "edge_id": "",
                    "description": "",
                    "evidence": {"adr_path": relative_adr_path},
                }
            )
    return records


def iter_doc_config_constraint_relation_records(
    *,
    repo_root: Path,
    source_snapshot: str,
) -> list[dict[str, Any]]:
    """Derive ``doc -> constrains -> config`` from explicit config refs."""
    docs_root = repo_root / "docs"
    if not docs_root.is_dir():
        return []
    records: list[dict[str, Any]] = []
    for doc_path in sorted(docs_root.rglob("*.md")):
        if _is_adr_path(doc_path, repo_root):
            continue
        relative_doc_path = doc_path.relative_to(repo_root).as_posix()
        text = doc_path.read_text(encoding="utf-8")
        for target_path in sorted(_explicit_config_path_refs(text)):
            if target_path == relative_doc_path:
                continue
            records.append(
                _path_relation_record(
                    source_path=relative_doc_path,
                    source_kind="Doc",
                    source_id=f"doc:{relative_doc_path}",
                    source_name=_markdown_title(text) or relative_doc_path,
                    target_path=target_path,
                    target_kind="Config",
                    target_id=_path_entity_id(target_path),
                    target_name=target_path,
                    relation="constrains",
                    confidence="inferred",
                    provenance="docs.config_path_refs",
                    source_snapshot=source_snapshot,
                    evidence={"doc_path": relative_doc_path},
                )
            )
    return records


def iter_adr_lifecycle_relation_records(
    *,
    repo_root: Path,
    source_snapshot: str,
) -> list[dict[str, Any]]:
    """Derive ``ADR -> supersedes/amends -> ADR`` lifecycle relations."""
    decisions_dir = repo_root / "docs" / "02-architecture" / "decisions"
    if not decisions_dir.is_dir():
        return []
    adr_paths = _adr_paths_by_number(decisions_dir)
    records: list[dict[str, Any]] = []
    for adr_path in sorted(decisions_dir.glob(ADR_DOC_GLOB)):
        source_number = _adr_number(adr_path)
        if source_number is None:
            continue
        source_relative_path = adr_path.relative_to(repo_root).as_posix()
        text = adr_path.read_text(encoding="utf-8")
        for field, target_number in _iter_adr_lifecycle_refs(text):
            record = _adr_lifecycle_relation_record(
                adr_path=adr_path,
                adr_paths=adr_paths,
                declaring_path=source_relative_path,
                field=field,
                target_number=target_number,
                repo_root=repo_root,
                source_snapshot=source_snapshot,
            )
            if record is not None:
                records.append(record)
    return records


def iter_runbook_failure_mode_relation_records(
    *,
    repo_root: Path,
    source_snapshot: str,
) -> list[dict[str, Any]]:
    """Derive ``runbook -> mitigates -> failure_mode`` relations."""
    runbook_dir = repo_root / "docs" / "05-operations" / "runbooks"
    if not runbook_dir.is_dir():
        return []
    records: list[dict[str, Any]] = []
    for runbook_path in sorted(runbook_dir.glob("*.md")):
        if runbook_path.stem in RUNBOOK_EXCLUDED_STEMS:
            continue
        relative_runbook_path = runbook_path.relative_to(repo_root).as_posix()
        text = runbook_path.read_text(encoding="utf-8")
        title = _markdown_title(text) or runbook_path.stem.replace("-", " ")
        failure_mode = _failure_mode_name(title, runbook_path.stem)
        failure_slug = _slugify(failure_mode)
        records.append(
            _path_relation_record(
                source_path=relative_runbook_path,
                source_kind="Runbook",
                source_id=f"runbook:{relative_runbook_path}",
                source_name=title,
                target_path="",
                target_kind="FailureMode",
                target_id=f"failure_mode:{failure_slug}",
                target_name=failure_mode,
                relation="mitigates",
                confidence="inferred",
                provenance="docs/05-operations/runbooks.filename_and_title",
                source_snapshot=source_snapshot,
                evidence={"runbook_path": relative_runbook_path},
            )
        )
    return records


def _node_source_path(node: dict[str, Any]) -> str:
    source_path = node.get("source_path")
    if isinstance(source_path, str) and source_path:
        return source_path.replace("\\", "/")
    return ""


def _node_module_name(node: dict[str, Any], node_id: str) -> str:
    raw_id = str(node.get("id") or node_id)
    if raw_id.startswith("mod:"):
        return raw_id.removeprefix("mod:")
    label = node.get("label")
    return str(label) if isinstance(label, str) else ""


def _node_display_name(node: dict[str, Any], node_id: str) -> str:
    label = node.get("label")
    if isinstance(label, str) and label:
        return label
    raw_id = str(node.get("id") or node_id)
    return raw_id.split(":", 1)[-1] if ":" in raw_id else raw_id


def _entity_ref(node: dict[str, Any], node_id: str) -> str:
    return str(node.get("id") or node_id)


def _entity_relation_record(
    *,
    source_node: dict[str, Any],
    source_id: str,
    target_node: dict[str, Any],
    target_id: str,
    relation: str,
    confidence: str,
    provenance: str,
    source_snapshot: str,
    source_generated_at: str,
    edge_id: str,
    evidence: dict[str, Any],
    description: str,
) -> dict[str, Any]:
    source_ref = _entity_ref(source_node, source_id)
    target_ref = _entity_ref(target_node, target_id)
    return {
        "id": f"{source_ref}|{relation}|{target_ref}",
        "source_id": source_ref,
        "source_name": _node_display_name(source_node, source_id),
        "source_kind": str(source_node.get("node_type") or "Unknown"),
        "source_path": _node_source_path(source_node),
        "target_id": target_ref,
        "target_name": _node_display_name(target_node, target_id),
        "target_kind": str(target_node.get("node_type") or "Unknown"),
        "target_path": _node_source_path(target_node),
        "relation": relation,
        "confidence": confidence,
        "provenance": provenance,
        "source_snapshot": source_snapshot,
        "source_generated_at": source_generated_at,
        "edge_id": edge_id,
        "description": description,
        "evidence": evidence,
    }


def _path_target_relation_record(
    *,
    source_node: dict[str, Any],
    source_id: str,
    target_path: str,
    target_kind: str,
    target_id: str,
    relation: str,
    confidence: str,
    provenance: str,
    source_snapshot: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    source_ref = _entity_ref(source_node, source_id)
    normalized_target_path = target_path.replace("\\", "/")
    return {
        "id": f"{source_ref}|{relation}|{target_id}",
        "source_id": source_ref,
        "source_name": _node_display_name(source_node, source_id),
        "source_kind": str(source_node.get("node_type") or "Unknown"),
        "source_path": _node_source_path(source_node),
        "target_id": target_id,
        "target_name": normalized_target_path,
        "target_kind": target_kind,
        "target_path": normalized_target_path,
        "relation": relation,
        "confidence": confidence,
        "provenance": provenance,
        "source_snapshot": source_snapshot,
        "source_generated_at": "unknown",
        "edge_id": "",
        "description": "",
        "evidence": evidence,
    }


def _path_relation_record(
    *,
    source_path: str,
    source_kind: str,
    source_id: str,
    source_name: str,
    target_path: str,
    target_kind: str,
    target_id: str,
    target_name: str,
    relation: str,
    confidence: str,
    provenance: str,
    source_snapshot: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    normalized_source_path = source_path.replace("\\", "/")
    normalized_target_path = target_path.replace("\\", "/")
    return {
        "id": f"{source_id}|{relation}|{target_id}",
        "source_id": source_id,
        "source_name": source_name,
        "source_kind": source_kind,
        "source_path": normalized_source_path,
        "target_id": target_id,
        "target_name": target_name,
        "target_kind": target_kind,
        "target_path": normalized_target_path,
        "relation": relation,
        "confidence": confidence,
        "provenance": provenance,
        "source_snapshot": source_snapshot,
        "source_generated_at": "unknown",
        "edge_id": "",
        "description": "",
        "evidence": evidence,
    }


def _pipeline_nodes_by_name(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    nodes: dict[str, dict[str, Any]] = payload["nodes"]
    pipeline_nodes: dict[str, dict[str, Any]] = {}
    for node in nodes.values():
        if node.get("node_type") not in PIPELINE_NODE_TYPES:
            continue
        label = node.get("label")
        node_id = str(node.get("id") or "")
        name = str(label or node_id.split(":", 1)[-1])
        if name:
            pipeline_nodes[name] = node
    return pipeline_nodes


def _pipeline_doc_paths(source_node: dict[str, Any], repo_root: Path) -> list[str]:
    label = str(source_node.get("label") or "")
    meta = source_node.get("meta") if isinstance(source_node.get("meta"), dict) else {}
    provider = str(meta.get("provider") or "")
    entity = str(meta.get("entity") or "")
    if not entity and label.startswith("composite_"):
        provider = "composite"
        entity = label.removeprefix("composite_")
    if not provider or not entity:
        return []

    entity_dash = entity.replace("_", "-")
    candidates = [
        *(
            path.relative_to(repo_root).as_posix()
            for path in (
                repo_root / "docs" / "04-reference" / "pipelines" / provider
            ).glob(f"*-{entity_dash}-spec.md")
        ),
        f"docs/04-reference/providers/{provider}/{entity_dash}.md",
        f"docs/04-reference/pipelines/{provider}-{entity_dash}.md",
    ]
    return sorted(
        {candidate for candidate in candidates if (repo_root / candidate).is_file()}
    )


def _explicit_path_refs(text: str) -> set[str]:
    refs: set[str] = set()
    for line in text.splitlines():
        for prefix in _PATH_REF_PREFIXES:
            refs.update(_extract_path_refs_for_prefix(line, prefix))
    return refs


def _extract_path_refs_for_prefix(line: str, prefix: str) -> set[str]:
    refs: set[str] = set()
    start = 0
    while True:
        index = line.find(prefix, start)
        if index == -1:
            break
        if index > 0 and (line[index - 1].isalnum() or line[index - 1] in "_/"):
            start = index + 1
            continue
        candidate = _collect_path_ref_candidate(line, index, prefix)
        if candidate:
            refs.add(candidate)
        start = index + 1
    return refs


def _collect_path_ref_candidate(line: str, start_index: int, prefix: str) -> str:
    end = start_index + len(prefix)
    while end < len(line) and line[end] in _PATH_REF_CHARS:
        end += 1
    return line[start_index:end].rstrip(".,);]")


def _explicit_config_path_refs(text: str) -> set[str]:
    return {
        path
        for path in _explicit_path_refs(text)
        if path.startswith(CONFIGS_DIR_PREFIX)
        and Path(path).suffix in {".yaml", ".yml", ".json"}
    }


def _path_entity_id(path: str) -> str:
    return f"{_path_entity_kind(path).lower()}:{path}"


def _path_entity_kind(path: str) -> str:
    if path.startswith("src/"):
        return "File"
    if path.startswith(CONFIGS_DIR_PREFIX):
        return "Config"
    if path.startswith("tests/"):
        return "Test"
    if path.startswith("docs/"):
        return "Doc"
    return "Path"


def _is_adr_path(path: Path, repo_root: Path) -> bool:
    try:
        relative = path.relative_to(repo_root).as_posix()
    except ValueError:
        return False
    return relative.startswith("docs/02-architecture/decisions/ADR-")


def _adr_number(path: Path) -> str | None:
    match = ADR_REF_PATTERN.search(path.name)
    return match.group(1) if match else None


def _extract_adr_lifecycle_field(line: str) -> str | None:
    line_stripped = line.lstrip(" *_`#>-")
    lower_line = line_stripped.lower()
    for keyword in ADR_LIFECYCLE_FIELDS:
        if lower_line.startswith(keyword):
            remainder = lower_line[len(keyword) :].lstrip()
            if remainder.lstrip(" *_`#>-").startswith(":"):
                return keyword
    return None


def _iter_adr_lifecycle_refs(text: str) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    for line in text.splitlines():
        field = _extract_adr_lifecycle_field(line)
        if field is None:
            continue
        for target_match in ADR_REF_PATTERN.finditer(line):
            refs.append((field, target_match.group(1)))
    return refs


def _markdown_title(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped.removeprefix("# ").strip()
    return ""


def _failure_mode_name(title: str, fallback_stem: str) -> str:
    cleaned = title.strip()
    if cleaned.lower().endswith(" runbook"):
        cleaned = cleaned[:-8].strip()
    if cleaned.endswith(")"):
        start_paren = cleaned.rfind("(")
        if start_paren != -1:
            cleaned = cleaned[:start_paren].strip()
    return cleaned or fallback_stem.replace("-", " ")


def _slugify(value: str) -> str:
    slug_parts: list[str] = []
    previous_was_dash = False
    for char in value.lower():
        if char.isalnum():
            slug_parts.append(char)
            previous_was_dash = False
            continue
        if not previous_was_dash:
            slug_parts.append("-")
            previous_was_dash = True
    slug = "".join(slug_parts).strip("-")
    return slug or "unknown"


def _dedupe_entity_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for record in records:
        unique.setdefault(record["id"], record)
    return sorted(
        unique.values(),
        key=lambda item: (
            item["source_id"],
            item["relation"],
            item["target_id"],
        ),
    )


def build_file_relation_index(
    records: list[dict[str, Any]],
    *,
    source_snapshot: str,
) -> dict[str, Any]:
    """Build a compact lookup index for file-level relation queries."""
    by_file: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: {"outbound": [], "inbound": []}
    )
    for record in records:
        outbound = _compact_relation(record, "outbound")
        inbound = _compact_relation(record, "inbound")
        by_file[record["source_path"]]["outbound"].append(outbound)
        by_file[record["target_path"]]["inbound"].append(inbound)

    normalized_by_file = {
        path: {
            "outbound": sorted(
                relations["outbound"], key=lambda item: item["target_path"]
            ),
            "inbound": sorted(
                relations["inbound"], key=lambda item: item["source_path"]
            ),
        }
        for path, relations in sorted(by_file.items())
    }
    return {
        "generator_version": GENERATOR_VERSION,
        "kind": "file_relation_index",
        "relation": "references_file",
        "source_snapshot": source_snapshot,
        "relation_count": len(records),
        "file_count": len(normalized_by_file),
        "by_file": normalized_by_file,
    }


def build_module_relation_index(
    records: list[dict[str, Any]],
    *,
    source_snapshot: str,
) -> dict[str, Any]:
    """Build a compact lookup index for module-level relation queries."""
    by_module: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: {"outbound": [], "inbound": []}
    )
    for record in records:
        outbound = _compact_module_relation(record, "outbound")
        inbound = _compact_module_relation(record, "inbound")
        by_module[record["source_name"]]["outbound"].append(outbound)
        by_module[record["target_name"]]["inbound"].append(inbound)

    normalized_by_module = {
        module_name: {
            "outbound": sorted(
                relations["outbound"], key=lambda item: item["target_name"]
            ),
            "inbound": sorted(
                relations["inbound"], key=lambda item: item["source_name"]
            ),
        }
        for module_name, relations in sorted(by_module.items())
    }
    return {
        "generator_version": GENERATOR_VERSION,
        "kind": "module_relation_index",
        "relation": "references",
        "source_snapshot": source_snapshot,
        "relation_count": len(records),
        "module_count": len(normalized_by_module),
        "by_module": normalized_by_module,
    }


def build_entity_relation_index(
    records: list[dict[str, Any]],
    *,
    source_snapshot: str,
) -> dict[str, Any]:
    """Build a compact lookup index for generic entity relation queries."""
    by_entity: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"name": "", "kind": "", "path": "", "outbound": [], "inbound": []}
    )
    for record in records:
        outbound = _compact_entity_relation(record, "outbound")
        inbound = _compact_entity_relation(record, "inbound")
        source_entry = by_entity[record["source_id"]]
        source_entry["name"] = record["source_name"]
        source_entry["kind"] = record["source_kind"]
        source_entry["path"] = record["source_path"]
        source_entry["outbound"].append(outbound)
        target_entry = by_entity[record["target_id"]]
        target_entry["name"] = record["target_name"]
        target_entry["kind"] = record["target_kind"]
        target_entry["path"] = record["target_path"]
        target_entry["inbound"].append(inbound)

    normalized_by_entity = {
        entity_id: {
            "name": entry["name"],
            "kind": entry["kind"],
            "path": entry["path"],
            "outbound": sorted(
                entry["outbound"],
                key=lambda item: (item["relation"], item["target_id"]),
            ),
            "inbound": sorted(
                entry["inbound"],
                key=lambda item: (item["relation"], item["source_id"]),
            ),
        }
        for entity_id, entry in sorted(by_entity.items())
    }
    relation_counts = Counter(record["relation"] for record in records)
    return {
        "generator_version": GENERATOR_VERSION,
        "kind": "entity_relation_index",
        "source_snapshot": source_snapshot,
        "relation_count": len(records),
        "entity_count": len(normalized_by_entity),
        "relation_counts": dict(sorted(relation_counts.items())),
        "by_entity": normalized_by_entity,
    }


def _compact_relation(record: dict[str, Any], direction: str) -> dict[str, Any]:
    return {
        "id": record["id"],
        "direction": direction,
        "relation": record["relation"],
        "source_path": record["source_path"],
        "target_path": record["target_path"],
        "confidence": record["confidence"],
        "provenance": record["provenance"],
        "source_generated_at": record["source_generated_at"],
        "evidence": record.get("evidence") or {},
    }


def _compact_module_relation(record: dict[str, Any], direction: str) -> dict[str, Any]:
    return {
        "id": record["id"],
        "direction": direction,
        "relation": record["relation"],
        "source_name": record["source_name"],
        "source_path": record["source_path"],
        "target_name": record["target_name"],
        "target_path": record["target_path"],
        "confidence": record["confidence"],
        "provenance": record["provenance"],
        "source_generated_at": record["source_generated_at"],
        "evidence": record.get("evidence") or {},
    }


def _compact_entity_relation(record: dict[str, Any], direction: str) -> dict[str, Any]:
    return {
        "id": record["id"],
        "direction": direction,
        "relation": record["relation"],
        "source_id": record["source_id"],
        "source_name": record["source_name"],
        "source_kind": record["source_kind"],
        "source_path": record["source_path"],
        "target_id": record["target_id"],
        "target_name": record["target_name"],
        "target_kind": record["target_kind"],
        "target_path": record["target_path"],
        "confidence": record["confidence"],
        "provenance": record["provenance"],
        "source_generated_at": record["source_generated_at"],
        "evidence": record.get("evidence") or {},
    }


def write_expanded_graph_relation_artifacts(
    snapshot_path: Path,
    output_root: Path,
    *,
    repo_root: Path | None = None,
) -> tuple[Path, Path, dict[str, Any]]:
    """Write file-reference projection JSONL and lookup index JSON."""
    payload = load_expanded_graph(snapshot_path)
    projection_dir = output_root / "graph" / "projections"
    index_dir = output_root / "graph" / "indexes"
    projection_dir.mkdir(parents=True, exist_ok=True)
    index_dir.mkdir(parents=True, exist_ok=True)

    records = iter_file_reference_records(
        payload,
        source_snapshot=str(snapshot_path),
    )
    module_records = iter_module_reference_records(
        payload,
        source_snapshot=str(snapshot_path),
    )
    entity_records = iter_entity_relation_records(
        payload,
        source_snapshot=str(snapshot_path),
        repo_root=repo_root,
    )
    projection_path = projection_dir / "file_references.jsonl"
    index_path = index_dir / "file_relations.json"
    module_projection_path = projection_dir / "module_references.jsonl"
    module_index_path = index_dir / "module_relations.json"
    entity_projection_path = projection_dir / "entity_relations.jsonl"
    entity_index_path = index_dir / "entity_relations.json"
    _write_jsonl(projection_path, records)
    _write_jsonl(module_projection_path, module_records)
    _write_jsonl(entity_projection_path, entity_records)
    index = build_file_relation_index(records, source_snapshot=str(snapshot_path))
    module_index = build_module_relation_index(
        module_records,
        source_snapshot=str(snapshot_path),
    )
    entity_index = build_entity_relation_index(
        entity_records,
        source_snapshot=str(snapshot_path),
    )
    index_path.write_text(
        json.dumps(index, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    module_index_path.write_text(
        json.dumps(module_index, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    entity_index_path.write_text(
        json.dumps(entity_index, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "ok": True,
        "kind": "graph_relations",
        "source_snapshot": str(snapshot_path),
        "projection_path": str(projection_path),
        "index_path": str(index_path),
        "module_projection_path": str(module_projection_path),
        "module_index_path": str(module_index_path),
        "entity_projection_path": str(entity_projection_path),
        "entity_index_path": str(entity_index_path),
        "paths": [
            str(projection_path),
            str(index_path),
            str(module_projection_path),
            str(module_index_path),
            str(entity_projection_path),
            str(entity_index_path),
        ],
        "relation_count": len(records),
        "file_count": index["file_count"],
        "module_relation_count": len(module_records),
        "module_count": module_index["module_count"],
        "entity_relation_count": len(entity_records),
        "entity_count": entity_index["entity_count"],
        "entity_relation_counts": entity_index["relation_counts"],
    }
    return projection_path, index_path, summary


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=True))
            handle.write("\n")


def load_file_relation_index(path: Path) -> dict[str, Any]:
    """Load a generated file relation lookup index."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("kind") != "file_relation_index":
        raise ValueError(f"invalid file relation index: {path}")
    return payload


def load_module_relation_index(path: Path) -> dict[str, Any]:
    """Load a generated module relation lookup index."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("kind") != "module_relation_index":
        raise ValueError(f"invalid module relation index: {path}")
    return payload


def load_entity_relation_index(path: Path) -> dict[str, Any]:
    """Load a generated generic entity relation lookup index."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("kind") != "entity_relation_index":
        raise ValueError(f"invalid entity relation index: {path}")
    return payload


def query_file_relations(
    index: dict[str, Any],
    source_path: str,
    *,
    direction: str = "both",
    limit: int = 20,
) -> dict[str, Any]:
    """Return direct inbound/outbound file relation records for one file."""
    resolved_path = resolve_index_file_path(index, source_path)
    if resolved_path is None:
        return _empty_relation_payload(index, source_path)
    entry = index["by_file"][resolved_path]
    outbound = entry.get("outbound", []) if direction in {"both", "outbound"} else []
    inbound = entry.get("inbound", []) if direction in {"both", "inbound"} else []
    return {
        "kind": "file_refs",
        "query": source_path,
        "resolved_path": resolved_path,
        "relation": index.get("relation"),
        "source_snapshot": index.get("source_snapshot"),
        "outbound": list(outbound)[:limit],
        "inbound": list(inbound)[:limit],
        "count": min(len(outbound), limit) + min(len(inbound), limit),
        "ok": True,
    }


def query_module_relations(
    index: dict[str, Any],
    module_name: str,
    *,
    direction: str = "both",
    limit: int = 20,
) -> dict[str, Any]:
    """Return direct inbound/outbound module relation records for one module."""
    resolved_name = resolve_index_module_name(index, module_name)
    if resolved_name is None:
        return _empty_module_relation_payload(index, module_name)
    entry = index["by_module"][resolved_name]
    outbound = entry.get("outbound", []) if direction in {"both", "outbound"} else []
    inbound = entry.get("inbound", []) if direction in {"both", "inbound"} else []
    return {
        "kind": "module_refs",
        "query": module_name,
        "resolved_module": resolved_name,
        "relation": index.get("relation"),
        "source_snapshot": index.get("source_snapshot"),
        "outbound": list(outbound)[:limit],
        "inbound": list(inbound)[:limit],
        "count": min(len(outbound), limit) + min(len(inbound), limit),
        "ok": True,
    }


def query_entity_relations(
    index: dict[str, Any],
    entity: str,
    *,
    direction: str = "both",
    relation: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Return direct inbound/outbound generic entity relation records."""
    resolved_entity = resolve_index_entity(index, entity)
    if resolved_entity is None:
        return _empty_entity_relation_payload(index, entity)
    entry = index["by_entity"][resolved_entity]
    outbound = entry.get("outbound", []) if direction in {"both", "outbound"} else []
    inbound = entry.get("inbound", []) if direction in {"both", "inbound"} else []
    if relation is not None:
        outbound = [item for item in outbound if item.get("relation") == relation]
        inbound = [item for item in inbound if item.get("relation") == relation]
    return {
        "kind": "entity_refs",
        "query": entity,
        "resolved_entity": resolved_entity,
        "entity": {
            "name": entry.get("name"),
            "kind": entry.get("kind"),
            "path": entry.get("path"),
        },
        "relation": relation,
        "source_snapshot": index.get("source_snapshot"),
        "outbound": list(outbound)[:limit],
        "inbound": list(inbound)[:limit],
        "count": min(len(outbound), limit) + min(len(inbound), limit),
        "ok": True,
    }


def _empty_relation_payload(index: dict[str, Any], source_path: str) -> dict[str, Any]:
    return {
        "kind": "file_refs",
        "query": source_path,
        "resolved_path": None,
        "relation": index.get("relation"),
        "source_snapshot": index.get("source_snapshot"),
        "outbound": [],
        "inbound": [],
        "count": 0,
        "ok": True,
    }


def _empty_module_relation_payload(
    index: dict[str, Any], module_name: str
) -> dict[str, Any]:
    return {
        "kind": "module_refs",
        "query": module_name,
        "resolved_module": None,
        "relation": index.get("relation"),
        "source_snapshot": index.get("source_snapshot"),
        "outbound": [],
        "inbound": [],
        "count": 0,
        "ok": True,
    }


def _empty_entity_relation_payload(
    index: dict[str, Any], entity: str
) -> dict[str, Any]:
    return {
        "kind": "entity_refs",
        "query": entity,
        "resolved_entity": None,
        "entity": None,
        "relation": None,
        "source_snapshot": index.get("source_snapshot"),
        "outbound": [],
        "inbound": [],
        "count": 0,
        "ok": True,
    }


def _empty_neighborhood_payload(
    *,
    kind: str,
    query: str,
    resolved_key: str,
    depth: int,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "query": query,
        resolved_key: None,
        "depth": depth,
        "nodes": [],
        "edges": [],
        "count": 0,
        "ok": True,
    }


def _bounded_relation_neighborhood(
    *,
    entries: dict[str, dict[str, Any]],
    start: str,
    depth: int,
    limit: int,
    relations_for_entry: Callable[[dict[str, Any]], list[dict[str, Any]]],
    neighbor_for_relation: Callable[[dict[str, Any], str], str],
) -> tuple[list[str], list[dict[str, Any]]]:
    visited = {start}
    seen_edge_ids: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(start, 0)])
    edges: list[dict[str, Any]] = []

    while queue and len(edges) < limit:
        current, current_depth = queue.popleft()
        if current_depth >= depth:
            continue
        _append_bounded_relations(
            current=current,
            current_depth=current_depth,
            entries=entries,
            relations_for_entry=relations_for_entry,
            neighbor_for_relation=neighbor_for_relation,
            seen_edge_ids=seen_edge_ids,
            visited=visited,
            queue=queue,
            edges=edges,
            limit=limit,
        )

    return sorted(visited), edges


def _pipeline_artifact_relation_record(
    *,
    edge_id: object,
    edge: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    source_snapshot: str,
    snapshot_generated_at: str,
) -> dict[str, Any] | None:
    if edge.get("edge_type") != "writes_to":
        return None
    source_id = str(edge.get("source") or "")
    target_id = str(edge.get("target") or "")
    source_node = nodes.get(source_id) or {}
    if str(source_node.get("node_type") or "") not in PIPELINE_NODE_TYPES:
        return None
    target_node = nodes.get(target_id) or {}
    source_ref = _entity_ref(source_node, source_id)
    target_ref = _entity_ref(target_node, target_id)
    target_entity_id = (
        target_ref if target_ref.startswith("artifact:") else f"artifact:{target_ref}"
    )
    return {
        "id": f"{source_ref}|emits_artifact|{target_entity_id}",
        "source_id": source_ref,
        "source_name": _node_display_name(source_node, source_id),
        "source_kind": str(source_node.get("node_type") or "Unknown"),
        "source_path": _node_source_path(source_node),
        "target_id": target_entity_id,
        "target_name": _node_display_name(target_node, target_id),
        "target_kind": "Artifact",
        "target_path": _node_source_path(target_node),
        "relation": "emits_artifact",
        "confidence": "derived",
        "provenance": "bioetl_knowledge_graph_expanded.writes_to",
        "source_snapshot": source_snapshot,
        "source_generated_at": snapshot_generated_at,
        "edge_id": str(edge_id),
        "description": str(edge.get("description") or ""),
        "evidence": edge.get("meta") if isinstance(edge.get("meta"), dict) else {},
    }


def _adr_paths_by_number(decisions_dir: Path) -> dict[int, Path]:
    return {
        adr_number: path
        for path in sorted(decisions_dir.glob(ADR_DOC_GLOB))
        if (adr_number := _adr_number(path)) is not None
    }


def _adr_lifecycle_relation_record(
    *,
    adr_path: Path,
    adr_paths: dict[int, Path],
    declaring_path: str,
    field: str,
    target_number: int,
    repo_root: Path,
    source_snapshot: str,
) -> dict[str, Any] | None:
    target_path = adr_paths.get(target_number)
    if target_path is None:
        return None
    relation = "amends" if "amend" in field else "supersedes"
    if field in {"superseded by", "amended by"}:
        source_path = target_path
        target_relative_path = declaring_path
    else:
        source_path = adr_path
        target_relative_path = target_path.relative_to(repo_root).as_posix()
    source_relative = source_path.relative_to(repo_root).as_posix()
    return _path_relation_record(
        source_path=source_relative,
        source_kind="ADR",
        source_id=f"adr:{source_relative}",
        source_name=source_path.stem,
        target_path=target_relative_path,
        target_kind="ADR",
        target_id=f"adr:{target_relative_path}",
        target_name=Path(target_relative_path).stem,
        relation=relation,
        confidence="derived",
        provenance="docs/02-architecture/decisions.lifecycle_metadata",
        source_snapshot=source_snapshot,
        evidence={
            "declaring_adr_path": declaring_path,
            "field": field,
        },
    )


def _append_bounded_relations(
    *,
    current: str,
    current_depth: int,
    entries: dict[str, dict[str, Any]],
    relations_for_entry: Callable[[dict[str, Any]], list[dict[str, Any]]],
    neighbor_for_relation: Callable[[dict[str, Any], str], str],
    seen_edge_ids: set[str],
    visited: set[str],
    queue: deque[tuple[str, int]],
    edges: list[dict[str, Any]],
    limit: int,
) -> None:
    for relation in relations_for_entry(entries.get(current, {})):
        relation_id = str(relation.get("id") or "")
        if relation_id in seen_edge_ids:
            continue
        seen_edge_ids.add(relation_id)
        edges.append(relation)
        neighbor = neighbor_for_relation(relation, current)
        if neighbor not in visited:
            visited.add(neighbor)
            queue.append((neighbor, current_depth + 1))
        if len(edges) >= limit:
            return


def query_file_neighborhood(
    index: dict[str, Any],
    source_path: str,
    *,
    depth: int = 1,
    limit: int = 50,
) -> dict[str, Any]:
    """Return a bounded BFS neighborhood over file-reference relations."""
    resolved_path = resolve_index_file_path(index, source_path)
    if resolved_path is None:
        return _empty_neighborhood_payload(
            kind="file_neighborhood",
            query=source_path,
            resolved_key="resolved_path",
            depth=depth,
        )
    nodes, edges = _bounded_relation_neighborhood(
        entries=index["by_file"],
        start=resolved_path,
        depth=depth,
        limit=limit,
        relations_for_entry=_relations_for_entry,
        neighbor_for_relation=_file_relation_neighbor,
    )

    return {
        "kind": "file_neighborhood",
        "query": source_path,
        "resolved_path": resolved_path,
        "depth": depth,
        "source_snapshot": index.get("source_snapshot"),
        "nodes": nodes,
        "edges": edges,
        "count": len(edges),
        "ok": True,
    }


def query_module_neighborhood(
    index: dict[str, Any],
    module_name: str,
    *,
    depth: int = 1,
    limit: int = 50,
) -> dict[str, Any]:
    """Return a bounded BFS neighborhood over module-reference relations."""
    resolved_name = resolve_index_module_name(index, module_name)
    if resolved_name is None:
        return _empty_neighborhood_payload(
            kind="module_neighborhood",
            query=module_name,
            resolved_key="resolved_module",
            depth=depth,
        )
    nodes, edges = _bounded_relation_neighborhood(
        entries=index["by_module"],
        start=resolved_name,
        depth=depth,
        limit=limit,
        relations_for_entry=_module_relations_for_entry,
        neighbor_for_relation=_module_relation_neighbor,
    )

    return {
        "kind": "module_neighborhood",
        "query": module_name,
        "resolved_module": resolved_name,
        "depth": depth,
        "source_snapshot": index.get("source_snapshot"),
        "nodes": nodes,
        "edges": edges,
        "count": len(edges),
        "ok": True,
    }


def query_entity_neighborhood(
    index: dict[str, Any],
    entity: str,
    *,
    depth: int = 1,
    limit: int = 50,
) -> dict[str, Any]:
    """Return a bounded BFS neighborhood over generic entity relations."""
    resolved_entity = resolve_index_entity(index, entity)
    if resolved_entity is None:
        return _empty_neighborhood_payload(
            kind="entity_neighborhood",
            query=entity,
            resolved_key="resolved_entity",
            depth=depth,
        )
    nodes, edges = _bounded_relation_neighborhood(
        entries=index["by_entity"],
        start=resolved_entity,
        depth=depth,
        limit=limit,
        relations_for_entry=_entity_relations_for_entry,
        neighbor_for_relation=_entity_relation_neighbor,
    )

    return {
        "kind": "entity_neighborhood",
        "query": entity,
        "resolved_entity": resolved_entity,
        "depth": depth,
        "source_snapshot": index.get("source_snapshot"),
        "nodes": nodes,
        "edges": edges,
        "count": len(edges),
        "ok": True,
    }


def _file_relation_neighbor(relation: dict[str, Any], current: str) -> str:
    return (
        relation["target_path"]
        if relation["source_path"] == current
        else relation["source_path"]
    )


def _module_relation_neighbor(relation: dict[str, Any], current: str) -> str:
    return (
        relation["target_name"]
        if relation["source_name"] == current
        else relation["source_name"]
    )


def _entity_relation_neighbor(relation: dict[str, Any], current: str) -> str:
    return (
        relation["target_id"]
        if relation["source_id"] == current
        else relation["source_id"]
    )


def _relations_for_entry(entry: dict[str, Any]) -> list[dict[str, Any]]:
    relations = [*entry.get("outbound", []), *entry.get("inbound", [])]
    return sorted(
        relations,
        key=lambda item: (
            item.get("source_path", ""),
            item.get("target_path", ""),
            item.get("direction", ""),
        ),
    )


def _module_relations_for_entry(entry: dict[str, Any]) -> list[dict[str, Any]]:
    relations = [*entry.get("outbound", []), *entry.get("inbound", [])]
    return sorted(
        relations,
        key=lambda item: (
            item.get("source_name", ""),
            item.get("target_name", ""),
            item.get("direction", ""),
        ),
    )


def _entity_relations_for_entry(entry: dict[str, Any]) -> list[dict[str, Any]]:
    relations = [*entry.get("outbound", []), *entry.get("inbound", [])]
    return sorted(
        relations,
        key=lambda item: (
            item.get("source_id", ""),
            item.get("relation", ""),
            item.get("target_id", ""),
            item.get("direction", ""),
        ),
    )


def resolve_index_file_path(index: dict[str, Any], query: str) -> str | None:
    """Resolve exact, normalized, or unique suffix file query to index path."""
    normalized_query = query.replace("\\", "/").lstrip("./")
    by_file = index.get("by_file", {})
    if normalized_query in by_file:
        return normalized_query
    suffix_matches = [
        path
        for path in by_file
        if path.endswith(f"/{normalized_query}") or path.endswith(normalized_query)
    ]
    if len(suffix_matches) == 1:
        return suffix_matches[0]
    return None


def resolve_index_module_name(index: dict[str, Any], query: str) -> str | None:
    """Resolve exact or unique suffix module query to index module name."""
    normalized_query = query.removeprefix("mod:")
    by_module = index.get("by_module", {})
    if normalized_query in by_module:
        return normalized_query
    suffix_matches = [
        module_name
        for module_name in by_module
        if module_name.endswith(f".{normalized_query}")
        or module_name.endswith(normalized_query)
    ]
    if len(suffix_matches) == 1:
        return suffix_matches[0]
    return None


def resolve_index_entity(index: dict[str, Any], query: str) -> str | None:
    """Resolve exact, path, name, or unique suffix entity query to index entity id."""
    normalized_query = query.replace("\\", "/").lstrip("./")
    by_entity = index.get("by_entity", {})
    if normalized_query in by_entity:
        return normalized_query
    matches = []
    for entity_id, entry in by_entity.items():
        name = str(entry.get("name") or "")
        path = str(entry.get("path") or "")
        if normalized_query in {name, path}:
            matches.append(entity_id)
            continue
        if entity_id.endswith(normalized_query) or path.endswith(normalized_query):
            matches.append(entity_id)
    if len(matches) == 1:
        return matches[0]
    return None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import file/module relations from an expanded BioETL graph JSON."
    )
    parser.add_argument(
        "--snapshot-path",
        type=Path,
        required=True,
        help="Path to the expanded knowledge-graph snapshot JSON.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=MEMORY_ROOT,
        help="Memory root or temporary output root for generated relation artifacts.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root used for derived docs/tests/ADR relation imports.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON summary.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    _, _, summary = write_expanded_graph_relation_artifacts(
        args.snapshot_path.resolve(),
        args.output_root.resolve(),
        repo_root=args.repo_root.resolve() if args.repo_root else None,
    )
    if args.json:
        sys.stdout.write(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(
            "Imported graph relation artifacts: "
            f"{summary['relation_count']} file relations across "
            f"{summary['file_count']} files; "
            f"{summary['module_relation_count']} module relations across "
            f"{summary['module_count']} modules; "
            f"{summary['entity_relation_count']} entity relations across "
            f"{summary['entity_count']} entities"
            "\n"
        )
        sys.stdout.write(f"- file projection: {summary['projection_path']}\n")
        sys.stdout.write(f"- file index: {summary['index_path']}\n")
        sys.stdout.write(f"- module projection: {summary['module_projection_path']}\n")
        sys.stdout.write(f"- module index: {summary['module_index_path']}\n")
        sys.stdout.write(f"- entity projection: {summary['entity_projection_path']}\n")
        sys.stdout.write(f"- entity index: {summary['entity_index_path']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
