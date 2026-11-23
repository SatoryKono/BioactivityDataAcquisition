"""Immutable snapshot/profile identity models and adapter format constants."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from iuphar_target_class.pipeline import IndexedSnapshot
from iuphar_target_class.snapshot import Completeness

REQUIRED_ACCEPTANCE_CHECKS = frozenset(
    {
        "stage0_admission",
        "reference_cases",
        "evidence_integrity",
        "semantic_determinism",
        "pipeline_integration",
    }
)
OUTPUT_NAMES = frozenset(
    {
        "classification.json",
        "evidence.json",
        "candidates.json",
        "components.json",
        "diagnostics.json",
        "metrics.json",
    }
)
NORMALIZATION_VERSION = "bioetl-iuphar-input-v1"
CLASSIFICATION_SCHEMA_VERSION = "3.1.0"


@dataclass(frozen=True, slots=True)
class LoadedIupharSnapshot:
    snapshot: IndexedSnapshot
    completeness: Completeness
    snapshot_manifest_sha256: str
    immutable_uri: str
    retrieved_at: str
    species_taxon_ids: frozenset[str]
    manifest: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class LoadedIupharProfile:
    snapshot: LoadedIupharSnapshot
    profile_sha256: str
    profile_uri: str
    acceptance_sha256: str | None
    normalization_version: str
    rules_version: str
    classification_schema_version: str
    matching_policy_version: str
