"""RF-002 UniProt identifier roles for classification matching.

Separates primary object accessions from auxiliary cross-references so unknown
xref tokens do not create empty exact-channels. This module versions the
matching/normalization policy change; it does not rewrite historical results
or claim biological accuracy. Independent qualification remains RF-008.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from types import MappingProxyType

RF002_CONTRACT_VERSION = "rf002-2026-11-23"
RF002_ISSUE = "https://github.com/SatoryKono/BioactivityDataAcquisition/issues/13310"
RF002_EPIC = "https://github.com/SatoryKono/BioactivityDataAcquisition/issues/13308"
MATCHING_POLICY_VERSION = "rf002-uniprot-roles-2026-11-23"
ANCHOR_PRIORITY_POLICY_VERSION = "hgnc-primary-uniprot-priority-v1"
CHANNEL_EC_POLICY_VERSION = "hgnc-uniprot-channel-ec-v1"
RANKED_CLASS_POLICY_VERSION = "hgnc-uniprot-name-ec-keyword-v1"
TRANSCRIPTION_FACTOR_POLICY_VERSION = "hgnc-uniprot-name-ec-keyword-tf-v1"
REVIEWED_CLASS_POLICY_VERSION = "hgnc-uniprot-reviewed-target-class-v1"
RANKED_CLASS_POLICIES = frozenset(
    {
        RANKED_CLASS_POLICY_VERSION,
        TRANSCRIPTION_FACTOR_POLICY_VERSION,
        REVIEWED_CLASS_POLICY_VERSION,
    }
)
TRANSCRIPTION_FACTOR_POLICIES = frozenset(
    {TRANSCRIPTION_FACTOR_POLICY_VERSION, REVIEWED_CLASS_POLICY_VERSION}
)
EC_EFFECTIVE_POLICIES = RANKED_CLASS_POLICIES | {CHANNEL_EC_POLICY_VERSION}
ANCHOR_PRIORITY_POLICIES = EC_EFFECTIVE_POLICIES | {ANCHOR_PRIORITY_POLICY_VERSION}


def normalize_hgnc_ids(value: str | None) -> tuple[str, ...]:
    """Normalize explicit HGNC identifiers without interpreting other namespaces."""
    identifiers = (
        re.fullmatch(r"(?:HGNC:\s*)?((?a:[1-9]\d*))", token.strip(), re.IGNORECASE)
        for token in re.split(r"[|,;]", value or "")
    )
    return tuple(dict.fromkeys(match[1] for match in identifiers if match))


# Profiles / receipts recorded under the pre-RF-002 merge of component + xref
# into one mandatory ``uniprot`` channel do not qualify this policy.
LEGACY_MATCHING_POLICY_VERSION = "pre-rf002-merged-uniprot-anchors"

IDENTIFIER_ROLES: Mapping[str, Mapping[str, str]] = MappingProxyType(
    {
        "primary": MappingProxyType(
            {
                "source_field": "component_accessions",
                "kernel_field": "uniprot",
                "meaning": (
                    "Primary UniProt accessions of the ChEMBL target object "
                    "(component list). Mandatory exact-channel anchors."
                ),
                "matching": "exact_channel",
            }
        ),
        "proven_equivalent": MappingProxyType(
            {
                "source_field": "target_xref_uniprot_ids ∩ component_accessions",
                "kernel_field": "uniprot_equivalent",
                "meaning": (
                    "Xref tokens that duplicate a primary accession. Recorded in "
                    "evidence; they do not open a second mandatory exact channel."
                ),
                "matching": "evidence_only",
            }
        ),
        "auxiliary_xref": MappingProxyType(
            {
                "source_field": "target_xref_uniprot_ids \\ component_accessions",
                "kernel_field": "uniprot_xref",
                "meaning": (
                    "Auxiliary UniProt cross-references. Unknown values yield "
                    "diagnostics; they must not force false ambiguity."
                ),
                "matching": "diagnostic_only",
            }
        ),
    }
)

COMPONENT_SCOPE_POLICY: Mapping[str, str] = MappingProxyType(
    {
        "single_protein": (
            "For SINGLE PROTEIN, primary component accessions identify the object."
        ),
        "complex_or_family": (
            "A component accession match does not prove identity of a multi-component "
            "complex, protein family, or group object; pipeline keeps "
            "complex_component_only / ambiguous when the matched catalog id is not "
            "itself a complex."
        ),
        "name_only": (
            "Text channels (exact_name / exact_synonym) never confirm identity alone."
        ),
    }
)

DIAGNOSTIC_CODES: Mapping[str, str] = MappingProxyType(
    {
        "unknown_auxiliary_uniprot": (
            "Auxiliary UniProt xref has no catalog hit under the active species guard"
        ),
        "auxiliary_uniprot_divergence": (
            "Auxiliary UniProt xref hits a different catalog target than the primary "
            "decision; recorded as diagnostic, not identity_conflict"
        ),
        "identity_conflict": (
            "Two or more trusted/primary exact channels disagree; unchanged from "
            "pre-RF-002 strict API"
        ),
    }
)


def identifier_roles_document() -> dict[str, object]:
    """Serializable RF-002 contract for manifests, docs, and policy embedding."""
    return {
        "artifact": "iuphar_rf002_identifier_roles",
        "biological_accuracy_accepted": False,
        "component_scope_policy": dict(COMPONENT_SCOPE_POLICY),
        "contract_version": RF002_CONTRACT_VERSION,
        "diagnostic_codes": dict(DIAGNOSTIC_CODES),
        "epic": RF002_EPIC,
        "identifier_roles": {
            key: dict(value) for key, value in IDENTIFIER_ROLES.items()
        },
        "issue": RF002_ISSUE,
        "legacy_matching_policy_version": LEGACY_MATCHING_POLICY_VERSION,
        "matching_policy_version": MATCHING_POLICY_VERSION,
        "profile_qualification": (
            "Profile envelopes and acceptance receipts must pin "
            "matching_policy_version to MATCHING_POLICY_VERSION. A pre-RF-002 "
            "receipt/profile (missing pin or legacy_matching_policy_version) is "
            "rejected by load_profile / validate_acceptance_receipt. RF-008 "
            "performs independent biological admission"
        ),
        "strict_primary_api": True,
    }


__all__ = [
    "COMPONENT_SCOPE_POLICY",
    "DIAGNOSTIC_CODES",
    "IDENTIFIER_ROLES",
    "LEGACY_MATCHING_POLICY_VERSION",
    "MATCHING_POLICY_VERSION",
    "RF002_CONTRACT_VERSION",
    "RF002_EPIC",
    "RF002_ISSUE",
    "identifier_roles_document",
]
