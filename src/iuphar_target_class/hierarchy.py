"""Family graph and direct-layer class for one target.

Paths are structured root to leaf. The old leaf-to-root text is only a
migration field. A graph defect does not yield a class from a cut path.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache

from .gtopdb_2026_3_1 import (
    ANNOTATION_CAPABILITY,
    EXPLICIT_TYPE_SUBCLASSES,
    FAMILY_ROWS,
)
from .iuphar_mapping import approved_class_mappings
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
    iuphar_subclasses: tuple[str, ...]
    iuphar_class_candidates: tuple[str, ...]
    annotation_capability: str
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
    *,
    max_paths: int = GRAPH_MAX_VISITED_NODES,
    max_depth: int = GRAPH_MAX_DEPTH,
    max_visited_nodes: int = GRAPH_MAX_VISITED_NODES,
    multiple_parents_allowed: bool = True,
) -> tuple[FamilyPath, ...] | Diagnostic:
    """Build root-to-leaf paths after the same integrity checks as the walk."""
    defect = validate_family_graph(
        nodes,
        family_ids,
        max_depth=max_depth,
        max_visited_nodes=max_visited_nodes,
        multiple_parents_allowed=multiple_parents_allowed,
    )
    if defect is not None:
        return defect
    indexed = _index_nodes(nodes)
    if isinstance(indexed, Diagnostic):
        return indexed
    paths: list[FamilyPath] = []
    for family_id in sorted(family_ids):
        built = _paths_from(
            indexed,
            family_id,
            max_paths=max_paths,
            max_depth=max_depth,
            found=len(paths),
        )
        if isinstance(built, Diagnostic):
            return built
        paths.extend(built)
    return tuple(sorted(paths, key=lambda item: (item.family_id, item.root_to_leaf)))


@cache
def _pinned_family_graph() -> tuple[FamilyNode, ...]:
    return tuple(
        FamilyNode(str(family_id), tuple(map(str, parents)), source_type)
        for family_id, source_type, parents in FAMILY_ROWS
    )


def normalize_approved_provider_class(
    *,
    release: str,
    type_name: str | None,
    family_ids: tuple[str, ...],
) -> HierarchyResult:
    """Classify against the approved mapping and matching release graph only."""
    types, families = approved_class_mappings(release)
    return normalize_provider_class(
        type_name=type_name.strip().lower() if type_name else None,
        family_ids=family_ids,
        nodes=_pinned_family_graph(),
        type_to_class=types,
        family_to_class=families,
        type_to_subclass=dict(EXPLICIT_TYPE_SUBCLASSES),
    )


def normalize_provider_class(
    *,
    type_name: str | None,
    family_ids: tuple[str, ...],
    nodes: tuple[FamilyNode, ...],
    type_to_class: Mapping[str, str],
    family_to_class: Mapping[str, str],
    name: str | None = None,
    path_text: str | None = None,
    type_to_subclass: Mapping[str, str] | None = None,
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
    built = build_family_paths(
        nodes,
        family_ids,
        max_paths=max_visited_nodes,
        max_depth=max_depth,
        max_visited_nodes=max_visited_nodes,
        multiple_parents_allowed=multiple_parents_allowed,
    )
    if isinstance(built, Diagnostic):
        return _graph_error_result(
            built,
            type_name=type_name,
            type_to_class=type_to_class,
            name=name,
            path_text=path_text,
        )
    source = "iuphar_normalized" if assigned.iuphar_class else None
    subclasses = _subclasses(
        assigned.status,
        type_name,
        family_ids,
        nodes,
        type_to_subclass or {},
    )
    return HierarchyResult(
        annotation_status=assigned.status,
        iuphar_class=assigned.iuphar_class,
        iuphar_subclass=subclasses[0] if len(subclasses) == 1 else None,
        iuphar_subclasses=subclasses,
        iuphar_class_candidates=assigned.candidates,
        annotation_capability=ANNOTATION_CAPABILITY,
        proof=proof,
        source=source,
        paths=built,
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
        annotation_status="partial" if mapped else "not_available",
        iuphar_class=mapped,
        iuphar_subclass=None,
        iuphar_subclasses=(),
        iuphar_class_candidates=(mapped,) if mapped else (),
        annotation_capability=ANNOTATION_CAPABILITY,
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
        parents = tuple(
            sorted(
                {
                    parent
                    for item in grouped[family_id]
                    for parent in item.parent_ids
                    if parent
                }
            )
        )
        indexed[family_id] = FamilyNode(family_id, parents, next(iter(payloads)))
    return indexed


def _subclasses(
    status: str,
    type_name: str | None,
    family_ids: tuple[str, ...],
    nodes: tuple[FamilyNode, ...],
    type_to_subclass: Mapping[str, str],
) -> tuple[str, ...]:
    """Use the explicit type dictionary. Disagreement keeps every label."""
    if status in {"conflicting", "unmapped_type", "not_available"}:
        return ()
    found: set[str] = set()
    if type_name and type_name in type_to_subclass:
        found.add(type_to_subclass[type_name])
    indexed = _index_nodes(nodes)
    if isinstance(indexed, Diagnostic):
        return tuple(sorted(found))
    for family_id in family_ids:
        node = indexed.get(family_id)
        if node is not None and node.payload in type_to_subclass:
            found.add(type_to_subclass[node.payload])
    return tuple(sorted(found))


def _walk_ancestors(
    nodes: dict[str, FamilyNode],
    family_ids: tuple[str, ...],
    *,
    max_depth: int,
    max_visited_nodes: int,
    multiple_parents_allowed: bool,
) -> Diagnostic | None:
    seen: set[str] = set()
    steps = [0]
    for family_id in sorted(family_ids):
        if family_id not in nodes:
            return _defect(_MISSING_FAMILY)
        defect = _walk_one(
            nodes,
            family_id,
            max_depth=max_depth,
            max_visited_nodes=max_visited_nodes,
            seen=seen,
            steps=steps,
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
    steps: list[int],
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
                steps=steps,
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
    steps: list[int],
    max_depth: int,
    max_visited_nodes: int,
    multiple_parents_allowed: bool,
    nodes: dict[str, FamilyNode],
) -> Diagnostic | None:
    steps[0] += 1
    too_many_steps = steps[0] > max_visited_nodes
    new_node = node.family_id not in seen and len(seen) >= max_visited_nodes
    if depth > max_depth or too_many_steps or new_node:
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


def _paths_from(
    nodes: dict[str, FamilyNode],
    start: str,
    *,
    max_paths: int,
    max_depth: int,
    found: int,
) -> tuple[FamilyPath, ...] | Diagnostic:
    if start not in nodes:
        return _defect(_MISSING_FAMILY)
    frames: list[tuple[str, tuple[str, ...]]] = [(start, (start,))]
    paths: list[FamilyPath] = []
    while frames:
        if found + len(paths) + len(frames) > max_paths:
            return _defect(_LIMIT)
        node_id, leaf_to_root_ids = frames.pop()
        step = _path_step(
            nodes,
            start,
            node_id,
            leaf_to_root_ids,
            frames,
            found=found + len(paths),
            max_paths=max_paths,
            max_depth=max_depth,
        )
        if isinstance(step, Diagnostic):
            return step
        if step is not None:
            paths.append(step)
    return tuple(paths)


def _path_step(
    nodes: dict[str, FamilyNode],
    start: str,
    node_id: str,
    leaf_to_root_ids: tuple[str, ...],
    frames: list[tuple[str, tuple[str, ...]]],
    *,
    found: int,
    max_paths: int,
    max_depth: int,
) -> FamilyPath | Diagnostic | None:
    node = nodes.get(node_id)
    if node is None:
        return _defect(_MISSING_PARENT)
    if len(leaf_to_root_ids) - 1 > max_depth:
        return _defect(_LIMIT)
    if node.parent_ids:
        return _queue_parents(nodes, node_id, leaf_to_root_ids, node.parent_ids, frames)
    if found >= max_paths:
        return _defect(_LIMIT)
    return FamilyPath(
        family_id=start,
        root_to_leaf=tuple(reversed(leaf_to_root_ids)),
        leaf_to_root=" → ".join(leaf_to_root_ids),
    )


def _queue_parents(
    nodes: dict[str, FamilyNode],
    node_id: str,
    leaf_to_root_ids: tuple[str, ...],
    parents: tuple[str, ...],
    frames: list[tuple[str, tuple[str, ...]]],
) -> Diagnostic | None:
    for parent_id in reversed(parents):
        defect = _parent_defect(nodes, node_id, parent_id, leaf_to_root_ids)
        if defect is not None:
            return defect
        frames.append((parent_id, (*leaf_to_root_ids, parent_id)))
    return None


def _parent_defect(
    nodes: dict[str, FamilyNode],
    node_id: str,
    parent_id: str,
    leaf_to_root_ids: tuple[str, ...],
) -> Diagnostic | None:
    if parent_id == node_id:
        return _defect(_SELF_LOOP)
    if parent_id in leaf_to_root_ids:
        return _defect(_CYCLE)
    if parent_id not in nodes:
        return _defect(_MISSING_PARENT)
    return None


def _defect(message: str) -> Diagnostic:
    return Diagnostic(code="graph_error", level="error", message=message)
