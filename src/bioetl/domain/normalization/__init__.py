"""Pure domain normalization functions (no I/O)."""

from __future__ import annotations

from bioetl.domain.normalization.authors import (
    extract_first_item,
    extract_first_string,
    parse_authors_to_list,
)
from bioetl.domain.normalization.control_plane import (
    build_execution_identity_payload,
    normalize_contract_ref,
    normalize_contract_version,
    normalize_control_plane_datetime,
    normalize_control_plane_opaque_hash_ref,
    normalize_control_plane_sha256,
    normalize_control_plane_strict_sha256,
    normalize_control_plane_uuid,
    normalize_execution_identity_payload,
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
    compute_execution_identity_fingerprint,
    compute_input_snapshot_identity_fingerprint,
    compute_manifest_execution_fingerprint,
)
from bioetl.domain.normalization.hash_identity import (
    normalize_hash_identity_record,
    normalize_hash_identity_value,
    serialize_hash_identity_canonical_json,
)
from bioetl.domain.normalization.identifiers import (
    normalize_doi,
    normalize_pmc_id,
    normalize_pmid,
    strip_doi_prefix,
)
from bioetl.domain.normalization.join_keys import (
    JOIN_KEY_NORMALIZATION_POLICIES,
    JoinKeyNormalizationPolicy,
    get_join_key_normalization_policy,
    normalize_join_key_scalar,
    normalize_join_key_text,
    stringify_join_key_value,
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
    "JOIN_KEY_NORMALIZATION_POLICIES",
    "JoinKeyNormalizationPolicy",
    "build_execution_identity_payload",
    "canonicalize_json_string",
    "compute_execution_identity_fingerprint",
    "compute_input_snapshot_identity_fingerprint",
    "compute_manifest_execution_fingerprint",
    "extract_first_item",
    "extract_first_string",
    "format_date_parts",
    "get_join_key_normalization_policy",
    "normalize_contract_ref",
    "normalize_contract_version",
    "normalize_control_plane_datetime",
    "normalize_control_plane_opaque_hash_ref",
    "normalize_control_plane_sha256",
    "normalize_control_plane_strict_sha256",
    "normalize_control_plane_uuid",
    "normalize_doi",
    "normalize_execution_identity_payload",
    "normalize_hash_identity_record",
    "normalize_hash_identity_value",
    "normalize_join_key_scalar",
    "normalize_join_key_text",
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
    "serialize_hash_identity_canonical_json",
    "serialize_json_canonical",
    "stringify_join_key_value",
    "strip_doi_prefix",
    "strip_html_tags",
    "validate_publication_year",
]
