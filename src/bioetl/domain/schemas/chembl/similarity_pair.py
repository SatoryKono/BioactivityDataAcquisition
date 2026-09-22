"""Framework-independent complete-pair invariant for similarity records."""

from __future__ import annotations

import re
from collections.abc import Mapping
from math import isfinite
from numbers import Real


def is_public_document_id(value: object) -> bool:
    """Recognize positive public ChEMBL IDs without inferring internal IDs."""
    return isinstance(value, str) and re.fullmatch(r"CHEMBL[1-9]\d*", value) is not None


def _present(value: object) -> bool:
    return isinstance(value, str) or (isinstance(value, Real) and isfinite(value))


def _positive_number(value: object) -> bool:
    return isinstance(value, Real) and isfinite(value) and float(value) > 0


def valid_similarity_pair(record: Mapping[str, object]) -> bool:
    """Require distinct endpoints from one namespace, never a mixed pair."""
    first, second = record.get("publication_id1"), record.get("publication_id2")
    if any(map(_present, (first, second))):
        return all(map(is_public_document_id, (first, second))) and first != second
    first, second = record.get("doc_1"), record.get("doc_2")
    return all(map(_positive_number, (first, second))) and first != second


def validate_public_pair(first: str | None, second: str | None) -> None:
    """Reject incomplete, malformed and self-referential public pairs."""
    if not all(map(is_public_document_id, (first, second))):
        raise ValueError("Both public document ChEMBL identifiers are required")
    if first == second:
        raise ValueError("Document cannot be similar to itself")


def validate_legacy_pair(first: int | None, second: int | None) -> None:
    """Retain the positive internal-ID contract for legacy records."""
    if first is None or second is None:
        raise ValueError("Both document identifiers are required")
    if min(first, second) <= 0:
        raise ValueError("doc_1 and doc_2 must be positive")
    if first == second:
        raise ValueError("Document cannot be similar to itself")
