"""Pure domain normalization functions (no I/O)."""

from __future__ import annotations

from bioetl.domain.normalization.authors import (
    extract_first_item,
    extract_first_string,
    parse_authors_to_list,
)
from bioetl.domain.normalization.control_plane import (
    normalize_contract_ref,
    normalize_contract_version,
    normalize_control_plane_datetime,
    normalize_control_plane_sha256,
    normalize_control_plane_uuid,
    normalize_run_ledger_payload,
    normalize_run_manifest_spec,
    normalize_runtime_anchor_effective_config_hash,
    normalize_runtime_anchor_payload,
)
from bioetl.domain.normalization.dates import (
    format_date_parts,
    normalize_partial_date,
    parse_date_field,
    validate_publication_year,
)
from bioetl.domain.normalization.fingerprints import (
    compute_manifest_execution_fingerprint,
    compute_runtime_anchor_fingerprint,
)
from bioetl.domain.normalization.identifiers import (
    normalize_doi,
    normalize_pmc_id,
    normalize_pmid,
    strip_doi_prefix,
)
from bioetl.domain.normalization.json import (
    canonicalize_json_string,
    serialize_json_canonical,
)
from bioetl.domain.normalization.pages import parse_page_range
from bioetl.domain.normalization.text import (
    normalize_string,
    normalize_to_string,
    strip_html_tags,
)

__all__ = [
    "canonicalize_json_string",
    "compute_manifest_execution_fingerprint",
    "compute_runtime_anchor_fingerprint",
    "extract_first_item",
    "extract_first_string",
    "format_date_parts",
    "normalize_contract_ref",
    "normalize_contract_version",
    "normalize_control_plane_datetime",
    "normalize_control_plane_sha256",
    "normalize_control_plane_uuid",
    "normalize_doi",
    "normalize_partial_date",
    "normalize_pmc_id",
    "normalize_pmid",
    "normalize_run_ledger_payload",
    "normalize_run_manifest_spec",
    "normalize_runtime_anchor_effective_config_hash",
    "normalize_runtime_anchor_payload",
    "normalize_string",
    "normalize_to_string",
    "parse_authors_to_list",
    "parse_date_field",
    "parse_page_range",
    "serialize_json_canonical",
    "strip_doi_prefix",
    "strip_html_tags",
    "validate_publication_year",
]
