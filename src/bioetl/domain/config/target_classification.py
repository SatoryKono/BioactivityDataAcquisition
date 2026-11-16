"""Immutable, opt-in configuration for offline IUPHAR target classification."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

TargetClassificationMode = Literal["off", "shadow", "enrich"]

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
        if self.mode not in {"off", "shadow", "enrich"}:
            raise ValueError("target classification mode must be off, shadow or enrich")
        if self.snapshot_manifest is not None and not self.snapshot_manifest.strip():
            raise ValueError("target classification manifest must not be blank")
        if self.snapshot_manifest_sha256 is not None and not re.fullmatch(
            r"[0-9a-f]{64}", self.snapshot_manifest_sha256
        ):
            raise ValueError("target classification manifest hash must be SHA-256 hex")
        supplied = self.snapshot_manifest is not None
        if supplied != (self.snapshot_manifest_sha256 is not None):
            raise ValueError("target classification manifest and hash must be paired")
        if self.mode != "off" and not supplied:
            raise ValueError("enabled target classification requires a pinned manifest")

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
