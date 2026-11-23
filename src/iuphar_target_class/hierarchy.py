"""Family graph and direct-layer class for one target.

Paths are structured root to leaf. Repeated rows for one family merge their
parent sets. Legacy chains and synthetic local identifiers stay outside
official paths. A graph defect does not yield a class or subclass from a cut
path. Subclass values come only from an explicit dictionary. The snapshot
annotation capability stays family_only.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache

from .gtopdb_2026_3_1 import (
    ARCHIVE_SHA256,
    ARCHIVE_URL,
    FAMILY_ROWS,
    RELEASE_DATE,
    SQL_SHA256,
    TARGETS_CSV_SHA256,
    TARGETS_CSV_URL,
)
from .iuphar_mapping import approved_class_mappings, require_mapping_release
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
_CONTRADICTORY = "противоречивая запись"
_MISSING_FAMILY = "отсутствующая семья"
_MULTI_PARENT = "множественные родители"
_OFFICIAL = "official"
_LEGACY = "legacy"
_SYNTHETIC = "synthetic_local"
_CAPABILITY = "family_only"
_ABSENCE = "source_unavailable"
_SPACES = (_OFFICIAL, _LEGACY, _SYNTHETIC)


@dataclass(frozen=True, slots=True)
class FamilyNode:
    """One family record. ``payload`` distinguishes contradictory repeats."""

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
    detached_edges: tuple[tuple[str, str, str], ...] = ()
    separated_ids: tuple[tuple[str, str], ...] = ()
    iuphar_subclass_candidates: tuple[str, ...] = ()
    type_origin: str | None = None
    class_origin: str | None = None
    subclass_origin: str | None = None
    annotation_capability: str = _CAPABILITY
    absence_status: str = _ABSENCE


@dataclass(frozen=True, slots=True)
class GraphAdmission:
    """Snapshot graph gate. A defect blocks admission and keeps family_only."""

    admitted: bool
    diagnostics: tuple[Diagnostic, ...]
    annotation_capability: str
    absence_status: str
    detached_edges: tuple[tuple[str, str, str], ...] = ()
    separated_ids: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class SpeciesVariant:
    """One target/species row. Distinct rows are not collapsed by position."""

    target_id: str
    taxon_id: str
    uniprot_ids: tuple[str, ...]
    object_type: str
    annotation: str


@dataclass(frozen=True, slots=True)
class CoverageExclusion:
    """Why one target/species row stays outside the admitted set."""

    target_id: str
    taxon_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class CoverageMatrix:
    """Species, object type, and annotation counts with release provenance."""

    release: str
    annotation_capability: str
    absence_status: str
    provenance: tuple[tuple[str, str], ...]
    variants: tuple[SpeciesVariant, ...]
    ambiguous_uniprot: tuple[tuple[str, tuple[str, ...]], ...]
    counts: tuple[tuple[str, str, str, int], ...]
    exclusions: tuple[CoverageExclusion, ...]


@dataclass(frozen=True, slots=True)
class _PreparedGraph:
    spaces: dict[str, dict[str, FamilyNode]]
    detached_edges: tuple[tuple[str, str, str], ...]

    @property
    def official(self) -> dict[str, FamilyNode]:
        return self.spaces[_OFFICIAL]


def qualified_absence(capability: str, *, completeness_qualified: bool) -> str:
    """Return not_found only for a qualified snapshot that is not family_only."""
    if capability == _CAPABILITY or not completeness_qualified:
        return _ABSENCE
    return "not_found"


def official_material_provenance(release: str) -> tuple[tuple[str, str], ...]:
    """Pinned public GtoPdb hashes. Nothing is fetched and completeness is not claimed."""
    require_mapping_release(release)
    return (
        ("archive_sha256", ARCHIVE_SHA256),
        ("archive_url", ARCHIVE_URL),
        ("release", release),
        ("release_date", RELEASE_DATE),
        ("sql_sha256", SQL_SHA256),
        ("targets_csv_sha256", TARGETS_CSV_SHA256),
        ("targets_csv_url", TARGETS_CSV_URL),
    )


def retain_species_variants(
    records: tuple[SpeciesVariant, ...],
) -> tuple[SpeciesVariant, ...]:
    """Keep every distinct target/species/UniProt row, independent of input order."""
    stored = (_stored_variant(item) for item in records)
    unique = {
        (
            item.target_id,
            item.taxon_id,
            item.uniprot_ids,
            item.object_type,
            item.annotation,
        ): item
        for item in stored
    }
    return tuple(unique[key] for key in sorted(unique))


def coverage_matrix(
    records: tuple[SpeciesVariant, ...],
    exclusions: tuple[CoverageExclusion, ...],
    *,
    release: str,
    provenance: tuple[tuple[str, str], ...],
    completeness_qualified: bool = False,
) -> CoverageMatrix:
    """Count included rows without promoting family_only or picking a first row."""
    variants = retain_species_variants(records)
    return CoverageMatrix(
        release,
        _CAPABILITY,
        qualified_absence(_CAPABILITY, completeness_qualified=completeness_qualified),
        tuple(sorted(provenance)),
        variants,
        _ambiguous_uniprot(variants),
        _coverage_counts(variants),
        tuple(
            sorted(
                exclusions,
                key=lambda item: (item.target_id, item.taxon_id, item.reason),
            )
        ),
    )


def validate_family_graph(
    nodes: tuple[FamilyNode, ...],
    family_ids: tuple[str, ...],
    *,
    max_depth: int,
    max_visited_nodes: int,
    multiple_parents_allowed: bool = True,
) -> Diagnostic | None:
    """Return the first defect in the supplied nodes, or ``None``.

    Every node is checked, not only ``family_ids``. The requested ids select
    the walk that also enforces the visit budget. A cycle, a missing parent,
    or a root distance above ``max_depth`` anywhere in the supplied nodes
    still blocks the graph. The result does not depend on identifier order.
    """
    prepared = _prepare_graph(nodes)
    if isinstance(prepared, Diagnostic):
        return prepared
    return _audit_prepared(
        prepared,
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
    prepared = _prepare_graph(nodes)
    if isinstance(prepared, Diagnostic):
        return prepared
    defect = _audit_prepared(
        prepared,
        family_ids,
        max_depth=max_depth,
        max_visited_nodes=max_visited_nodes,
        multiple_parents_allowed=multiple_parents_allowed,
    )
    if defect is not None:
        return defect
    return _build_from_prepared(
        prepared,
        family_ids,
        max_paths=max_paths,
        max_depth=max_depth,
    )


def admit_family_graph(
    nodes: tuple[FamilyNode, ...],
    family_ids: tuple[str, ...],
    *,
    max_depth: int = GRAPH_MAX_DEPTH,
    max_visited_nodes: int = GRAPH_MAX_VISITED_NODES,
    multiple_parents_allowed: bool = True,
) -> GraphAdmission:
    """Admit a graph only when every supplied node is structurally intact."""
    prepared = _prepare_graph(nodes)
    separated = _separated(family_ids)
    if isinstance(prepared, Diagnostic):
        return GraphAdmission(False, (prepared,), _CAPABILITY, _ABSENCE, (), separated)
    defect = _audit_prepared(
        prepared,
        family_ids,
        max_depth=max_depth,
        max_visited_nodes=max_visited_nodes,
        multiple_parents_allowed=multiple_parents_allowed,
    )
    diagnostics = () if defect is None else (defect,)
    return GraphAdmission(
        defect is None,
        diagnostics,
        _CAPABILITY,
        _ABSENCE,
        prepared.detached_edges,
        separated,
    )


def admit_approved_release(release: str, family_ids: tuple[str, ...]) -> GraphAdmission:
    """Admit the pinned local family graph for one release. No API key is used."""
    require_mapping_release(release)
    return admit_family_graph(_pinned_family_graph(), family_ids)


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
    family_to_subclass: Mapping[str, str] | None = None,
) -> HierarchyResult:
    """Classify against the approved mapping and matching release graph only."""
    types, families = approved_class_mappings(release)
    return normalize_provider_class(
        type_name=type_name.strip().lower() if type_name else None,
        family_ids=family_ids,
        nodes=_pinned_family_graph(),
        type_to_class=types,
        family_to_class=families,
        family_to_subclass=family_to_subclass,
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
    family_to_subclass: Mapping[str, str] | None = None,
    max_depth: int = GRAPH_MAX_DEPTH,
    max_visited_nodes: int = GRAPH_MAX_VISITED_NODES,
    multiple_parents_allowed: bool = True,
) -> HierarchyResult:
    """Map a provider type or family only after the ancestor walk succeeds."""
    prepared = _prepare_graph(nodes)
    separated = _separated(family_ids)
    if isinstance(prepared, Diagnostic):
        return _graph_error_result(
            prepared,
            type_name=type_name,
            type_to_class=type_to_class,
            name=name,
            path_text=path_text,
            separated=separated,
        )
    defect = _audit_prepared(
        prepared,
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
            detached=prepared.detached_edges,
            separated=separated,
        )
    official_ids = _official_ids(family_ids)
    assigned = assign_mapped_class(
        type_name=type_name,
        family_ids=official_ids,
        type_to_class=type_to_class,
        family_to_class=family_to_class,
        name=name,
        path_text=path_text,
    )
    type_origin, class_origin = _field_origins(assigned.proof, assigned.status)
    proof = assigned.proof
    if proof == "family_mapping":
        proof = "отображение семейства"
    evidence = tuple(
        (family_id, family_to_class[family_id])
        for family_id in sorted(official_ids)
        if family_id in family_to_class
    )
    built = _build_from_prepared(
        prepared,
        official_ids,
        max_paths=max_visited_nodes,
        max_depth=max_depth,
    )
    if isinstance(built, Diagnostic):
        return _graph_error_result(
            built,
            type_name=type_name,
            type_to_class=type_to_class,
            name=name,
            path_text=path_text,
            detached=prepared.detached_edges,
            separated=separated,
        )
    subclass, subclass_candidates, subclass_origin = _subclass_from(
        official_ids, family_to_subclass or {}
    )
    source = "iuphar_normalized" if assigned.iuphar_class else None
    return HierarchyResult(
        annotation_status=assigned.status,
        iuphar_class=assigned.iuphar_class,
        iuphar_subclass=subclass,
        iuphar_class_candidates=assigned.candidates,
        proof=proof,
        source=source,
        paths=built,
        family_evidence=evidence,
        diagnostics=(),
        detached_edges=prepared.detached_edges,
        separated_ids=separated,
        iuphar_subclass_candidates=subclass_candidates,
        type_origin=type_origin,
        class_origin=class_origin,
        subclass_origin=subclass_origin,
        annotation_capability=_CAPABILITY,
        absence_status=_ABSENCE,
    )


def _graph_error_result(
    defect: Diagnostic,
    *,
    type_name: str | None,
    type_to_class: Mapping[str, str],
    name: str | None,
    path_text: str | None,
    detached: tuple[tuple[str, str, str], ...] = (),
    separated: tuple[tuple[str, str], ...] = (),
) -> HierarchyResult:
    """Keep a type class. A family class or subclass from a cut path is discarded."""
    typed = assign_mapped_class(
        type_name=type_name,
        family_ids=(),
        type_to_class=type_to_class,
        family_to_class={},
        name=name,
        path_text=path_text,
    )
    mapped = typed.iuphar_class if typed.status == "available" else None
    if mapped:
        type_origin, class_origin = "type_mapping", "type_mapping"
    else:
        type_origin, class_origin = None, None
    return HierarchyResult(
        annotation_status="partial" if mapped else "not_available",
        iuphar_class=mapped,
        iuphar_subclass=None,
        iuphar_class_candidates=(mapped,) if mapped else (),
        proof="type" if mapped else None,
        source="iuphar_normalized" if mapped else None,
        paths=(),
        family_evidence=(),
        diagnostics=(defect,),
        detached_edges=detached,
        separated_ids=separated,
        type_origin=type_origin,
        class_origin=class_origin,
        annotation_capability=_CAPABILITY,
        absence_status=_ABSENCE,
    )


def _space(family_id: str) -> str:
    if family_id.startswith("legacy:"):
        return _LEGACY
    if family_id.startswith("local:"):
        return _SYNTHETIC
    return _OFFICIAL


def _official_ids(family_ids: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        family_id for family_id in family_ids if _space(family_id) == _OFFICIAL
    )


def _separated(family_ids: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted(
            (family_id, _space(family_id))
            for family_id in family_ids
            if _space(family_id) != _OFFICIAL
        )
    )


def _prepare_graph(nodes: tuple[FamilyNode, ...]) -> _PreparedGraph | Diagnostic:
    grouped: dict[tuple[str, str], list[FamilyNode]] = {}
    for node in nodes:
        grouped.setdefault((_space(node.family_id), node.family_id), []).append(node)
    merged: dict[str, dict[str, tuple[str, tuple[str, ...]]]] = {
        space: {} for space in _SPACES
    }
    for space, family_id in sorted(grouped):
        items = grouped[(space, family_id)]
        payloads = {item.payload for item in items}
        if len(payloads) > 1:
            return _defect(_CONTRADICTORY)
        parents = tuple(
            sorted({parent for item in items for parent in item.parent_ids})
        )
        merged[space][family_id] = (next(iter(payloads)), parents)
    spaces: dict[str, dict[str, FamilyNode]] = {space: {} for space in _SPACES}
    detached: list[tuple[str, str, str]] = []
    for space in _SPACES:
        for family_id in sorted(merged[space]):
            payload, parents = merged[space][family_id]
            kept: list[str] = []
            for parent_id in parents:
                parent_space = _space(parent_id)
                if parent_space != space:
                    detached.append((family_id, parent_id, parent_space))
                    continue
                if parent_id not in merged[space]:
                    return _defect(_MISSING_PARENT)
                kept.append(parent_id)
            spaces[space][family_id] = FamilyNode(family_id, tuple(kept), payload)
    return _PreparedGraph(spaces, tuple(sorted(set(detached))))


def _audit_prepared(
    prepared: _PreparedGraph,
    family_ids: tuple[str, ...],
    *,
    max_depth: int,
    max_visited_nodes: int,
    multiple_parents_allowed: bool,
) -> Diagnostic | None:
    for space in _SPACES:
        defect = _structural_defect(
            prepared.spaces[space],
            max_depth=max_depth,
            multiple_parents_allowed=multiple_parents_allowed,
        )
        if defect is not None:
            return defect
    return _walk_ancestors(
        prepared.official,
        _official_ids(family_ids),
        max_depth=max_depth,
        max_visited_nodes=max_visited_nodes,
        multiple_parents_allowed=multiple_parents_allowed,
    )


def _structural_defect(
    nodes: dict[str, FamilyNode],
    *,
    max_depth: int,
    multiple_parents_allowed: bool,
) -> Diagnostic | None:
    """Reject cycles and root distance above ``max_depth`` in any order."""
    for family_id in sorted(nodes):
        node = nodes[family_id]
        if not multiple_parents_allowed and len(node.parent_ids) > 1:
            return _defect(_MULTI_PARENT)
        for parent_id in node.parent_ids:
            if parent_id == family_id:
                return _defect(_SELF_LOOP)
            if parent_id not in nodes:
                return _defect(_MISSING_PARENT)
    distances: dict[str, int] = {}
    for start in sorted(nodes):
        defect = _bind_root_distance(nodes, start, distances, max_depth=max_depth)
        if defect is not None:
            return defect
    return None


def _bind_root_distance(
    nodes: dict[str, FamilyNode],
    start: str,
    distances: dict[str, int],
    *,
    max_depth: int,
) -> Diagnostic | None:
    """Store each node's longest parent-chain length, including finished parents."""
    if start in distances:
        return None
    frames: list[list[int | str]] = [[start, 0]]
    stacked: set[str] = set()
    best: dict[str, int] = {}
    while frames:
        frame = frames[-1]
        node_id = str(frame[0])
        cursor = int(frame[1])
        if node_id in distances:
            frames.pop()
            continue
        parents = nodes[node_id].parent_ids
        if cursor == 0 and node_id not in stacked:
            stacked.add(node_id)
            best[node_id] = 0
        if cursor < len(parents):
            parent_id = parents[cursor]
            if parent_id not in distances:
                if parent_id in stacked:
                    return _defect(_CYCLE)
                frames.append([parent_id, 0])
                continue
            best[node_id] = max(best[node_id], distances[parent_id] + 1)
            frame[1] = cursor + 1
            continue
        distance = best[node_id]
        if distance > max_depth:
            return _defect(_LIMIT)
        distances[node_id] = distance
        stacked.remove(node_id)
        frames.pop()
    return None


