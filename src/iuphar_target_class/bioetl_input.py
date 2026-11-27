"""Shared pure field projection for runtime classification and canonical export."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping

from iuphar_target_class.effective_policy import name_keyword_class
from iuphar_target_class.identifier_roles import (
    EC_EFFECTIVE_POLICIES,
    RANKED_CLASS_POLICIES,
    REVIEWED_CLASS_POLICY_VERSION,
    TRANSCRIPTION_FACTOR_POLICIES,
)
from iuphar_target_class.normalization import parse_ec_numbers
from iuphar_target_class.stage0.io import canonical_json_bytes

_TAXONOMY_ERROR = "taxonomy_id must be a positive integer"
_SOURCE_TAXA = {
    "Homo sapiens": "9606",
    "Mus musculus": "10090",
    "Rattus norvegicus": "10116",
}


_MISSING_MARKERS = frozenset({"n/a", "#n/a"})


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or text.casefold() in {"unknown", *_MISSING_MARKERS}:
        return None
    return text


def _tokens(value: object, *, allow_bracket_text: bool = False) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(
            part
            for item in value
            for part in _tokens(item, allow_bracket_text=allow_bracket_text)
        )
    text = _text(value)
    if text is None:
        return ()
    if text.startswith("["):
        try:
            loaded = json.loads(text)
        except json.JSONDecodeError:
            if not allow_bracket_text:
                raise
        else:
            if not isinstance(loaded, list):
                raise ValueError("expected a JSON identifier array")
            return _tokens(loaded, allow_bracket_text=allow_bracket_text)
    return tuple(part for raw in re.split(r"[|;]", text) if (part := _text(raw)))


def _taxon(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(_TAXONOMY_ERROR)
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise ValueError(_TAXONOMY_ERROR)
        value = int(value)
    text = str(value).strip()
    if not text.isascii() or not text.isdecimal() or text.startswith("0"):
        raise ValueError(_TAXONOMY_ERROR)
    return text


def plain_target_value(value: object) -> object:
    """Normalize nested business payloads for shared runtime/export digests.

    Nullable Silver schema fields materialize as explicit ``None``; runtime
    classifier inputs omit the same keys. Dropping null-valued mapping entries
    keeps ``source_business_data`` identical across both paths.
    """
    if isinstance(value, Mapping):
        return {
            key: plain_target_value(item)
            for key, item in value.items()
            if item is not None
        }
    if isinstance(value, (list, tuple)):
        return [plain_target_value(item) for item in value]
    return value


def target_gene_aliases(data: Mapping[str, object]) -> tuple[str, ...]:
    return _tokens(data.get("target_gene_synonyms"), allow_bracket_text=True)


def project_target_fields(
    data: Mapping[str, object], taxon: str | None
) -> dict[str, str | None]:
    """Project ChEMBL target fields onto the offline classification kernel.

    RF-002 (#13310): ``component_accessions`` are primary UniProt anchors;
    ``target_xref_uniprot_ids`` are split into proven equivalents (overlap with
    primary) and auxiliary xrefs. Only primary values fill ``uniprot`` so
    unknown auxiliary tokens cannot open empty exact-channels. A joined
    ``uniprot_accession`` is a primary anchor from the dependency join, not an
    auxiliary xref. All original business fields remain in
    ``source_business_data``.
    """
    primary = tuple(
        dict.fromkeys(
            (
                *_tokens(data.get("component_accessions")),
                *_tokens(data.get("uniprot_accession")),
            )
        )
    )
    xref = tuple(dict.fromkeys(_tokens(data.get("target_xref_uniprot_ids"))))
    primary_set = set(primary)
    proven = tuple(item for item in xref if item in primary_set)
    auxiliary = tuple(item for item in xref if item not in primary_set)
    synonyms = tuple(
        dict.fromkeys(
            (
                *_tokens(data.get("target_protein_synonyms"), allow_bracket_text=True),
                *target_gene_aliases(data),
            )
        )
    )
    projected = {
        "target_chembl_id": _text(data.get("target_id")),
        # ChEMBL identity is never passed as the kernel's explicit IUPHAR ID.
        "target_id": _text(data.get("iuphar_target_id")),
        "uniprot": "|".join(primary) or None,
        "uniprot_equivalent": "|".join(proven) or None,
        "uniprot_xref": "|".join(auxiliary) or None,
        "organism": taxon,
        "source_organism": _text(data.get("organism")),
        "name": _text(data.get("pref_name")),
        "synonyms": "|".join(synonyms) or None,
        "ec": "|".join(_tokens(data.get("target_ec_numbers"))) or None,
        "gene_symbol": _text(data.get("gene_symbol")),
        "gene_id": _text(data.get("gene_id")),
        "source_business_data": canonical_json_bytes(plain_target_value(data)).decode(
            "utf-8"
        ),
    }
    keyword_ids = "|".join(_tokens(data.get("controlled_keyword_ids"))) or None
    if keyword_ids is not None:
        projected["keywords"] = keyword_ids
    return projected


def target_input_eligibility(
    data: Mapping[str, object],
    species: frozenset[str],
    *,
    policy: str | None = None,
) -> tuple[str | None, str | None]:
    if data.get("target_type") != "SINGLE PROTEIN":
        return None, "unsupported_target_type"
    try:
        taxon = _taxon(data.get("taxonomy_id"))
    except ValueError:
        return None, "invalid_taxonomy_id"
    if policy == REVIEWED_CLASS_POLICY_VERSION:
        return taxon, _taxonomy_name_ineligibility(taxon, data.get("organism"))
    if taxon is not None and taxon not in species:
        if policy not in EC_EFFECTIVE_POLICIES:
            return taxon, "unsupported_taxon"
        reason = _taxonomy_name_ineligibility(taxon, data.get("organism"))
        if reason is not None:
            return taxon, reason
        ec = "|".join(_tokens(data.get("target_ec_numbers")))
        ranked = policy in RANKED_CLASS_POLICIES
        valid_ec = any(
            number.valid for number in parse_ec_numbers(ec, allow_preliminary=ranked)
        )
        if not valid_ec and not (
            ranked
            and name_keyword_class(
                _text(data.get("pref_name")),
                allow_transcription_factor=policy in TRANSCRIPTION_FACTOR_POLICIES,
            )
        ):
            return taxon, "unsupported_taxon"
    return taxon, _taxonomy_name_ineligibility(taxon, data.get("organism"))


def _taxonomy_name_ineligibility(taxon: str | None, organism: object) -> str | None:
    """Check name/taxonomy consistency after the species eligibility check."""
    source_taxon = _SOURCE_TAXA.get(_text(organism) or "")
    if source_taxon is None:
        return None
    if taxon is None:
        return "missing_taxonomy_for_known_organism"
    if taxon != source_taxon:
        return "taxonomy_name_conflict"
    return None


__all__ = ["plain_target_value", "project_target_fields", "target_input_eligibility"]
