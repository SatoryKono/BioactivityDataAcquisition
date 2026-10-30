"""Bounded maintenance of resource-free source census entries after review.

Resource-bearing files cannot use this path. Existing integrity checks still
validate the complete acquisition census and every immutable source reference.
No runtime evidence or lifecycle fact is created or rebound.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from scripts.engineering.qa.external_resource_inventory import SourceBlob


def rebind_resource_free_sources(
    payload: dict[str, Any],
    sources: Mapping[str, bytes],
    blobs: Mapping[str, SourceBlob],
    *,
    commit: str,
    tree: str,
    reviewed: Mapping[str, str],
) -> dict[str, Any]:
    """Requalify only explicitly reviewed, reference-free existing source files."""
    from scripts.engineering.qa.external_resource_inventory import (
        _references,
        validate_inventory,
    )

    original = payload["source_files"]
    if set(original) != set(blobs) or set(sources) != set(blobs):
        raise ValueError(
            "Source census additions/removals require full inventory review"
        )
    changed = {path for path, blob in blobs.items() if original[path] != blob.oid}
    if not changed or changed != set(reviewed):
        raise ValueError("Reviewed source set must exactly match changed source blobs")
    referenced = {ref["file"] for ref in _references(payload)}
    if changed & referenced:
        raise ValueError(
            "Resource-bearing source changes require full inventory review"
        )
    for path in changed:
        actual = hashlib.sha256(sources[path].replace(b"\r\n", b"\n")).hexdigest()
        if reviewed[path] != actual or blobs[path].sha256 != actual:
            raise ValueError(f"Reviewed source digest differs: {path}")
    updated = copy.deepcopy(payload)
    updated["source_commit"] = commit
    updated["source_tree"] = tree
    updated["source_files"] = {path: blob.oid for path, blob in blobs.items()}
    for ref in _references(updated):
        ref["source_commit"] = commit
    updated.setdefault("source_rebindings", []).append(
        {
            "from_commit": payload["source_commit"],
            "to_commit": commit,
            "reviewed_resource_free_sources": dict(reviewed),
        }
    )
    errors = validate_inventory(updated, sources, blobs)
    if errors:
        raise ValueError("Source requalification failed: " + "; ".join(errors))
    return updated
