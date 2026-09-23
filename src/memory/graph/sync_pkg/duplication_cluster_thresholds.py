"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _coerce_int
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.complexity_analysis_context import (
    _complexity_analysis_context,
)
from memory.graph.sync_pkg.complexity_candidate_context import (
    _emit_complexity_candidate,
)
from memory.graph.sync_pkg.duplication_analysis_config import (
    _duplication_analysis_config,
)
from memory.graph.sync_pkg.evaluate_complexity_surface import (
    _evaluate_complexity_surface,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.promotion_targets_from_payload import (
    _complexity_analysis_config,
    _retirement_analysis_config,
)
from memory.graph.sync_pkg.retirement_analysis_context import (
    _prime_retirement_age_cache,
    _retirement_analysis_context,
    _retirement_candidate_payload,
)
from memory.graph.sync_pkg.retirement_analysis_label_sets import (
    _retirement_candidate_nodes,
)
from memory.graph.sync_pkg.retirement_marker_sets import _emit_retirement_candidate

__all__ = [
    "_add_complexity_analysis_surfaces",
    "_add_retirement_analysis_surfaces",
    "_duplication_cluster_thresholds",
]


def _duplication_cluster_thresholds(config: dict[str, object]) -> tuple[int, int]:
    return _coerce_int(config.get("min_cluster_size", 2), 2), _coerce_int(
        config.get("min_ast_nodes", 12), 12
    )


def _add_retirement_analysis_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    memory_mapping: dict[str, object],
) -> None:
    duplication_config = _duplication_analysis_config(memory_mapping)
    config = _retirement_analysis_config(memory_mapping, duplication_config)
    if not config.enabled or not config.family_names:
        return
    context = _retirement_analysis_context(snapshot, config, today)

    candidate_nodes = _retirement_candidate_nodes(
        snapshot,
        duplication_config=duplication_config,
        family_names=context.family_names,
        family_cache=context.family_cache,
    )
    _prime_retirement_age_cache(
        root, context.today_date, context.age_cache, candidate_nodes
    )

    for node, source_path, family, module_key in candidate_nodes:
        candidate_payload = _retirement_candidate_payload(
            snapshot,
            root,
            node,
            source_path,
            module_key,
            indexes=context.indexes,
            label_sets=context.label_sets,
            text_cache=context.text_cache,
            age_cache=context.age_cache,
            family_name=family.name,
            config=config,
        )
        if candidate_payload is None:
            continue
        _emit_retirement_candidate(
            snapshot, project, today, config, node, candidate_payload
        )


def _add_complexity_analysis_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    memory_mapping: dict[str, object],
) -> None:
    duplication_config = _duplication_analysis_config(memory_mapping)
    retirement_config = _retirement_analysis_config(memory_mapping, duplication_config)
    config = _complexity_analysis_config(
        memory_mapping, duplication_config, retirement_config
    )
    if not config.enabled or not config.family_names:
        return
    analysis_context = _complexity_analysis_context(snapshot, config)
    for node in sorted(
        snapshot.nodes.values(), key=lambda item: (item.key.label, item.key.name)
    ):
        candidate_payload = _evaluate_complexity_surface(
            snapshot,
            root,
            node,
            duplication_config=duplication_config,
            family_names=analysis_context.family_names,
            family_cache=analysis_context.family_cache,
            label_sets=analysis_context.label_sets,
            indexes=analysis_context.indexes,
            text_cache=analysis_context.text_cache,
            config=config,
        )
        if candidate_payload is None:
            continue
        _emit_complexity_candidate(
            snapshot, project, today, config, node, candidate_payload
        )
