#!/usr/bin/env python3
"""Build and optionally sync the canonical deterministic BioETL graph into Neo4j."""

from __future__ import annotations

import shutil as shutil  # re-exported via __all__
import sys
from typing import TYPE_CHECKING

from memory.graph.sync_pkg import _core_reexport_a as _core_reexport_a
from memory.graph.sync_pkg import _core_reexport_b as _core_reexport_b
from memory.graph.sync_pkg import _core_reexport_c as _core_reexport_c
from memory.graph.sync_pkg import _core_reexport_d as _core_reexport_d

if TYPE_CHECKING:
    from memory.graph.sync_pkg._core_reexport_a import (
        JsonValue as JsonValue,
    )
    from memory.graph.sync_pkg._core_reexport_a import (
        NodeKey as NodeKey,
    )
    from memory.graph.sync_pkg._core_reexport_a import (
        SnapshotSelection as SnapshotSelection,
    )
    from memory.graph.sync_pkg._core_reexport_a import (
        SyncApplyOptions as SyncApplyOptions,
    )
    from memory.graph.sync_pkg._core_reexport_a import (
        _add_file_structure_surfaces as _add_file_structure_surfaces,
    )
    from memory.graph.sync_pkg._core_reexport_a import (
        _coerce_int as _coerce_int,
    )
    from memory.graph.sync_pkg._core_reexport_a import (
        _write_json as _write_json,
    )
    from memory.graph.sync_pkg._core_reexport_a import (
        main as main,
    )
    from memory.graph.sync_pkg._core_reexport_b import (
        DEFAULT_BATCH_SIZE as DEFAULT_BATCH_SIZE,
    )
    from memory.graph.sync_pkg._core_reexport_b import (
        _critical_analysis_audit_issues as _critical_analysis_audit_issues,
    )
    from memory.graph.sync_pkg._core_reexport_b import (
        build_snapshot as build_snapshot,
    )
    from memory.graph.sync_pkg._core_reexport_c import (
        GraphNode as GraphNode,
    )
    from memory.graph.sync_pkg._core_reexport_c import (
        GraphRelation as GraphRelation,
    )
    from memory.graph.sync_pkg._core_reexport_c import (
        GraphSnapshot as GraphSnapshot,
    )
    from memory.graph.sync_pkg._core_reexport_c import (
        _write_export as _write_export,
    )
    from memory.graph.sync_pkg._core_reexport_c import (
        apply_normalization_evidence_only as apply_normalization_evidence_only,
    )
    from memory.graph.sync_pkg._core_reexport_c import (
        build_audit_report as build_audit_report,
    )
    from memory.graph.sync_pkg._core_reexport_c import (
        build_fast_analysis_audit_report as build_fast_analysis_audit_report,
    )
    from memory.graph.sync_pkg._core_reexport_c import (
        snapshot_orphans as snapshot_orphans,
    )
    from memory.graph.sync_pkg._core_reexport_d import (
        DEFAULT_ROOT as DEFAULT_ROOT,
    )
    from memory.graph.sync_pkg._core_reexport_d import (
        SRC_ROOT as SRC_ROOT,
    )
    from memory.graph.sync_pkg._core_reexport_d import (
        Neo4jHttpClient as Neo4jHttpClient,
    )
    from memory.graph.sync_pkg._core_reexport_d import (
        _filtered_snapshot as _filtered_snapshot,
    )
    from memory.graph.sync_pkg._core_reexport_d import (
        _walk_repo_zone_file_structure as _walk_repo_zone_file_structure,
    )
    from memory.graph.sync_pkg._core_reexport_d import (
        _walk_repo_zone_root as _walk_repo_zone_root,
    )
    from memory.graph.sync_pkg._core_reexport_d import (
        load_repo_env as load_repo_env,
    )
    from memory.graph.sync_pkg._core_reexport_d import (
        resolve_neo4j_connection as resolve_neo4j_connection,
    )
    from memory.graph.sync_pkg._core_reexport_d import (
        snapshot_invariant_issues as snapshot_invariant_issues,
    )
    from memory.graph.sync_pkg._core_reexport_d import (
        sync_snapshot as sync_snapshot,
    )


def _install_reexport_shards() -> None:
    g = globals()
    for mod in (
        _core_reexport_a,
        _core_reexport_b,
        _core_reexport_c,
        _core_reexport_d,
    ):
        for name in mod.__all__:
            g[name] = getattr(mod, name)


_install_reexport_shards()

__all__ = [
    name
    for name in globals()
    if not name.startswith("__")
    and name not in {"_install_reexport_shards", "TYPE_CHECKING"}
    and not name.startswith("_core_reexport_")
]

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(DEFAULT_ROOT) not in sys.path:
    sys.path.insert(0, str(DEFAULT_ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
