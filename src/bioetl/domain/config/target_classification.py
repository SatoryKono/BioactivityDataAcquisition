"""Immutable, opt-in configuration for offline IUPHAR target classification.

RF-001 (#13309) field-layer contract (semantics only; no biological admission):

* ``target_type`` remains the ChEMBL object type and is never an IUPHAR class.
* ``iuphar_*`` columns are reference/direct-layer outputs from the pinned snapshot.
* ``local_*`` columns are local-rule outputs and must not be copied into ``iuphar_*``.
* ``effective_*`` / ``decision_status`` are the final resolution plus provenance.
* ``source_unavailable`` and confirmed ``not_found`` stay distinct match statuses.

Canonical vocabulary: ``iuphar_target_class.semantics``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

TargetClassificationMode = Literal["off", "shadow", "enrich"]
TargetTableContract = Literal["3.0.0", "3.1.0", "3.2.0"]
_TARGET_CLASSIFICATION_MODES = frozenset({"off", "shadow", "enrich"})
_TARGET_TABLE_CONTRACTS = frozenset({"3.0.0", "3.1.0", "3.2.0"})

# RF-001 baseline identity for the additive V31 column set and profile rules.
RF001_SEMANTICS_CONTRACT = "rf001-2026-11-23"
FIELD_LAYER_BY_NAME: dict[str, str] = {
    "target_type": "chembl_object",
    "iuphar_target_id": "iuphar_reference",
    "iuphar_class": "iuphar_reference",
    "iuphar_match_status": "iuphar_reference",
    "iuphar_annotation_status": "iuphar_reference",
    "local_class": "local_rules",
    "effective_class": "effective",
    "effective_source": "effective",
    "decision_status": "effective",
    "target_class_profile_sha256": "effective",
}


def _validate_target_classification_mode(mode: str) -> None:
    if mode not in _TARGET_CLASSIFICATION_MODES:
        raise ValueError("target classification mode must be off, shadow or enrich")


def _default_physical_table_contract(mode: str) -> str:
    return "3.1.0" if mode == "enrich" else "3.0.0"


def _reject_incompatible_table_contract(mode: str, table_contract: str) -> None:
    if mode != "enrich" and table_contract != "3.0.0":
        raise ValueError(
            "off/shadow target profiles require physical table contract 3.0.0"
        )
    if mode == "enrich" and table_contract == "3.0.0":
        raise ValueError(
            "enrich target profile cannot use physical table contract 3.0.0"
        )


def resolve_physical_table_contract(mode: str, table_contract: str | None) -> str:
    """Select the physical table contract without reading a snapshot.

    Computational classification_schema_version stays on the loaded profile.
    off and shadow stay on 3.0.0. enrich stays on 3.1.0 unless the caller
    explicitly selects 3.2.0. Those combinations are the only compatible ones.
    """
    _validate_target_classification_mode(mode)
    if table_contract is None:
        return _default_physical_table_contract(mode)
    if table_contract not in _TARGET_TABLE_CONTRACTS:
        raise ValueError("target table contract must be 3.0.0, 3.1.0 or 3.2.0")
    _reject_incompatible_table_contract(mode, table_contract)
    return table_contract


def _validate_manifest_hash(digest: str | None) -> None:
    if digest is not None and re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ValueError("target classification manifest hash must be SHA-256 hex")


def _require_nonblank_manifest(manifest: str | None) -> None:
    if manifest is not None and not manifest.strip():
        raise ValueError("target classification manifest must not be blank")


def _require_paired_manifest(manifest: str | None, digest: str | None) -> None:
    if (manifest is not None) != (digest is not None):
        raise ValueError("target classification manifest and hash must be paired")


def _require_manifest_when_enabled(mode: str, manifest: str | None) -> None:
    if mode != "off" and manifest is None:
        raise ValueError("enabled target classification requires a pinned manifest")


def _validate_target_classification_manifest(
    mode: str,
    manifest: str | None,
    digest: str | None,
) -> None:
    _require_nonblank_manifest(manifest)
    _validate_manifest_hash(digest)
    _require_paired_manifest(manifest, digest)
    _require_manifest_when_enabled(mode, manifest)


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
# Additive 3.2.0 detail. Arrays are canonical JSON text; null means not computed.
TARGET_CLASSIFICATION_DETAIL_FIELDS: tuple[str, ...] = (
    "iuphar_type_raw",
    "iuphar_source_completeness",
    "iuphar_family_ids",
    "iuphar_subclasses",
    "iuphar_family_paths",
    "local_status",
    "local_subclasses",
    "local_rule_ids",
    "effective_subclasses",
    "conflict_codes",
    "classification_evidence_refs",
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
    table_contract: str | None = None

    def __post_init__(self) -> None:
        _validate_target_classification_mode(self.mode)
        resolve_physical_table_contract(self.mode, self.table_contract)
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
        """Physical table contract. It is not the computational schema version."""
        return resolve_physical_table_contract(self.mode, self.table_contract)

    @property
    def semantics_contract_version(self) -> str:
        """RF-001 vocabulary identity; independent of enrich admission."""
        return RF001_SEMANTICS_CONTRACT


__all__ = [
    "FIELD_LAYER_BY_NAME",
    "RF001_SEMANTICS_CONTRACT",
    "TARGET_CLASSIFICATION_DETAIL_FIELDS",
    "TARGET_CLASSIFICATION_FIELDS",
    "TargetClassificationConfig",
    "TargetClassificationMode",
    "TargetTableContract",
    "resolve_physical_table_contract",
]
