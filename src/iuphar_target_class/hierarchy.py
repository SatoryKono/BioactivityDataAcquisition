"""Family graph and direct-layer class for one target.

Paths are structured root to leaf. The old leaf-to-root text is only a
migration field. A graph defect does not yield a class from a cut path.

RF-005 (#13313): repeated family IDs with the same payload merge parent sets
instead of keeping the first row; subclasses come only from an explicit
dictionary; synthetic/local IDs stay outside the official family graph.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache

from .gtopdb_2026_3_1 import FAMILY_ROWS
from .iuphar_mapping import approved_class_mappings, approved_subclass_mappings
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
_SYNTHETIC_MIXED = "синтетический идентификатор в официальном графе"
_KIND_SYNTHETIC_LOCAL = "synthetic_local"
_KIND_FAMILY = "family"

_SYNTHETIC_PREFIXES = ("local:", "synthetic:", "legacy:")


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


def family_id_kind(family_id: str) -> str:
    """Classify an ID as synthetic/local chain or graph-eligible family ID.

    Production GtoPdb IDs are numeric, but unit fixtures may use letter IDs.
    Only explicit ``local:`` / ``synthetic:`` / ``legacy:`` prefixes are
    segregated from the official family graph.
    """
    lowered = family_id.casefold()
    for prefix in _SYNTHETIC_PREFIXES:
        if lowered.startswith(prefix):
            return _KIND_SYNTHETIC_LOCAL
    return _KIND_FAMILY


def is_synthetic_local_family_id(family_id: str) -> bool:
    """True for ``local:`` / ``synthetic:`` / ``legacy:`` family identifiers."""
    return family_id_kind(family_id) == _KIND_SYNTHETIC_LOCAL


def partition_family_ids(
    family_ids: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Split graph-eligible family IDs from synthetic/legacy/local chains."""
    official: list[str] = []
    other: list[str] = []
    for family_id in family_ids:
        if is_synthetic_local_family_id(family_id):
            other.append(family_id)
        else:
            official.append(family_id)
    return tuple(official), tuple(other)


def assign_mapped_subclass(
    *,
    type_name: str | None,
    family_ids: tuple[str, ...],
    type_to_subclass: Mapping[str, str],
    family_to_subclass: Mapping[str, str],
    iuphar_class: str | None = None,
    family_to_class: Mapping[str, str] | None = None,
) -> str | None:
    """Return a subclass only from the approved type/family dictionaries."""
    mapped = {
        family_to_subclass[family_id]
        for family_id in family_ids
        if family_id in family_to_subclass
    }
    if len(mapped) > 1:
        return None
    if type_name and type_name in type_to_subclass:
        return type_to_subclass[type_name]
    if len(mapped) != 1:
        return None
    subclass = next(iter(mapped))
    if iuphar_class is None or family_to_class is None:
        return subclass
    for family_id in family_ids:
        if (
            family_to_subclass.get(family_id) == subclass
            and family_to_class.get(family_id) == iuphar_class
        ):
            return subclass
    return None


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
    type_sub, family_sub = approved_subclass_mappings(release)
    return normalize_provider_class(
        type_name=type_name.strip().lower() if type_name else None,
        family_ids=family_ids,
        nodes=_pinned_family_graph(),
        type_to_class=types,
        family_to_class=families,
        type_to_subclass=type_sub,
        family_to_subclass=family_sub,
    )


