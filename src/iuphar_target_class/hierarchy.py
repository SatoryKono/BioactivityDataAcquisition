"""Family-ancestor walk and the direct class layer for one IUPHAR target.

Graph limits come only from the approved ``graph_limits`` keys
``max_depth`` and ``max_visited_nodes``. This module does not approve
biological mappings; callers pass those as test or release fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Diagnostic, ProviderAnnotation
from .policy import policy_document

LIMIT_EXCEEDED = "превышение лимита"
FAMILY_MAPPING_PROOF = "отображение семейства"
NORMALIZED_SOURCE = "iuphar_normalized"
STATUS_AVAILABLE = "available"
STATUS_PARTIAL = "partial"
STATUS_UNMAPPED = "unmapped_type"
STATUS_CONFLICTING = "conflicting"
STATUS_NOT_AVAILABLE = "not_available"
DEFECT_MISSING_PARENT = "отсутствующий родитель"
DEFECT_DUPLICATE = "повторяющийся идентификатор"
DEFECT_SELF_LOOP = "самоссылка"
DEFECT_CYCLE = "цикл"
DEFECT_MULTIPLE_PARENTS = "множественные связи"


@dataclass(frozen=True, slots=True)
class FamilyNode:
    """One family node. ``data`` distinguishes duplicate identifiers."""

    family_id: str
    parent_ids: tuple[str, ...] = ()
    data: str = ""


@dataclass(frozen=True, slots=True)
class GraphDefect:
    """Controlled graph failure. ``limit_key`` is set only for a limit."""

    defect: str
    family_id: str | None = None
    limit_key: str | None = None


@dataclass(frozen=True, slots=True)
class FamilyPath:
    """Structured root-to-leaf path. The legacy string is not used for class."""

    root_to_leaf: tuple[str, ...]
    legacy_leaf_to_root: str


@dataclass(frozen=True, slots=True)
class ApprovedMapping:
    """Caller-supplied fixture. It is not a ``policy.json`` approval."""

    type_to_class: tuple[tuple[str, str], ...] = ()
    family_to_class: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class GraphWalk:
    """Paths are empty whenever ``defects`` is non-empty."""

    paths: tuple[FamilyPath, ...]
    defects: tuple[GraphDefect, ...]


@dataclass(frozen=True, slots=True)
class FamilyCandidate:
    """One family kept with its class and the family-mapping proof."""

    family_id: str
    iuphar_class: str
    evidence: str
    source: str


@dataclass(frozen=True, slots=True)
class DirectAnnotation:
    """Direct-layer outcome. It is not a full classification row."""

    iuphar_annotation_status: str
    iuphar_class: str | None
    iuphar_subclass: str | None
    iuphar_class_candidates: tuple[str, ...]
    family_candidates: tuple[FamilyCandidate, ...]
    diagnostics: tuple[Diagnostic, ...]
    defects: tuple[GraphDefect, ...]
    source: str | None
    partial_basis: str | None


def graph_limits() -> tuple[int, int]:
    """Return the approved ``(max_depth, max_visited_nodes)`` pair."""

    parameters = policy_document()["parameters"]
    if not isinstance(parameters, dict):
        raise ValueError("policy parameters are missing")
    limits = parameters.get("graph_limits")
    if not isinstance(limits, dict):
        raise ValueError("graph_limits are missing")
    depth = limits.get("max_depth")
    visited = limits.get("max_visited_nodes")
    if isinstance(depth, bool) or not isinstance(depth, int):
        raise ValueError("max_depth is not approved")
    if isinstance(visited, bool) or not isinstance(visited, int):
        raise ValueError("max_visited_nodes is not approved")
    if depth < 1 or visited < 1:
        raise ValueError("graph_limits must be positive")
    return depth, visited


def validate_family_graph(
    nodes: tuple[FamilyNode, ...],
    *,
    family_ids: tuple[str, ...] | None = None,
    max_depth: int | None = None,
    max_visited_nodes: int | None = None,
    multiple_parents_allowed: bool = True,
) -> tuple[GraphDefect, ...]:
    """Return structural and limit defects. An empty tuple means the walk fits."""

    return _walk(
        nodes,
        family_ids=family_ids,
        max_depth=max_depth,
        max_visited_nodes=max_visited_nodes,
        multiple_parents_allowed=multiple_parents_allowed,
    ).defects


def build_family_paths(
    nodes: tuple[FamilyNode, ...],
    *,
    family_ids: tuple[str, ...] | None = None,
    max_depth: int | None = None,
    max_visited_nodes: int | None = None,
    multiple_parents_allowed: bool = True,
) -> GraphWalk:
    """Build root-to-leaf paths. Any defect drops every path."""

    return _walk(
        nodes,
        family_ids=family_ids,
        max_depth=max_depth,
        max_visited_nodes=max_visited_nodes,
        multiple_parents_allowed=multiple_parents_allowed,
    )


def normalize_provider_class(
    annotation: ProviderAnnotation,
    nodes: tuple[FamilyNode, ...],
    mapping: ApprovedMapping | None = None,
    *,
    multiple_parents_allowed: bool = True,
) -> DirectAnnotation:
    """Assign a class from an approved fixture, never from a path word."""

    resolved = mapping if mapping is not None else ApprovedMapping()
    family_ids = tuple(annotation.family_ids)
    walk = build_family_paths(
        nodes,
        family_ids=family_ids,
        multiple_parents_allowed=multiple_parents_allowed,
    )
    type_raw = annotation.type_raw.strip() if annotation.type_raw else ""
    type_class = dict(resolved.type_to_class).get(type_raw) if type_raw else None
    if walk.defects:
        status = STATUS_PARTIAL if type_raw else STATUS_NOT_AVAILABLE
        return _annotation(
            status=status,
            iuphar_class=None,
            candidates=(),
            diagnostics=_diagnostics(walk.defects),
            defects=walk.defects,
        )
    if type_class is not None:
        return _annotation(
            status=STATUS_AVAILABLE,
            iuphar_class=type_class,
            candidates=(),
            diagnostics=(),
            defects=(),
            source=NORMALIZED_SOURCE,
        )
    family_map = dict(resolved.family_to_class)
    matched = tuple(
        (family_id, family_map[family_id])
        for family_id in family_ids
        if family_id in family_map
    )
    classes = tuple(dict.fromkeys(item_class for _, item_class in matched))
    if not classes:
        return _annotation(
            status=STATUS_UNMAPPED,
            iuphar_class=None,
            candidates=(),
            diagnostics=(),
            defects=(),
        )
    candidates = tuple(
        FamilyCandidate(
            family_id=family_id,
            iuphar_class=item_class,
            evidence=FAMILY_MAPPING_PROOF,
            source=NORMALIZED_SOURCE,
        )
        for family_id, item_class in matched
    )
    if len(classes) > 1:
        return _annotation(
            status=STATUS_CONFLICTING,
            iuphar_class=None,
            candidates=candidates,
            diagnostics=(),
            defects=(),
            source=NORMALIZED_SOURCE,
        )
    return _annotation(
        status=STATUS_PARTIAL,
        iuphar_class=classes[0],
        candidates=candidates,
        diagnostics=(),
        defects=(),
        source=NORMALIZED_SOURCE,
        partial_basis=FAMILY_MAPPING_PROOF,
    )


def _annotation(
    *,
    status: str,
    iuphar_class: str | None,
    candidates: tuple[FamilyCandidate, ...],
    diagnostics: tuple[Diagnostic, ...],
    defects: tuple[GraphDefect, ...],
    source: str | None = None,
    partial_basis: str | None = None,
) -> DirectAnnotation:
    return DirectAnnotation(
        iuphar_annotation_status=status,
        iuphar_class=iuphar_class,
        iuphar_subclass=None,
        iuphar_class_candidates=tuple(item.iuphar_class for item in candidates),
        family_candidates=candidates,
        diagnostics=diagnostics,
        defects=defects,
        source=source,
        partial_basis=partial_basis,
    )


def _diagnostics(defects: tuple[GraphDefect, ...]) -> tuple[Diagnostic, ...]:
    return tuple(
        Diagnostic(
            code="graph_error",
            level="error",
            message=defect.defect,
            evidence_id=defect.family_id,
        )
        for defect in defects
    )


def _walk(
    nodes: tuple[FamilyNode, ...],
    *,
    family_ids: tuple[str, ...] | None,
    max_depth: int | None,
    max_visited_nodes: int | None,
    multiple_parents_allowed: bool,
) -> GraphWalk:
    depth_limit, visited_limit = _resolved_limits(max_depth, max_visited_nodes)
    by_id, structural = _structural_defects(nodes, multiple_parents_allowed)
    if structural:
        return GraphWalk(paths=(), defects=structural)
    starts = tuple(sorted(by_id)) if family_ids is None else family_ids
    missing_starts = _missing_starts(starts, by_id)
    if missing_starts:
        return GraphWalk(paths=(), defects=missing_starts)
    return _walk_starts(by_id, starts, depth_limit, visited_limit)


def _missing_starts(
    starts: tuple[str, ...],
    by_id: dict[str, FamilyNode],
) -> tuple[GraphDefect, ...]:
    return tuple(
        GraphDefect(defect=DEFECT_MISSING_PARENT, family_id=family_id)
        for family_id in starts
        if family_id not in by_id
    )


def _walk_starts(
    by_id: dict[str, FamilyNode],
    starts: tuple[str, ...],
    depth_limit: int,
    visited_limit: int,
) -> GraphWalk:
    leaf_to_root: list[tuple[str, ...]] = []
    visited: set[str] = set()
    for start in starts:
        defect = _walk_from(
            by_id, start, visited, leaf_to_root, depth_limit, visited_limit
        )
        if defect is not None:
            return GraphWalk(paths=(), defects=(defect,))
    return GraphWalk(paths=_family_paths(leaf_to_root), defects=())


def _walk_from(
    by_id: dict[str, FamilyNode],
    start: str,
    visited: set[str],
    leaf_to_root: list[tuple[str, ...]],
    depth_limit: int,
    visited_limit: int,
) -> GraphDefect | None:
    stack: list[tuple[str, tuple[str, ...]]] = [(start, (start,))]
    while stack:
        node_id, path = stack.pop()
        limit_defect = _limit_defect(node_id, path, visited, depth_limit, visited_limit)
        if limit_defect is not None:
            return limit_defect
        parents = by_id[node_id].parent_ids
        if not parents:
            leaf_to_root.append(path)
            continue
        parent_defect = _enqueue_parents(stack, by_id, node_id, path, parents)
        if parent_defect is not None:
            return parent_defect
    return None


def _limit_defect(
    node_id: str,
    path: tuple[str, ...],
    visited: set[str],
    depth_limit: int,
    visited_limit: int,
) -> GraphDefect | None:
    if len(path) > depth_limit:
        return GraphDefect(
            defect=LIMIT_EXCEEDED,
            family_id=node_id,
            limit_key="max_depth",
        )
    if node_id not in visited:
        visited.add(node_id)
        if len(visited) > visited_limit:
            return GraphDefect(
                defect=LIMIT_EXCEEDED,
                family_id=node_id,
                limit_key="max_visited_nodes",
            )
    return None


def _enqueue_parents(
    stack: list[tuple[str, tuple[str, ...]]],
    by_id: dict[str, FamilyNode],
    node_id: str,
    path: tuple[str, ...],
    parents: tuple[str, ...],
) -> GraphDefect | None:
    for parent_id in reversed(parents):
        if parent_id in path:
            defect = DEFECT_SELF_LOOP if parent_id == node_id else DEFECT_CYCLE
            return GraphDefect(defect=defect, family_id=node_id)
        if parent_id not in by_id:
            return GraphDefect(defect=DEFECT_MISSING_PARENT, family_id=parent_id)
        stack.append((parent_id, (*path, parent_id)))
    return None


def _family_paths(leaf_to_root: list[tuple[str, ...]]) -> tuple[FamilyPath, ...]:
    return tuple(
        FamilyPath(
            root_to_leaf=tuple(reversed(path)),
            legacy_leaf_to_root=" → ".join(path),
        )
        for path in sorted(leaf_to_root)
    )


def _resolved_limits(
    max_depth: int | None,
    max_visited_nodes: int | None,
) -> tuple[int, int]:
    approved_depth, approved_visited = graph_limits()
    depth = approved_depth if max_depth is None else max_depth
    visited = approved_visited if max_visited_nodes is None else max_visited_nodes
    if isinstance(depth, bool) or not isinstance(depth, int):
        raise ValueError("max_depth is not approved")
    if isinstance(visited, bool) or not isinstance(visited, int):
        raise ValueError("max_visited_nodes is not approved")
    if depth < 1 or visited < 1:
        raise ValueError("graph_limits must be positive")
    return depth, visited


def _structural_defects(
    nodes: tuple[FamilyNode, ...],
    multiple_parents_allowed: bool,
) -> tuple[dict[str, FamilyNode], tuple[GraphDefect, ...]]:
    by_id, defects = _collapse_nodes(nodes, multiple_parents_allowed)
    if defects:
        return {}, tuple(defects)
    missing = _missing_parents(by_id)
    if missing:
        return {}, missing
    return by_id, ()


def _collapse_nodes(
    nodes: tuple[FamilyNode, ...],
    multiple_parents_allowed: bool,
) -> tuple[dict[str, FamilyNode], list[GraphDefect]]:
    grouped: dict[str, list[FamilyNode]] = {}
    for node in nodes:
        grouped.setdefault(node.family_id, []).append(node)
    defects: list[GraphDefect] = []
    by_id: dict[str, FamilyNode] = {}
    for family_id in sorted(grouped):
        group = grouped[family_id]
        signatures = {(item.parent_ids, item.data) for item in group}
        if len(signatures) > 1:
            defects.append(GraphDefect(defect=DEFECT_DUPLICATE, family_id=family_id))
            continue
        shape = _shape_defect(group[0], multiple_parents_allowed)
        if shape is not None:
            defects.append(shape)
            continue
        by_id[family_id] = group[0]
    return by_id, defects


def _shape_defect(
    node: FamilyNode,
    multiple_parents_allowed: bool,
) -> GraphDefect | None:
    if node.family_id in node.parent_ids:
        return GraphDefect(defect=DEFECT_SELF_LOOP, family_id=node.family_id)
    if not multiple_parents_allowed and len(node.parent_ids) > 1:
        return GraphDefect(defect=DEFECT_MULTIPLE_PARENTS, family_id=node.family_id)
    return None


def _missing_parents(by_id: dict[str, FamilyNode]) -> tuple[GraphDefect, ...]:
    known = set(by_id)
    return tuple(
        GraphDefect(defect=DEFECT_MISSING_PARENT, family_id=parent_id)
        for family_id in sorted(by_id)
        for parent_id in by_id[family_id].parent_ids
        if parent_id not in known
    )
