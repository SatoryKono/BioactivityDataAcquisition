"""Core type aliases and identifiers for BioETL domain layer.

No I/O operations allowed (REQ-ARCH-003).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, NewType, TypedDict
from uuid import UUID

if TYPE_CHECKING:
    import pyarrow

__all__ = [
    "ArrowSchema",
    "BatchID",
    "BronzeRecord",
    "ContentHash",
    "EntityID",
    "GoldRecord",
    "GoldSchemaType",
    "JsonDict",
    "MetaDict",
    "PrimaryId",
    "RunID",
    "SilverRecord",
]

# ── NewType identifiers ──────────────────────────────────────────────

RunID = NewType("RunID", UUID)
"""Unique identifier for a pipeline run (correlation ID)."""

EntityID = NewType("EntityID", str)
"""Business key for an entity (e.g., 'CHEMBL123', 'pubchem:2244')."""

ContentHash = NewType("ContentHash", str)
"""SHA256 hash of canonical record representation for versioning."""

BatchID = NewType("BatchID", UUID)
"""Unique identifier for a data batch."""

# ── Type aliases ──────────────────────────────────────────────────────

type ArrowSchema = "pyarrow.Schema"
"""PyArrow schema type alias (runtime: pyarrow.Schema, import-time: string)."""

type JsonDict = dict[str, Any]  # Any: JSON payloads have heterogeneous values
"""Type alias for JSON-like dictionaries with string keys and heterogeneous values.

Use instead of ``dict[str, Any]`` for data originating from external APIs,
configuration files (YAML/JSON), or any other untyped key-value mapping.
Reduces visual type-debt while preserving semantic clarity.
"""

type BronzeRecord = JsonDict  # raw API JSON has heterogeneous values
"""Untyped dictionary representing a raw record from the source."""

type GoldRecord = JsonDict  # heterogeneous scalar types before Pandera coercion
"""Record after Silver→Gold transform, before schema validation."""

type MetaDict = JsonDict  # freeform metadata (str|int|float|datetime|None)
"""Freeform metadata bag used in aggregates, audit entries, events."""

type GoldSchemaType = type[object]
"""Gold schema class accepted by validation wiring.

Concrete Pandera model imports belong in domain schema/contract packages, not in
shared domain identifier aliases.
"""

type PrimaryId = str | int
"""Primary identifier extracted from a Bronze record (e.g., ChEMBL ID string or numeric ID)."""


# ── TypedDict ─────────────────────────────────────────────────────────


class SilverRecord(TypedDict, total=False):
    """Normalized record for Silver layer."""

    entity_id: str
    content_hash: str
    # Other fields are dynamic based on entity type
