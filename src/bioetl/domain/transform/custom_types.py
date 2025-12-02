"""Utility normalizers for domain-specific identifiers and records."""
from __future__ import annotations

import json
import re
from typing import Any, Callable, Iterable, Mapping, MutableMapping

import pandas as pd

# --- Constants & Regex Patterns ---

DOI_REGEX = re.compile(r"^10\.\d{4,9}/\S+$", flags=re.IGNORECASE)
CHEMBL_ID_REGEX = re.compile(r"^CHEMBL\d+$", flags=re.IGNORECASE)
# PubMed IDs are integers, usually 1-8 digits. We allow up to 9 safely.
PUBMED_ID_REGEX = re.compile(r"^\d{1,10}$") 
PUBCHEM_CID_REGEX = re.compile(r"^\d{1,10}$")
BAO_ID_REGEX = re.compile(r"^BAO_\d+$", flags=re.IGNORECASE)

# UniProt: 6 or 10 alphanumeric characters.
# More strict patterns from UniProt documentation:
# P12345 (6 chars), A0A0P7VRU5 (10 chars)
# Simplest valid pattern according to task: 6 or 10 alphanumeric chars.
# We will use the patterns previously defined but expose a combined one.
_UNIPROT_PATTERN_SHORT = r"[A-NR-Z][0-9][A-Z][A-Z0-9]{2}[0-9]"
_UNIPROT_PATTERN_PQ = r"[OPQ][0-9][A-Z0-9]{3}[0-9]"
_UNIPROT_PATTERN_LONG = r"[A-NR-Z][0-9][A-Z][A-Z0-9]{2}[0-9][A-Z0-9]{3}[0-9]"
# Combined strict regex
UNIPROT_ID_REGEX = re.compile(
    f"^(?:{_UNIPROT_PATTERN_PQ}|{_UNIPROT_PATTERN_SHORT}|{_UNIPROT_PATTERN_LONG})$",
    flags=re.IGNORECASE
)


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (ValueError, TypeError):
        return False


def normalize_doi(value: Any) -> str | None:
    """
    Normalize DOI to lowercase canonical form without prefixes.
    
    Format: 10.xxxx/xxxx
    """
    if _is_missing(value):
        return None
    if not isinstance(value, str):
        # If it's not a string but convertable, we try to convert?
        # Task says: "привести строку...". If not str, maybe raise?
        # Existing code raised ValueError.
        raise ValueError(f"DOI должен быть строкой, получено: {type(value)}")

    doi = value.strip().lower()
    # Remove common prefixes
    doi = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", doi)
    if doi.startswith("doi:"):
        doi = doi[4:]
    
    if not doi:
        return None

    # Validate format
    if not doi.startswith("10."):
         raise ValueError(f"Неверный формат DOI (должен начинаться с '10.'): '{value}'")

    # Additional regex validation
    if not DOI_REGEX.match(doi):
        # Should have matched startswith 10. already, but this checks structure
        # But let's follow the task logic: "validate format correct".
        # The regex ^10\.\d{4,9}/\S+$ is good.
        raise ValueError(f"Неверный формат DOI: '{value}'")
        
    return doi


def normalize_chembl_id(value: Any) -> str | None:
    """
    Normalize ChEMBL ID ensuring prefix and numeric body.
    
    Format: CHEMBL<digits> (upper case)
    """
    if _is_missing(value):
        return None
    
    text = str(value).strip().upper()
    if not text:
        return None

    # Auto-fix if digits only
    if text.isdigit():
        text = f"CHEMBL{text}"
    
    # Auto-fix if digits only
    if text.isdigit():
        text = f"CHEMBL{text}"
    
    match = re.fullmatch(r"CHEMBL(\d+)", text)
    if not match:
        raise ValueError(f"Неверный ChEMBL ID (ожидался формат CHEMBL<digits>): '{value}'")
        
    return text


def normalize_pmid(value: Any) -> int | None:
    """
    Normalize PubMed ID as positive integer.
    """
    if _is_missing(value):
        return None

    # Handle float (e.g. from pandas/numpy)
    if isinstance(value, float):
        if value.is_integer():
            value = int(value)
        else:
             raise ValueError(f"PubMed ID не является целым числом: '{value}'")

    if isinstance(value, int):
        if value <= 0:
            raise ValueError("PubMed ID должен быть положительным числом")
        return value

    # Handle string
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
    """
    Normalize PubChem CID as positive integer.
    """
    if _is_missing(value):
        return None
    
    # Handle float
    if isinstance(value, float):
        if value.is_integer():
            value = int(value)
        else:
            raise ValueError(f"PubChem CID не является целым числом: '{value}'")

    if isinstance(value, int):
         if value <= 0:
            raise ValueError("PubChem CID должен быть положительным числом")
         return value

    text = str(value).strip().upper()
    if not text:
        return None
    
    # Sometimes people write "CID123" or "PCID123"
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
    """
    Normalize UniProt accession with strict format validation.
    """
    if _is_missing(value):
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
    if _is_missing(value):
        return None
        
    text = str(value).strip().upper()
    if not text:
        return None

    if not BAO_ID_REGEX.match(text):
         raise ValueError(f"Неверный BAO ID (ожидался формат BAO_<digits>): '{value}'")
         
    return text


