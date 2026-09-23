"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import re

from memory.graph.sync_pkg._core_models import NodeKey

__all__ = [
    "_claim_exact_candidates",
    "_claim_target_tokens",
]


def _claim_target_tokens(claim_text: str) -> set[str]:
    tokens: set[str] = set()
    tokens.update(match.group(1) for match in re.finditer(r"`([^`]+)`", claim_text))
    tokens.update(
        match.group(0) for match in re.finditer(r"\bbioetl\s+[\w-]+\b", claim_text)
    )
    tokens.update(
        match.group(0)
        for match in re.finditer(r"\bscripts\.\w+(?:\s+[\w.-]+)?\b", claim_text)
    )
    tokens.update(
        match.group(0)
        for match in re.finditer(r"\b(?:bioetl|domain)\.[\w.]+\b", claim_text)
    )
    return tokens


def _claim_exact_candidates(normalized_token: str) -> tuple[NodeKey, ...]:
    return (
        NodeKey("port_surface", normalized_token),
        NodeKey("cli_command_surface", normalized_token),
        NodeKey("script_surface", normalized_token),
        NodeKey("module_surface", normalized_token),
        NodeKey("workflow_surface", normalized_token),
        NodeKey("execution_path", normalized_token),
    )
