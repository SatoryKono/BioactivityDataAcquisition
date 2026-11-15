"""Family-ancestor walk and the direct class layer for one IUPHAR target.

Graph limits come only from the approved ``graph_limits`` keys
``max_depth`` and ``max_visited_nodes``. This module does not approve
biological mappings; callers pass those as test or release fixtures.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import overload

from .models import Diagnostic, ProviderAnnotation
from .policy import WORKING_CLASSES, policy_document

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

    paths: Sequence[FamilyPath]
    defects: tuple[GraphDefect, ...]


@dataclass(frozen=True, slots=True)
class FamilyCandidate:
    """One family kept with its class and the family-mapping proof."""

    family_id: str
    iuphar_class: str
    evidence: str
    source: str


@dataclass(frozen=True, slots=True)
class _Ready:
    """Indexed graph that is ready to walk. Defects are already excluded."""

    by_id: dict[str, FamilyNode]
    local: dict[str, GraphDefect]
    starts: tuple[str, ...]
    depth_limit: int
    visited_limit: int


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

    ready = _prepare(
        nodes,
        family_ids=family_ids,
        max_depth=max_depth,
        max_visited_nodes=max_visited_nodes,
        multiple_parents_allowed=multiple_parents_allowed,
    )
    if isinstance(ready, GraphWalk):
        return ready.defects
    defect = _probe(ready)
    if defect is None:
        return ()
    return (defect,)


def build_family_paths(
    nodes: tuple[FamilyNode, ...],
    *,
    family_ids: tuple[str, ...] | None = None,
    max_depth: int | None = None,
    max_visited_nodes: int | None = None,
    multiple_parents_allowed: bool = True,
) -> GraphWalk:
    """Build root-to-leaf paths. Any defect drops every path."""

    ready = _prepare(
        nodes,
        family_ids=family_ids,
        max_depth=max_depth,
        max_visited_nodes=max_visited_nodes,
        multiple_parents_allowed=multiple_parents_allowed,
    )
    if isinstance(ready, GraphWalk):
        return ready
    defect = _probe(ready)
    if defect is not None:
        return GraphWalk(paths=(), defects=(defect,))
    if not ready.starts:
        return GraphWalk(paths=(), defects=())
    counts = _path_counts(ready.by_id, ready.starts)
    return GraphWalk(
        paths=_FamilyPaths(ready.by_id, tuple(sorted(ready.starts)), counts), defects=()
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
    _require_known_classes(resolved)
    family_ids = tuple(annotation.family_ids)
    defects = validate_family_graph(
        nodes,
        family_ids=family_ids,
        multiple_parents_allowed=multiple_parents_allowed,
    )
    type_raw = annotation.type_raw.strip() if annotation.type_raw else ""
    type_class = dict(resolved.type_to_class).get(type_raw) if type_raw else None
    if defects:
        status = STATUS_PARTIAL if type_raw else STATUS_NOT_AVAILABLE
        return _annotation(
            status=status,
            iuphar_class=None,
            candidates=(),
            diagnostics=_diagnostics(defects),
            defects=defects,
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


def _require_known_classes(mapping: ApprovedMapping) -> None:
    foreign = sorted(
        {
            value
            for _name, value in (*mapping.type_to_class, *mapping.family_to_class)
            if value not in WORKING_CLASSES
        }
    )
    if not foreign:
        return
    message = "mapping target is outside the class dictionary: " + ", ".join(foreign)
    raise ValueError(message)


def _prepare(
    nodes: tuple[FamilyNode, ...],
    *,
    family_ids: tuple[str, ...] | None,
    max_depth: int | None,
    max_visited_nodes: int | None,
    multiple_parents_allowed: bool,
) -> _Ready | GraphWalk:
    depth_limit, visited_limit = _resolved_limits(max_depth, max_visited_nodes)
    by_id, local = _node_index(nodes, multiple_parents_allowed)
    if family_ids is None:
        defects = _global_defects(by_id, local)
        if defects:
            return GraphWalk(paths=(), defects=defects)
        starts = tuple(sorted(by_id))
        local = {}
    else:
        starts = family_ids
    missing_starts = _missing_starts(starts, by_id, local)
    if missing_starts:
        return GraphWalk(paths=(), defects=missing_starts)
    return _Ready(by_id, local, starts, depth_limit, visited_limit)


def _missing_starts(
    starts: tuple[str, ...],
    by_id: dict[str, FamilyNode],
    local: dict[str, GraphDefect],
) -> tuple[GraphDefect, ...]:
    defects: list[GraphDefect] = []
    for family_id in starts:
        if family_id in local:
            defects.append(local[family_id])
        elif family_id not in by_id:
            defects.append(GraphDefect(DEFECT_MISSING_PARENT, family_id))
    return tuple(defects)


def _path_counts(
    by_id: dict[str, FamilyNode], starts: tuple[str, ...]
) -> dict[str, int]:
    """Count routes on an already validated DAG without enumerating them."""
    counts: dict[str, int] = {}

    def count(node_id: str) -> int:
        if node_id not in counts:
            parents = by_id[node_id].parent_ids
            counts[node_id] = sum(count(parent) for parent in parents) if parents else 1
        return counts[node_id]

    for start in starts:
        count(start)
    return counts


@dataclass(frozen=True, slots=True, eq=False)
class _FamilyPaths(Sequence[FamilyPath]):
    """Immutable lazy sequence preserving the original sorted path contents."""

    nodes: dict[str, FamilyNode]
    starts: tuple[str, ...]
    counts: dict[str, int]

    def __len__(self) -> int:
        return self._total()

    def _total(self) -> int:
        return sum(self.counts[start] for start in self.starts)

    def __iter__(self) -> Iterator[FamilyPath]:
        for start, copies in sorted(Counter(self.starts).items()):
            stack: list[tuple[tuple[str, ...], int]] = [((start,), copies)]
            while stack:
                path, multiplicity = stack.pop()
                parents = self.nodes[path[-1]].parent_ids
                if parents:
                    stack.extend(
                        ((*path, parent), multiplicity * count)
                        for parent, count in sorted(
                            Counter(parents).items(), reverse=True
                        )
                    )
                else:
                    value = _family_path(path)
                    for _ in range(multiplicity):
                        yield value

    @overload
    def __getitem__(self, index: int) -> FamilyPath: ...

    @overload
    def __getitem__(self, index: slice) -> tuple[FamilyPath, ...]: ...

    def __getitem__(self, index: int | slice) -> FamilyPath | tuple[FamilyPath, ...]:
        total = self._total()
        if isinstance(index, slice):
            return tuple(self[item] for item in range(*index.indices(total)))
        if index < 0:
            index += total
        if not 0 <= index < total:
            raise IndexError("family path index out of range")
        node_id, index = self._select(self.starts, index)
        path = [node_id]
        while self.nodes[node_id].parent_ids:
            node_id, index = self._select(self.nodes[node_id].parent_ids, index)
            path.append(node_id)
        return _family_path(tuple(path))

    def _select(self, node_ids: tuple[str, ...], index: int) -> tuple[str, int]:
        for node_id, copies in sorted(Counter(node_ids).items()):
            count = self.counts[node_id] * copies
            if index < count:
                return node_id, index // copies
            index -= count
        raise IndexError("family path index out of range")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Sequence):
            return NotImplemented
        return self._total() == len(other) and all(
            left == right for left, right in zip(self, other, strict=True)
        )


def _family_path(path: tuple[str, ...]) -> FamilyPath:
    return FamilyPath(
        root_to_leaf=tuple(reversed(path)),
        legacy_leaf_to_root=" → ".join(path),
    )


def _resolved_limits(
    max_depth: int | None,
    max_visited_nodes: int | None,
) -> tuple[int, int]:
    approved_depth, approved_visited = graph_limits()
    depth = _capped_limit(max_depth, approved_depth, "max_depth")
    visited = _capped_limit(max_visited_nodes, approved_visited, "max_visited_nodes")
    return depth, visited


def _capped_limit(requested: int | None, approved: int, name: str) -> int:
    value = approved if requested is None else requested
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} is not approved")
    if value < 1:
        raise ValueError("graph_limits must be positive")
    return min(value, approved)


def _probe(ready: _Ready) -> GraphDefect | None:
    seen: set[str] = set()
    longest: dict[str, int] = {}
    for start in ready.starts:
        defect = _probe_from(ready, start, seen, longest)
        if defect is not None:
            return defect
    return None


def _probe_from(
    ready: _Ready,
    start: str,
    seen: set[str],
    longest: dict[str, int],
) -> GraphDefect | None:
    stack: list[tuple[str, int]] = [(start, 0)]
    path: list[str] = []
    while stack:
        defect = _probe_step(ready, stack, path, seen, longest)
        if defect is not None:
            return defect
    return None


def _probe_step(
    ready: _Ready,
    stack: list[tuple[str, int]],
    path: list[str],
    seen: set[str],
    longest: dict[str, int],
) -> GraphDefect | None:
    node_id, index = stack[-1]
    if index == 0:
        entered = _probe_enter(ready, node_id, path, seen, longest)
        if entered == "skip":
            stack.pop()
            return None
        if isinstance(entered, GraphDefect):
            return entered
        path.append(node_id)
    return _probe_edge(ready, stack, path, longest)


def _probe_enter(
    ready: _Ready,
    node_id: str,
    path: list[str],
    seen: set[str],
    longest: dict[str, int],
) -> GraphDefect | str | None:
    if node_id in ready.local:
        return ready.local[node_id]
    if node_id not in ready.by_id:
        return GraphDefect(DEFECT_MISSING_PARENT, node_id)
    if node_id in longest:
        if len(path) + longest[node_id] > ready.depth_limit:
            return GraphDefect(LIMIT_EXCEEDED, node_id, "max_depth")
        return "skip"
    if len(path) + 1 > ready.depth_limit:
        return GraphDefect(LIMIT_EXCEEDED, node_id, "max_depth")
    if node_id not in seen:
        seen.add(node_id)
        if len(seen) > ready.visited_limit:
            return GraphDefect(LIMIT_EXCEEDED, node_id, "max_visited_nodes")
    return None


def _probe_edge(
    ready: _Ready,
    stack: list[tuple[str, int]],
    path: list[str],
    longest: dict[str, int],
) -> GraphDefect | None:
    node_id, index = stack[-1]
    parents = ready.by_id[node_id].parent_ids
    if index < len(parents):
        stack[-1] = (node_id, index + 1)
        return _follow_parent(ready, stack, path, node_id, parents[index], longest)
    span = _remember_span(node_id, parents, longest)
    path.pop()
    stack.pop()
    if span > ready.depth_limit:
        return GraphDefect(LIMIT_EXCEEDED, node_id, "max_depth")
    return None


def _follow_parent(
    ready: _Ready,
    stack: list[tuple[str, int]],
    path: list[str],
    node_id: str,
    parent_id: str,
    longest: dict[str, int],
) -> GraphDefect | None:
    if parent_id in path:
        kind = DEFECT_SELF_LOOP if parent_id == node_id else DEFECT_CYCLE
        return GraphDefect(kind, node_id)
    known = ready.local.get(parent_id)
    if known is not None:
        return known
    if parent_id not in ready.by_id:
        return GraphDefect(DEFECT_MISSING_PARENT, parent_id)
    if parent_id in longest:
        if len(path) + longest[parent_id] > ready.depth_limit:
            return GraphDefect(LIMIT_EXCEEDED, parent_id, "max_depth")
        return None
    stack.append((parent_id, 0))
    return None


def _remember_span(
    node_id: str,
    parents: tuple[str, ...],
    longest: dict[str, int],
) -> int:
    if not parents:
        longest[node_id] = 1
        return 1
    span = 1 + max(longest[parent_id] for parent_id in parents)
    longest[node_id] = span
    return span


def _global_defects(
    by_id: dict[str, FamilyNode],
    local: dict[str, GraphDefect],
) -> tuple[GraphDefect, ...]:
    if local:
        return tuple(local[family_id] for family_id in sorted(local))
    return _missing_parents(by_id)


def _node_index(
    nodes: tuple[FamilyNode, ...],
    multiple_parents_allowed: bool,
) -> tuple[dict[str, FamilyNode], dict[str, GraphDefect]]:
    grouped: dict[str, list[FamilyNode]] = {}
    for node in nodes:
        grouped.setdefault(node.family_id, []).append(node)
    local: dict[str, GraphDefect] = {}
    by_id: dict[str, FamilyNode] = {}
    for family_id in sorted(grouped):
        group = grouped[family_id]
        signatures = {(item.parent_ids, item.data) for item in group}
        if len(signatures) > 1:
            local[family_id] = GraphDefect(DEFECT_DUPLICATE, family_id)
            continue
        shape = _shape_defect(group[0], multiple_parents_allowed)
        if shape is not None:
            local[family_id] = shape
            continue
        by_id[family_id] = group[0]
    return by_id, local


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
