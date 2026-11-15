"""Family graph and direct-layer class for one target.

Paths are structured root to leaf. The old leaf-to-root text is only a
migration field. A graph defect does not yield a class from a cut path.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .models import Diagnostic
from .policy import (
    GRAPH_MAX_DEPTH,
    GRAPH_MAX_VISITED_NODES,
    assign_mapped_class,
)

_LIMIT = "превышение лимита"
_CYCLE = "цикл"
_SELF_LOOP = "self-loop"
_MISSING_PARENT = "отсутствующий родитель"
_DUPLICATE = "повторяющийся идентификатор"
_MISSING_FAMILY = "отсутствующая семья"
_MULTI_PARENT = "множественные родители"


@dataclass(frozen=True, slots=True)
class FamilyNode:
    """One family record. ``payload`` distinguishes repeated identifiers."""

    family_id: str
    parent_ids: tuple[str, ...]
    payload: str


@dataclass(frozen=True, slots=True)
class FamilyPath:
    """One ancestor path. ``leaf_to_root`` is not used to choose a class."""

    family_id: str
    root_to_leaf: tuple[str, ...]
    leaf_to_root: str


@dataclass(frozen=True, slots=True)
class HierarchyResult:
    """Direct-layer outcome for one target."""

    annotation_status: str
    iuphar_class: str | None
    iuphar_subclass: str | None
    iuphar_class_candidates: tuple[str, ...]
    proof: str | None
    source: str | None
    paths: tuple[FamilyPath, ...]
    family_evidence: tuple[tuple[str, str], ...]
    diagnostics: tuple[Diagnostic, ...]


def validate_family_graph(
    nodes: tuple[FamilyNode, ...],
    family_ids: tuple[str, ...],
    *,
    max_depth: int,
    max_visited_nodes: int,
    multiple_parents_allowed: bool = True,
) -> Diagnostic | None:
    """Return the first graph defect, or ``None`` when the walk is intact."""
    indexed = _index_nodes(nodes)
    if isinstance(indexed, Diagnostic):
        return indexed
    return _walk_ancestors(
        indexed,
        family_ids,
        max_depth=max_depth,
        max_visited_nodes=max_visited_nodes,
        multiple_parents_allowed=multiple_parents_allowed,
    )


def build_family_paths(
    nodes: tuple[FamilyNode, ...],
    family_ids: tuple[str, ...],
) -> tuple[FamilyPath, ...]:
    """Build root-to-leaf paths. The caller validates the graph first."""
    indexed = _index_nodes(nodes)
    if isinstance(indexed, Diagnostic):
        return ()
    paths: list[FamilyPath] = []
    for family_id in sorted(family_ids):
        paths.extend(_paths_from(indexed, family_id))
    return tuple(sorted(paths, key=lambda item: (item.family_id, item.root_to_leaf)))


def normalize_provider_class(
    *,
    type_name: str | None,
    family_ids: tuple[str, ...],
    nodes: tuple[FamilyNode, ...],
    type_to_class: Mapping[str, str],
    family_to_class: Mapping[str, str],
    name: str | None = None,
    path_text: str | None = None,
    max_depth: int = GRAPH_MAX_DEPTH,
    max_visited_nodes: int = GRAPH_MAX_VISITED_NODES,
    multiple_parents_allowed: bool = True,
) -> HierarchyResult:
    """Map a provider type or family only after the ancestor walk succeeds."""
    defect = validate_family_graph(
        nodes,
        family_ids,
        max_depth=max_depth,
        max_visited_nodes=max_visited_nodes,
        multiple_parents_allowed=multiple_parents_allowed,
    )
    if defect is not None:
        return _graph_error_result(
            defect,
            type_name=type_name,
            type_to_class=type_to_class,
            name=name,
            path_text=path_text,
        )
    assigned = assign_mapped_class(
        type_name=type_name,
        family_ids=family_ids,
        type_to_class=type_to_class,
        family_to_class=family_to_class,
        name=name,
        path_text=path_text,
    )
    proof = assigned.proof
    if proof == "family_mapping":
        proof = "отображение семейства"
    evidence = tuple(
        (family_id, family_to_class[family_id])
        for family_id in sorted(family_ids)
        if family_id in family_to_class
    )
    source = "iuphar_normalized" if assigned.iuphar_class else None
    return HierarchyResult(
        annotation_status=assigned.status,
        iuphar_class=assigned.iuphar_class,
        iuphar_subclass=None,
        iuphar_class_candidates=assigned.candidates,
        proof=proof,
        source=source,
        paths=build_family_paths(nodes, family_ids),
        family_evidence=evidence,
        diagnostics=(),
    )


def _graph_error_result(
    defect: Diagnostic,
    *,
    type_name: str | None,
    type_to_class: Mapping[str, str],
    name: str | None,
    path_text: str | None,
) -> HierarchyResult:
    """Keep a type class. A family class from a cut path is discarded."""
    typed = assign_mapped_class(
        type_name=type_name,
        family_ids=(),
        type_to_class=type_to_class,
        family_to_class={},
        name=name,
        path_text=path_text,
    )
    mapped = typed.iuphar_class if typed.status == "available" else None
    return HierarchyResult(
        annotation_status="partial" if type_name else "not_available",
        iuphar_class=mapped,
        iuphar_subclass=None,
        iuphar_class_candidates=(mapped,) if mapped else (),
        proof="type" if mapped else None,
        source="iuphar_normalized" if mapped else None,
        paths=(),
        family_evidence=(),
        diagnostics=(defect,),
    )


def _index_nodes(
    nodes: tuple[FamilyNode, ...],
) -> dict[str, FamilyNode] | Diagnostic:
    grouped: dict[str, list[FamilyNode]] = {}
    for node in nodes:
        grouped.setdefault(node.family_id, []).append(node)
    indexed: dict[str, FamilyNode] = {}
    for family_id in sorted(grouped):
        payloads = {item.payload for item in grouped[family_id]}
        if len(payloads) > 1:
            return _defect(_DUPLICATE)
        parents = tuple(sorted(set(grouped[family_id][0].parent_ids)))
        payload = grouped[family_id][0].payload
        indexed[family_id] = FamilyNode(family_id, parents, payload)
    return indexed


def _walk_ancestors(
    nodes: dict[str, FamilyNode],
    family_ids: tuple[str, ...],
    *,
    max_depth: int,
    max_visited_nodes: int,
    multiple_parents_allowed: bool,
) -> Diagnostic | None:
    seen: set[str] = set()
    for family_id in sorted(family_ids):
        if family_id not in nodes:
            return _defect(_MISSING_FAMILY)
        defect = _walk_one(
            nodes,
            family_id,
            max_depth=max_depth,
            max_visited_nodes=max_visited_nodes,
            seen=seen,
            multiple_parents_allowed=multiple_parents_allowed,
        )
        if defect is not None:
            return defect
    return None


def _walk_one(
    nodes: dict[str, FamilyNode],
    start: str,
    *,
    max_depth: int,
    max_visited_nodes: int,
    seen: set[str],
    multiple_parents_allowed: bool,
) -> Diagnostic | None:
    frames: list[list[int | str]] = [[start, 0, 0]]
    in_path: set[str] = set()
    while frames:
        frame = frames[-1]
        node_id = str(frame[0])
        depth = int(frame[1])
        cursor = int(frame[2])
        node = nodes[node_id]
        if cursor == 0 and node_id not in in_path:
            defect = _enter_node(
                node,
                depth=depth,
                seen=seen,
                max_depth=max_depth,
                max_visited_nodes=max_visited_nodes,
                multiple_parents_allowed=multiple_parents_allowed,
                nodes=nodes,
            )
            if defect is not None:
                return defect
            in_path.add(node_id)
        if cursor < len(node.parent_ids):
            parent_id = node.parent_ids[cursor]
            frame[2] = cursor + 1
            if parent_id in in_path:
                return _defect(_CYCLE)
            frames.append([parent_id, depth + 1, 0])
            continue
        in_path.remove(node_id)
        frames.pop()
    return None


def _enter_node(
    node: FamilyNode,
    *,
    depth: int,
    seen: set[str],
    max_depth: int,
    max_visited_nodes: int,
    multiple_parents_allowed: bool,
    nodes: dict[str, FamilyNode],
) -> Diagnostic | None:
    if depth > max_depth or (
        node.family_id not in seen and len(seen) >= max_visited_nodes
    ):
        return _defect(_LIMIT)
    seen.add(node.family_id)
    if not multiple_parents_allowed and len(node.parent_ids) > 1:
        return _defect(_MULTI_PARENT)
    for parent_id in node.parent_ids:
        if parent_id == node.family_id:
            return _defect(_SELF_LOOP)
        if parent_id not in nodes:
            return _defect(_MISSING_PARENT)
    return None


def _paths_from(nodes: dict[str, FamilyNode], start: str) -> tuple[FamilyPath, ...]:
    if start not in nodes:
        return ()
    frames: list[tuple[str, tuple[str, ...]]] = [(start, (start,))]
    paths: list[FamilyPath] = []
    while frames:
        node_id, leaf_to_root_ids = frames.pop()
        parents = nodes[node_id].parent_ids
        if not parents:
            paths.append(
                FamilyPath(
                    family_id=start,
                    root_to_leaf=tuple(reversed(leaf_to_root_ids)),
                    leaf_to_root=" → ".join(leaf_to_root_ids),
                ),
            )
            continue
        for parent_id in reversed(parents):
            frames.append((parent_id, (*leaf_to_root_ids, parent_id)))
    return tuple(paths)


def _defect(message: str) -> Diagnostic:
    return Diagnostic(code="graph_error", level="error", message=message)