def normalize_provider_class(
    *,
    type_name: str | None,
    family_ids: tuple[str, ...],
    nodes: tuple[FamilyNode, ...],
    type_to_class: Mapping[str, str],
    family_to_class: Mapping[str, str],
    type_to_subclass: Mapping[str, str] | None = None,
    family_to_subclass: Mapping[str, str] | None = None,
    name: str | None = None,
    path_text: str | None = None,
    max_depth: int = GRAPH_MAX_DEPTH,
    max_visited_nodes: int = GRAPH_MAX_VISITED_NODES,
    multiple_parents_allowed: bool = True,
) -> HierarchyResult:
    """Map a provider type or family only after the ancestor walk succeeds."""
    official_ids, other_ids = partition_family_ids(family_ids)
    subclass_types = type_to_subclass or {}
    subclass_families = family_to_subclass or {}
    if other_ids and not official_ids:
        return _graph_error_result(
            Diagnostic(
                code="graph_error",
                level="error",
                message=_SYNTHETIC_MIXED,
            ),
            type_name=type_name,
            type_to_class=type_to_class,
            type_to_subclass=subclass_types,
            name=name,
            path_text=path_text,
        )
    defect = validate_family_graph(
        nodes,
        official_ids,
        max_depth=max_depth,
        max_visited_nodes=max_visited_nodes,
        multiple_parents_allowed=multiple_parents_allowed,
    )
    if defect is not None:
        return _graph_error_result(
            defect,
            type_name=type_name,
            type_to_class=type_to_class,
            type_to_subclass=subclass_types,
            name=name,
            path_text=path_text,
        )
    assigned = assign_mapped_class(
        type_name=type_name,
        family_ids=official_ids,
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
        for family_id in sorted(official_ids)
        if family_id in family_to_class
    )
    built = build_family_paths(
        nodes,
        official_ids,
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
            type_to_subclass=subclass_types,
            name=name,
            path_text=path_text,
        )
    subclass = assign_mapped_subclass(
        type_name=type_name,
        family_ids=official_ids,
        type_to_subclass=subclass_types,
        family_to_subclass=subclass_families,
        iuphar_class=assigned.iuphar_class,
        family_to_class=family_to_class,
    )
    source = "iuphar_normalized" if assigned.iuphar_class else None
    extras: list[Diagnostic] = []
    if other_ids:
        extras.append(
            Diagnostic(
                code="graph_warning",
                level="warning",
                message=_SYNTHETIC_MIXED,
            )
        )
    return HierarchyResult(
        annotation_status=assigned.status,
        iuphar_class=assigned.iuphar_class,
        iuphar_subclass=subclass if assigned.iuphar_class else None,
        iuphar_class_candidates=assigned.candidates,
        proof=proof,
        source=source,
        paths=built,
        family_evidence=evidence,
        diagnostics=tuple(extras),
    )


def _graph_error_result(
    defect: Diagnostic,
    *,
    type_name: str | None,
    type_to_class: Mapping[str, str],
    type_to_subclass: Mapping[str, str],
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
    subclass = (
        assign_mapped_subclass(
            type_name=type_name,
            family_ids=(),
            type_to_subclass=type_to_subclass,
            family_to_subclass={},
        )
        if mapped
        else None
    )
    return HierarchyResult(
        annotation_status="partial" if mapped else "not_available",
        iuphar_class=mapped,
        iuphar_subclass=subclass,
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
    """Index nodes; same payload merges parents, conflicting payloads fail.

    Synthetic/local records are dropped before the official walk. An official
    node that points at a synthetic parent remains a graph defect.
    """
    grouped: dict[str, list[FamilyNode]] = {}
    for node in nodes:
        if is_synthetic_local_family_id(node.family_id):
            continue
        for parent_id in node.parent_ids:
            if is_synthetic_local_family_id(parent_id):
                return _defect(_SYNTHETIC_MIXED)
        grouped.setdefault(node.family_id, []).append(node)
    indexed: dict[str, FamilyNode] = {}
    for family_id in sorted(grouped):
        payloads = {item.payload for item in grouped[family_id]}
        if len(payloads) > 1:
            return _defect(_DUPLICATE)
        payload = next(iter(payloads))
        parents: set[str] = set()
        for item in grouped[family_id]:
            parents.update(item.parent_ids)
        indexed[family_id] = FamilyNode(family_id, tuple(sorted(parents)), payload)
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
