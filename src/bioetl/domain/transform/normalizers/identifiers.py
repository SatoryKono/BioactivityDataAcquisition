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
        raise ValueError(
            f"Неверный формат DOI (должен начинаться с '10.'): '{value}'"
        )

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
        raise ValueError(
            f"Неверный PubMed ID (содержит нецифровые символы): '{value}'"
        )

    parsed = int(text)
    if parsed <= 0:
        raise ValueError("PubMed ID должен быть положительным числом")
    return parsed


def normalize_pcid(value: Any) -> int | None:
    """Normalize PubChem CID as positive integer."""
    if is_missing(value):
        return None

    if isinstance(value, float):
        if value.is_integer():
            value = int(value)
        else:
            msg = f"PubChem CID не является целым числом: '{value}'"
            raise ValueError(msg)

    if isinstance(value, int):
        if value <= 0:
            raise ValueError("PubChem CID должен быть положительным числом")
        return value

    text = str(value).strip().upper()
    if not text:
        return None

    if text.startswith("CID"):
        text = text[3:]
    elif text.startswith("PCID"):
        text = text[4:]

    if not text.isdigit():
        raise ValueError(f"Неверный PubChem CID: '{value}'")

    parsed = int(text)
    if parsed <= 0:
        raise ValueError("PubChem CID должен быть положительным числом")
    return parsed


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
        raise ValueError(
            f"Неверный BAO ID (ожидался формат BAO_<digits>): '{value}'"
        )

    return text


def normalize_bao_label(value: Any) -> str | None:
    """Normalize BioAssay Ontology Label. Trims whitespace."""
    if is_missing(value):
        return None

    if not isinstance(value, str):
        value = str(value)

    text = value.strip()
    return text if text else None


__all__ = [
    "normalize_doi",
    "normalize_chembl_id",
    "normalize_pmid",
    "normalize_pcid",
    "normalize_uniprot",
    "normalize_bao_id",
    "normalize_bao_label",
]
