"""Manifest diagnostics snapshot helper bridge."""

from __future__ import annotations

from bioetl.application.services.control_plane.manifest.diagnostics.nested_mapping import (
    lookup_mapping_path,
)
from bioetl.application.services.control_plane.manifest.diagnostics.snapshot_ledger import (
    collect_ledger_input_snapshot_refs,
)
from bioetl.application.services.control_plane.manifest.diagnostics.snapshot_materialization import (
    resolve_post_manifest_input_snapshot_materialization_mode,
)
from bioetl.application.services.control_plane.manifest.diagnostics.snapshot_refs import (
    collect_input_snapshot_content_hashes,
    collect_input_snapshot_ids,
    collect_input_snapshot_refs,
    compute_input_snapshot_identity_fingerprint,
)
from bioetl.application.services.control_plane.manifest.diagnostics.snapshot_summary import (
    merge_ledger_input_snapshots_into_summary,
)

# Legacy aliases retained while helper imports are migrated incrementally.
_lookup_mapping_path = lookup_mapping_path
_collect_input_snapshot_refs = collect_input_snapshot_refs
_collect_input_snapshot_ids = collect_input_snapshot_ids
_collect_input_snapshot_content_hashes = collect_input_snapshot_content_hashes
_compute_input_snapshot_identity_fingerprint = (
    compute_input_snapshot_identity_fingerprint
)

__all__ = [
    "_collect_input_snapshot_content_hashes",
    "_collect_input_snapshot_ids",
    "_collect_input_snapshot_refs",
    "_compute_input_snapshot_identity_fingerprint",
    "_lookup_mapping_path",
    "collect_input_snapshot_content_hashes",
    "collect_input_snapshot_ids",
    "collect_input_snapshot_refs",
    "collect_ledger_input_snapshot_refs",
    "compute_input_snapshot_identity_fingerprint",
    "merge_ledger_input_snapshots_into_summary",
    "resolve_post_manifest_input_snapshot_materialization_mode",
]
