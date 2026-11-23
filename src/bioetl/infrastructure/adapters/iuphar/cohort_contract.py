"""Typed source contract for canonical ChEMBL target cohort conversion."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

NORMALIZED_TARGET_SCHEMA = "chembl.target.normalized_silver.v1"
CSV_SOURCE_FORMAT = "chembl_target_silver_csv_v1"
ARROW_SOURCE_FORMAT = "chembl_target_silver_arrow_ipc_v1"
_RESERVED = frozenset(
    {
        "input_row_id",
        "target_kind",
        "import_profile",
        "source_path",
        "source_sha256",
        "source_record",
        "source_business_data",
    }
)
_REQUIRED = frozenset(
    {
        "target_id",
        "target_type",
        "taxonomy_id",
        "pref_name",
        "organism",
        "component_accessions",
    }
)
_COLUMNS = (
    "input_row_id",
    "target_kind",
    "target_chembl_id",
    "target_id",
    "uniprot",
    "uniprot_equivalent",
    "uniprot_xref",
    "organism",
    "name",
    "source_organism",
    "synonyms",
    "ec",
    "gene_symbol",
    "gene_id",
    "source_business_data",
)


class CohortConversionError(ValueError):
    """A rejected record with an explicit diagnostic for the immutable ledger."""

    def __init__(self, message: str, source_record: int, row_id: str) -> None:
        super().__init__(message)
        self.source_record = source_record
        self.row_id = row_id


@dataclass(frozen=True, slots=True)
class CohortExportRequest:
    """Technical source contract; no field grants biological/reference approval."""

    source_path: Path
    source_sha256: str
    source_format: Literal[
        "chembl_target_silver_csv_v1", "chembl_target_silver_arrow_ipc_v1"
    ]
    source_schema_version: str
    approval_reference: str
    environment: str
    target_kind: Literal["protein"] = "protein"
    direct_iuphar_id_column: str | None = None


@dataclass(frozen=True, slots=True)
class CanonicalCohortExport:
    canonical_path: Path
    raw_copy_path: Path
    conversion_ledger_path: Path
    canonical_sha256: str
    raw_sha256: str
    conversion_ledger_sha256: str
    row_ids: tuple[str, ...]


def _validate_request(request: CohortExportRequest) -> None:
    if (
        request.source_schema_version != NORMALIZED_TARGET_SCHEMA
        or request.target_kind != "protein"
    ):
        raise ValueError("explicit normalized ChEMBL target v1 protein schema required")
    if request.source_format not in {CSV_SOURCE_FORMAT, ARROW_SOURCE_FORMAT}:
        raise ValueError("unsupported normalized target source format")
    if not request.approval_reference.strip() or not request.environment.strip():
        raise ValueError(
            "technical mapping reference and execution environment required"
        )
    if re.fullmatch(r"[0-9a-f]{64}", request.source_sha256) is None:
        raise ValueError("expected pinned normalized source SHA-256")
    if request.direct_iuphar_id_column in {
        "target_id",
        "target_chembl_id",
        "entity_id",
    }:
        raise ValueError("ChEMBL identity cannot be selected as direct IUPHAR identity")
