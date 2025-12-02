"""Utility normalizers for domain-specific identifiers and records."""
from __future__ import annotations

import re
from typing import Any, Callable, Iterable, Mapping, MutableMapping

import pandas as pd


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (ValueError, TypeError):
        return False


def normalize_doi(value: Any) -> str | None:
    """Normalize DOI to lowercase canonical form without prefixes."""
    if _is_missing(value):
        return None
    if not isinstance(value, str):
        raise ValueError("DOI должен быть строкой")

    doi = value.strip().lower()
    doi = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", doi)
    if doi.startswith("doi:"):
        doi = doi[4:]
    if not doi:
        return None
    if not re.fullmatch(r"10\.\d{4,9}/.+", doi):
        raise ValueError(f"Неверный формат DOI: '{value}'")
    return doi


def normalize_chembl_id(value: Any) -> str | None:
    """Normalize ChEMBL ID ensuring prefix and numeric body."""
    if _is_missing(value):
        return None
    text = str(value).strip().upper()
    if not text:
        return None
    match = re.fullmatch(r"(?:CHEMBL)?(\d+)", text)
    if not match:
        raise ValueError(f"Неверный ChEMBL ID: '{value}'")
    return f"CHEMBL{match.group(1)}"


def normalize_pmid(value: Any) -> str | None:
    """Normalize PubMed ID as numeric string."""
    if _is_missing(value):
        return None
    if isinstance(value, int):
        if value <= 0:
            raise ValueError("PubMed ID должен быть положительным числом")
        return str(value)
    text = str(value).strip()
    if not text:
        return None
    if not text.isdigit():
        raise ValueError(f"Неверный PubMed ID: '{value}'")
    return text


def normalize_pcid(value: Any) -> str | None:
    """Normalize PubChem CID as numeric string."""
    if _is_missing(value):
        return None
    text = str(value).strip().upper()
    if not text:
        return None
    if text.startswith("CID"):
        text = text[3:]
    if text.startswith("PCID"):
        text = text[4:]
    if not text.isdigit():
        raise ValueError(f"Неверный PubChem CID: '{value}'")
    return text


def normalize_uniprot(value: Any) -> str | None:
    """Normalize UniProt accession with strict format validation."""
    if _is_missing(value):
        return None
    if not isinstance(value, str):
        raise ValueError("UniProt ID должен быть строкой")
    accession = value.strip().upper()
    if not accession:
        return None

    pattern_short = r"[A-NR-Z][0-9][A-Z][A-Z0-9]{2}[0-9]"
    pattern_pq = r"[OPQ][0-9][A-Z0-9]{3}[0-9]"
    pattern_long = r"[A-NR-Z][0-9][A-Z][A-Z0-9]{5}[0-9]"
    if not re.fullmatch(f"(?:{pattern_pq}|{pattern_short}|{pattern_long})", accession):
        raise ValueError(f"Неверный UniProt ID: '{value}'")
    return accession


def normalize_array(
    value: Any, *, item_normalizer: Callable[[Any], Any] | None = None
) -> list[Any] | None:
    """Normalize array-like value and its elements."""
    if _is_missing(value):
        return None
    if not isinstance(value, (list, tuple)):
        raise ValueError(
            f"Ожидался список или кортеж для массива, получено {type(value).__name__}"
        )

    normalized: list[Any] = []
    for idx, item in enumerate(value):
        if _is_missing(item):
            continue
        if isinstance(item, dict):
            try:
                normalized_item = normalize_record(item, value_normalizer=item_normalizer)
            except ValueError as exc:
                raise ValueError(
                    f"Некорректный элемент словаря в массиве на позиции {idx}: {exc}"
                ) from exc
        else:
            try:
                normalized_item = item_normalizer(item) if item_normalizer else item
            except ValueError as exc:
                raise ValueError(
                    f"Некорректный элемент массива на позиции {idx}: {exc}"
                ) from exc
        if not _is_missing(normalized_item):
            normalized.append(normalized_item)

    return normalized or None


def normalize_record(
    value: Any, *, value_normalizer: Callable[[Any], Any] | None = None
) -> MutableMapping[str, Any] | None:
    """Normalize mapping/dict values using provided normalizer."""
    if _is_missing(value):
        return None
    if not isinstance(value, Mapping):
        raise ValueError(
            f"Ожидался словарь для object-поля, получено {type(value).__name__}"
        )

    normalized: MutableMapping[str, Any] = {}
    for key, item in value.items():
        if _is_missing(item):
            continue
        try:
            normalized_value = value_normalizer(item) if value_normalizer else item
        except ValueError as exc:
            raise ValueError(
                f"Некорректное значение в поле '{key}': {exc}"
            ) from exc
        if not _is_missing(normalized_value):
            normalized[key] = normalized_value

    return normalized or None


CUSTOM_FIELD_NORMALIZERS: dict[str, Callable[[Any], Any]] = {
    "doi": normalize_doi,
    "doi_chembl": normalize_doi,
    "document_chembl_id": normalize_chembl_id,
    "assay_chembl_id": normalize_chembl_id,
    "molecule_chembl_id": normalize_chembl_id,
    "target_chembl_id": normalize_chembl_id,
    "pubmed_id": normalize_pmid,
    "pmid": normalize_pmid,
    "pcid": normalize_pcid,
    "pubchem_cid": normalize_pcid,
    "uniprot_accession": normalize_uniprot,
    "uniprot_id": normalize_uniprot,
}


__all__ = [
    "CUSTOM_FIELD_NORMALIZERS",
    "normalize_array",
    "normalize_chembl_id",
    "normalize_doi",
    "normalize_pcid",
    "normalize_pmid",
    "normalize_record",
    "normalize_uniprot",
]