def _field_origins(proof: str | None, status: str) -> tuple[str | None, str | None]:
    if proof == "type":
        return "type_mapping", "type_mapping"
    if status in {"partial", "conflicting"}:
        return None, "family_mapping"
    return None, None


def _subclass_from(
    family_ids: tuple[str, ...], mapping: Mapping[str, str]
) -> tuple[str | None, tuple[str, ...], str | None]:
    values = tuple(
        mapping[family_id] for family_id in sorted(family_ids) if family_id in mapping
    )
    distinct = tuple(sorted(set(values)))
    if len(distinct) == 1:
        return distinct[0], values, "subclass_dictionary"
    if distinct:
        return None, values, "subclass_dictionary"
    return None, (), None


def _stored_variant(item: SpeciesVariant) -> SpeciesVariant:
    return SpeciesVariant(
        item.target_id,
        item.taxon_id,
        tuple(sorted(set(item.uniprot_ids))),
        item.object_type,
        _CAPABILITY,
    )


def _ambiguous_uniprot(
    variants: tuple[SpeciesVariant, ...],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    owners: dict[str, set[str]] = {}
    for item in variants:
        for accession in item.uniprot_ids:
            owners.setdefault(accession, set()).add(item.target_id)
    return tuple(
        (accession, tuple(sorted(targets)))
        for accession, targets in sorted(owners.items())
        if len(targets) > 1
    )


def _coverage_counts(
    variants: tuple[SpeciesVariant, ...],
) -> tuple[tuple[str, str, str, int], ...]:
    counts: dict[tuple[str, str, str], int] = {}
    for item in variants:
        key = (item.taxon_id, item.object_type, item.annotation)
        counts[key] = counts.get(key, 0) + 1
    return tuple((*key, counts[key]) for key in sorted(counts))


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


def _build_from_prepared(
    prepared: _PreparedGraph,
    family_ids: tuple[str, ...],
    *,
    max_paths: int,
    max_depth: int,
) -> tuple[FamilyPath, ...] | Diagnostic:
    paths: list[FamilyPath] = []
    for family_id in sorted(_official_ids(family_ids)):
        built = _paths_from(
            prepared.official,
            family_id,
            max_paths=max_paths,
            max_depth=max_depth,
            found=len(paths),
        )
        if isinstance(built, Diagnostic):
            return built
        paths.extend(built)
    return tuple(sorted(paths, key=lambda item: (item.family_id, item.root_to_leaf)))


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
