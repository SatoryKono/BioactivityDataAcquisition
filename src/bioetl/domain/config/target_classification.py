"""Immutable, opt-in configuration for offline IUPHAR target classification."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

TargetClassificationMode = Literal["off", "shadow", "enrich"]
_TARGET_CLASSIFICATION_MODES = frozenset({"off", "shadow", "enrich"})


def _validate_target_classification_mode(mode: str) -> None:
    if mode not in _TARGET_CLASSIFICATION_MODES:
        raise ValueError("target classification mode must be off, shadow or enrich")


def _validate_manifest_hash(digest: str | None) -> None:
    if digest is not None and re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ValueError("target classification manifest hash must be SHA-256 hex")


def _validate_target_classification_manifest(
    mode: str,
    manifest: str | None,
    digest: str | None,
) -> None:
    if manifest is not None and not manifest.strip():
        raise ValueError("target classification manifest must not be blank")
    _validate_manifest_hash(digest)
    if (manifest is not None) != (digest is not None):
        raise ValueError("target classification manifest and hash must be paired")
    if mode != "off" and manifest is None:
        raise ValueError("enabled target classification requires a pinned manifest")


TARGET_CLASSIFICATION_FIELDS: tuple[str, ...] = (
    "iuphar_target_id",
    "iuphar_class",
    "iuphar_match_status",
    "iuphar_annotation_status",
    "local_class",
    "effective_class",
    "effective_source",
    "decision_status",
    "target_class_profile_sha256",
)


@dataclass(frozen=True, slots=True)
class TargetClassificationConfig:
    """Select one pinned profile without performing I/O or implying admission.

    The manifest hash identifies the exact input profile. Its actual bytes,
    publication eligibility and source completeness are checked by the loader.
    """

    mode: TargetClassificationMode = "off"
    snapshot_manifest: str | None = None
    snapshot_manifest_sha256: str | None = None

    def __post_init__(self) -> None:
        _validate_target_classification_mode(self.mode)
        _validate_target_classification_manifest(
            self.mode,
            self.snapshot_manifest,
            self.snapshot_manifest_sha256,
        )

    @property
    def enabled(self) -> bool:
        return self.mode != "off"

    @property
    def contract_version(self) -> str:
        return "3.1.0" if self.mode == "enrich" else "3.0.0"


__all__ = [
    "TARGET_CLASSIFICATION_FIELDS",
    "TargetClassificationConfig",
    "TargetClassificationMode",
]
