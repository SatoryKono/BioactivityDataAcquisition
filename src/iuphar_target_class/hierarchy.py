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
    missing_starts = tuple(
        GraphDefect(defect=DEFECT_MISSING_PARENT, family_id=family_id)
        for family_id in starts
        if family_id not in by_id
    )
    if missing_starts:
        return GraphWalk(paths=(), defects=missing_starts)
    leaf_to_root: list[tuple[str, ...]] = []
    visited: set[str] = set()
    for start in starts:
        stack: list[tuple[str, tuple[str, ...]]] = [(start, (start,))]
        while stack:
            node_id, path = stack.pop()
            if len(path) > depth_limit:
                return GraphWalk(
                    paths=(),
                    defects=(
                        GraphDefect(
                            defect=LIMIT_EXCEEDED,
                            family_id=node_id,
                            limit_key="max_depth",
                        ),
                    ),
                )
            if node_id not in visited:
                visited.add(node_id)
                if len(visited) > visited_limit:
                    return GraphWalk(
                        paths=(),
                        defects=(
                            GraphDefect(
                                defect=LIMIT_EXCEEDED,
                                family_id=node_id,
                                limit_key="max_visited_nodes",
                            ),
                        ),
                    )
            parents = by_id[node_id].parent_ids
            if not parents:
                leaf_to_root.append(path)
                continue
            for parent_id in reversed(parents):
                if parent_id in path:
                    defect = DEFECT_SELF_LOOP if parent_id == node_id else DEFECT_CYCLE
                    return GraphWalk(
                        paths=(),
                        defects=(GraphDefect(defect=defect, family_id=node_id),),
                    )
                if parent_id not in by_id:
                    return GraphWalk(
                        paths=(),
                        defects=(
                            GraphDefect(
                                defect=DEFECT_MISSING_PARENT, family_id=parent_id
                            ),
                        ),
                    )
                stack.append((parent_id, (*path, parent_id)))
    paths = tuple(
        FamilyPath(
            root_to_leaf=tuple(reversed(path)),
            legacy_leaf_to_root=" → ".join(path),
        )
        for path in sorted(leaf_to_root)
    )
    return GraphWalk(paths=paths, defects=())


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
        node = group[0]
        if node.family_id in node.parent_ids:
            defects.append(GraphDefect(defect=DEFECT_SELF_LOOP, family_id=family_id))
            continue
        if not multiple_parents_allowed and len(node.parent_ids) > 1:
            defects.append(
                GraphDefect(defect=DEFECT_MULTIPLE_PARENTS, family_id=family_id)
            )
            continue
        by_id[family_id] = node
    if defects:
        return {}, tuple(defects)
    known = set(by_id)
    for family_id in sorted(by_id):
        for parent_id in by_id[family_id].parent_ids:
            if parent_id not in known:
                defects.append(
                    GraphDefect(defect=DEFECT_MISSING_PARENT, family_id=parent_id)
                )
    if defects:
        return {}, tuple(defects)
    return by_id, ()
