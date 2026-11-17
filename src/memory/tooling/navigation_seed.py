"""Build a source-bound navigation seed without copying historical assertions."""

from __future__ import annotations

import hashlib
from pathlib import Path

NAVIGATION_SOURCES = (
    ("root-runtime-contract", "AGENTS.md"),
    ("agent-memory", "docs/00-project/ai/memory/agent-memory.md"),
    ("memory-usage-policy", "docs/00-project/ai/agents/guides/MEMORY_USAGE.md"),
    ("daily-workflow", "src/memory/DAILY_WORKFLOW.md"),
    ("orchestration-map", ".codex/agents/ORCHESTRATION.md"),
    ("normative-sources", "docs/00-project/NORMATIVE_SOURCES.md"),
    (
        "dashboard-extension-llm-guide",
        "docs/03-guides/dashboards/dashboard-extension-llm.md",
    ),
)


def build_navigation_seed(root: Path) -> dict[str, list[dict[str, object]]]:
    """Read current source pointers; never initialize, bind, or write a graph.

    The seed intentionally contains navigation metadata only. Runtime versions,
    client registration, historical outcomes and document-body instructions
    must be verified at source rather than inherited from an older seed.
    """
    root = root.resolve(strict=True)
    snapshots: dict[Path, bytes] = {}
    entities: list[dict[str, object]] = []
    for name, relative in NAVIGATION_SOURCES:
        source = root / relative
        resolved = source.resolve(strict=True)
        if not resolved.is_relative_to(root) or resolved != source:
            raise ValueError(f"Navigation source escapes its physical root: {relative}")
        raw = source.read_bytes()
        heading = next(
            (
                line[2:].strip()
                for line in raw.decode("utf-8-sig").splitlines()
                if line.startswith("# ")
            ),
            None,
        )
        if not heading:
            raise ValueError(f"Navigation source has no title: {relative}")
        snapshots[source] = raw
        entities.append(
            {
                "name": name,
                "entityType": "document",
                "observations": [
                    f"Path: {relative}",
                    f"Title: {heading}",
                    f"Source SHA256: {hashlib.sha256(raw).hexdigest()}",
                    "Verify the current source before use; AGENTS.md owns runtime precedence.",
                ],
            }
        )
    if any(path.read_bytes() != raw for path, raw in snapshots.items()):
        raise RuntimeError("Navigation sources changed while building the seed")
    return {"entities": entities, "relations": []}
