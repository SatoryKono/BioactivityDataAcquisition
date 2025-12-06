"""Normalizers for domain-specific identifiers (DOI, ChEMBL, PMID, etc.)."""

from __future__ import annotations

import re
from typing import Any

from bioetl.domain.transform.normalizers.base import (
    BAO_ID_REGEX,
    DOI_REGEX,
    UNIPROT_ID_REGEX,
    is_missing,
)


def normalize_doi(value: Any) -> str | None:
    """
    Normalize DOI to lowercase canonical form without prefixes.

    Format: 10.xxxx/xxxx
    """
    if is_missing(value):
        return None
    if not isinstance(value, str):
        raise ValueError(f"DOI должен быть строкой, получено: {type(value)}")

    doi = value.strip().lower()
    doi = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", doi)
    if doi.startswith("doi:"):
        doi = doi[4:]

    if not doi:
        return None

    if not doi.startswith("10."):
        raise ValueError(f"Неверный формат DOI (должен начинаться с '10.'): '{value}'")

    if not DOI_REGEX.match(doi):
        raise ValueError(f"Неверный формат DOI: '{value}'")

    return doi


def normalize_chembl_id(value: Any) -> str | None:
    """
    Normalize ChEMBL ID ensuring prefix and numeric body.

    Format: CHEMBL<digits> (upper case)
    """
    if is_missing(value):
        return None

    text = str(value).strip().upper()
    if not text:
        return None

    if text.isdigit():
        text = f"CHEMBL{text}"

    match = re.fullmatch(r"CHEMBL(\d+)", text)
    if not match:
        raise ValueError(
            f"Неверный ChEMBL ID (ожидался формат CHEMBL<digits>): '{value}'"
        )

    return text


def normalize_pmid(value: Any) -> int | None:
    """Normalize PubMed ID as positive integer."""
    if is_missing(value):
        return None

    if isinstance(value, float):
        if value.is_integer():
            value = int(value)
        else:
            raise ValueError(f"PubMed ID не является целым числом: '{value}'")

    if isinstance(value, int):
        if value <= 0:
            raise ValueError("PubMed ID должен быть положительным числом")
        return value

    text = str(value).strip()
    if not text:
        return None

    if not text.isdigit():
        raise ValueError(f"Неверный PubMed ID (содержит нецифровые символы): '{value}'")

    parsed = int(text)
    if parsed <= 0:
        raise ValueError("PubMed ID должен быть положительным числом")
    return parsed


def normalize_pcid(value: Any) -> int | None:
    """Normalize PubChem CID as positive integer."""
    return _parse_positive_int_with_prefixes(
        value,
        field_name="PubChem CID",
        prefixes=("CID", "PCID"),
    )


def normalize_uniprot(value: Any) -> str | None:
    """Normalize UniProt accession with strict format validation."""
    if is_missing(value):
        return None
    if not isinstance(value, str):
        raise ValueError("UniProt ID должен быть строкой")

    accession = value.strip().upper()
    if not accession:
        return None

    if not UNIPROT_ID_REGEX.match(accession):
        raise ValueError(f"Неверный UniProt ID: '{value}'")
    return accession


def normalize_bao_id(value: Any) -> str | None:
    """
    Normalize BioAssay Ontology ID.

    Format: BAO_<digits>
    """
    if is_missing(value):
        return None

    text = str(value).strip().upper()
    if not text:
        return None

    if not BAO_ID_REGEX.match(text):
        raise ValueError(f"Неверный BAO ID (ожидался формат BAO_<digits>): '{value}'")

    return text


def normalize_bao_label(value: Any) -> str | None:
    """Normalize BioAssay Ontology Label. Trims whitespace."""
    if is_missing(value):
        return None

    if not isinstance(value, str):
        value = str(value)

    text = value.strip()
    return text if text else None


def _parse_positive_int_with_prefixes(
    value: Any, *, field_name: str, prefixes: tuple[str, ...]
) -> int | None:
    if is_missing(value):
        return None

    numeric = _coerce_positive_int(value, field_name)
    if numeric is not None:
        return numeric

    text = str(value).strip().upper()
    if not text:
        return None

    stripped = _strip_prefix(text, prefixes)
    if not stripped.isdigit():
        raise ValueError(f"Неверный {field_name}: '{value}'")

    parsed = int(stripped)
    _ensure_positive(parsed, field_name)
    return parsed


def _coerce_positive_int(value: Any, field_name: str) -> int | None:
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError(f"{field_name} не является целым числом: '{value}'")
        value = int(value)

    if isinstance(value, int):
        _ensure_positive(value, field_name)
        return value

    return None


def _strip_prefix(text: str, prefixes: tuple[str, ...]) -> str:
    for prefix in prefixes:
        if text.startswith(prefix):
            return text[len(prefix) :]
    return text


def _ensure_positive(value: int, field_name: str) -> None:
    if value <= 0:
        raise ValueError(f"{field_name} должен быть положительным числом")


__all__ = [
    "normalize_doi",
    "normalize_chembl_id",
    "normalize_pmid",
    "normalize_pcid",
    "normalize_uniprot",
    "normalize_bao_id",
    "normalize_bao_label",
]