def normalize_bao_label(value: Any) -> str | None:
    """
    Normalize BioAssay Ontology Label.
    
    Trims whitespace and ensures non-empty.
    """
    if _is_missing(value):
        return None
    
    if not isinstance(value, str):
        value = str(value)
        
    text = value.strip()
    if not text:
        return None
        
    return text


def normalize_array(
    value: Any, *, item_normalizer: Callable[[Any], Any] | None = None
) -> list[Any] | None:
    """
    Normalize array-like value and its elements.
    """
    if _is_missing(value):
        return None

    # Try to parse string representation of list
    if isinstance(value, str):
        value = value.strip()
        # Basic JSON check
        if value.startswith("[") and value.endswith("]"):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass # Fallback to single string or other split logic if needed
        else:
            # Delimited string? User mentioned: 'a; b; c' -> ['a', 'b', 'c'] optional
            if ";" in value:
                value = [x.strip() for x in value.split(";")]
            elif "," in value and " " not in value: # Very basic heuristic, risky
                 # Let's treat simple string as single element list unless it looks like a list
                 pass

    if isinstance(value, (list, tuple)):
        items: Iterable[Any] = value
    else:
        # Single value -> list
        items = [value]

    normalized: list[Any] = []
    for idx, item in enumerate(items):
        if _is_missing(item):
            continue
        
        norm_item = None
        try:
            if isinstance(item, dict):
                # Treat as record, use item_normalizer for values if available
                norm_item = normalize_record(item, value_normalizer=item_normalizer)
            elif item_normalizer:
                norm_item = item_normalizer(item)
            else:
                # Default: stringify? Task: "привести каждый к строковому типу (например, str(element))"
                norm_item = str(item)
        except ValueError as exc:
             raise ValueError(
                f"Ошибка нормализации элемента массива на позиции {idx}: {exc}"
            ) from exc
            
        if not _is_missing(norm_item):
            normalized.append(norm_item)

    # Task: "Если пустое или null, вернуть пустой список [] или None"
    # "Цель – в итоге хранить списковые поля как List[str]"
    # Let's return [] if empty list, None if original was None (handled at top)
    if not normalized:
         # If original was a list but all items filtered out? 
         return []
         
    return normalized


def normalize_record(
    value: Any, *, value_normalizer: Callable[[Any], Any] | None = None
) -> MutableMapping[str, Any] | None:
    """
    Normalize mapping/dict values using provided normalizer.
    """
    if _is_missing(value):
        return None
        
    # Try parsing string JSON
    if isinstance(value, str):
        value = value.strip()
        if value.startswith("{") and value.endswith("}"):
             try:
                value = json.loads(value)
             except json.JSONDecodeError as e:
                 raise ValueError(f"Некорректный JSON для записи: {e}")
    
    if not isinstance(value, Mapping):
        raise ValueError(
            f"Ожидался словарь для object-поля, получено {type(value).__name__}"
        )

    normalized: MutableMapping[str, Any] = {}
    for key, item in value.items():
        # Keys should be strings
        str_key = str(key)
        
        if _is_missing(item):
            continue
            
        try:
            if value_normalizer:
                normalized_value = value_normalizer(item)
            else:
                # If no normalizer, keep as is or simple types?
                # Task: "значения оставить как есть или тоже валидацией привести к простым типам"
                normalized_value = item
        except ValueError as exc:
            raise ValueError(
                f"Некорректное значение в поле '{str_key}': {exc}"
            ) from exc
            
        if not _is_missing(normalized_value):
            normalized[str_key] = normalized_value

    return normalized or None


CUSTOM_FIELD_NORMALIZERS: dict[str, Callable[[Any], Any]] = {
    "doi": normalize_doi,
    "doi_chembl": normalize_doi,
    "doi_clean": normalize_doi,
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
    "accession": normalize_uniprot,
    "bao_endpoint": normalize_bao_id,
    "bao_format": normalize_bao_id,
    "bao_label": normalize_bao_label,
}


__all__ = [
    "CUSTOM_FIELD_NORMALIZERS",
    "DOI_REGEX",
    "CHEMBL_ID_REGEX",
    "PUBMED_ID_REGEX",
    "PUBCHEM_CID_REGEX",
    "UNIPROT_ID_REGEX",
    "BAO_ID_REGEX",
    "normalize_array",
    "normalize_bao_id",
    "normalize_bao_label",
    "normalize_chembl_id",
    "normalize_doi",
    "normalize_pcid",
    "normalize_pmid",
    "normalize_record",
    "normalize_uniprot",
]
