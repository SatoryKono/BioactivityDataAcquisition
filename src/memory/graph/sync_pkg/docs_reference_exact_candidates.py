"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _normalize_cli_command_name
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.claim_target_tokens import (
    _claim_exact_candidates,
    _claim_target_tokens,
)
from memory.graph.sync_pkg.default_batch_size import GITHUB_WORKFLOWS_PREFIX
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.port_surfaces import PORTS_MODULE_PREFIX

__all__ = [
    "_docs_reference_exact_candidates",
    "_resolve_claim_targets",
]


def _docs_reference_exact_candidates(ref: str) -> tuple[NodeKey, ...]:
    return (
        NodeKey("module_surface", ref),
        NodeKey("script_surface", ref),
        NodeKey("test_artifact", ref),
        NodeKey("config_artifact", ref),
        NodeKey(
            "workflow_surface",
            Path(ref).stem if ref.startswith(GITHUB_WORKFLOWS_PREFIX) else ref,
        ),
        NodeKey("cli_command_surface", _normalize_cli_command_name(ref) or ref),
        NodeKey("file_surface", ref),
        NodeKey("directory_surface", ref),
    )


def _resolve_claim_targets(
    snapshot: GraphSnapshot, claim_text: str
) -> tuple[tuple[NodeKey, str, str], ...]:
    resolved: list[tuple[NodeKey, str, str]] = []
    seen: set[NodeKey] = set()
    for token in sorted(_claim_target_tokens(claim_text)):
        normalized_token = PORTS_MODULE_PREFIX if token == "domain.ports" else token
        for candidate in _claim_exact_candidates(normalized_token):
            if candidate in snapshot.nodes and candidate not in seen:
                resolved.append((candidate, "claim_token", "medium"))
                seen.add(candidate)
                break
    return tuple(resolved)
