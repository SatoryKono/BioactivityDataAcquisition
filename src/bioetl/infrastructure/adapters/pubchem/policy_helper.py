"""Policy helpers for PubChem fetch loop controls and parsing."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from bioetl.domain.ports import LoggerPort

__all__ = [
    "is_blank_value",
    "is_limit_reached",
    "is_valid_inchikey",
    "iter_cid_batches",
    "parse_valid_cids",
]


def is_limit_reached(limit: int | None, fetched: int) -> bool:
    """Return True when a configured record limit has been reached."""
    return limit is not None and fetched >= limit


def is_blank_value(value: str | None) -> bool:
    """Return True for empty/whitespace or None strings."""
    return value is None or not value.strip()


def is_valid_inchikey(inchikey: str) -> bool:
    """Basic InChIKey shape validation."""
    return len(inchikey) == 27 and inchikey.count("-") == 2


def parse_valid_cids(
    cid_list: list[str],
    *,
    logger: LoggerPort,
    provider_name: str,
) -> list[int]:
    """Parse CID strings to integers, logging skipped invalid values."""
    valid_cids: list[int] = []
    for cid in cid_list:
        try:
            valid_cids.append(int(cid))
        except (ValueError, TypeError):
            logger.warning("invalid_cid_skipped", provider=provider_name, cid=cid)
    return valid_cids


def iter_cid_batches(cid_list: list[int], batch_size: int) -> Iterator[list[int]]:
    """Yield CID batches for bulk fetches."""
    for idx in range(0, len(cid_list), batch_size):
        yield cid_list[idx : idx + batch_size]
