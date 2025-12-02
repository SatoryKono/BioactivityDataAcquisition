import re
from typing import Any, Callable, Optional, TYPE_CHECKING

import pandas as pd
from bioetl.domain.transform.custom_types import (
    CUSTOM_FIELD_NORMALIZERS,
    normalize_array,
    normalize_record,
)

if TYPE_CHECKING:
    from bioetl.infrastructure.config.models import PipelineConfig

# Fields that must preserve case (chemical structures, etc.)
CASE_SENSITIVE_FIELDS = {
    "canonical_smiles",
    "smiles",
    "inchi",
    "inchi_key",
    "standard_inchi",
    "standard_inchi_key",
    "molecule_structures", # Serialized dict containing smiles
    "helm_notation",
    "variant_sequence",
    "target_components",
    "cross_references",
}

# Identifier patterns
DOI_REGEX = re.compile(r"^10\.\d{4,9}/\S+$", flags=re.IGNORECASE)
PUBMED_ID_REGEX = re.compile(r"^\d{1,9}$")
PUBCHEM_CID_REGEX = re.compile(r"^\d{1,9}$")
CHEMBL_ID_REGEX = re.compile(r"^CHEMBL\d+$", flags=re.IGNORECASE)
UNIPROT_ID_REGEX = re.compile(r"^[A-Z][0-9][A-Z0-9]{3}[0-9](?:-[0-9]+)?$")

# Fields that are IDs (should be UPPER case)
# Heuristic: ends with _id, or specific known ID fields
ID_FIELDS_EXACT = {
    "doi",
    "doi_chembl",
    "accession",
    "uo_units",
    "qudt_units",
    "toid",
    "bao_endpoint",
    "bao_format",
    "atc_classifications", # List of IDs
    "ligand_efficiency", # Keys are metrics, values are numbers.
    "assay_type", # B, F, A, etc.
}

def is_id_field(name: str) -> bool:
    if name in ID_FIELDS_EXACT:
        return True
    if name.endswith("_id") or name.endswith("_chembl_id") or name.startswith("id_"):
        return True
    return False


def normalize_doi(value: Any) -> str | None:
    """Normalize DOI value to canonical lowercase form without URL prefix."""
    if value is None:
        return None
    if isinstance(value, (dict, list, tuple)):
        return None

    val = str(value).strip().lower()
    if not val:
        return None

    # Drop URL prefixes and leading labels
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if val.startswith(prefix):
            val = val[len(prefix) :].strip()

    if len(val) > 255:
        return None

    return val if DOI_REGEX.match(val) else None


def _normalize_numeric_identifier(value: Any, pattern: re.Pattern[str]) -> int | None:
    if value is None:
        return None
    if isinstance(value, (list, dict, tuple)):
        return None

    val = str(value).strip()
    if not pattern.match(val):
        return None

    try:
        parsed = int(val)
    except ValueError:
        return None

    return parsed if parsed > 0 else None


def normalize_pubmed_id(value: Any) -> int | None:
    """Normalize PubMed identifier to positive integer."""
    return _normalize_numeric_identifier(value, PUBMED_ID_REGEX)


def normalize_pubchem_cid(value: Any) -> int | None:
    """Normalize PubChem CID to positive integer."""
    return _normalize_numeric_identifier(value, PUBCHEM_CID_REGEX)


def normalize_chembl_id(value: Any) -> str | None:
    """Normalize ChEMBL identifiers to uppercase form (CHEMBL123)."""
    if value is None:
        return None
    if isinstance(value, (list, dict, tuple)):
        return None

    val = str(value).strip().upper()
    return val if CHEMBL_ID_REGEX.match(val) else None


def normalize_uniprot_id(value: Any) -> str | None:
    """Normalize UniProt accession with optional isoform suffix."""
    if value is None:
        return None
    if isinstance(value, (list, dict, tuple)):
        return None

    val = str(value).strip().upper()
    if len(val) > 20:
        return None

    return val if UNIPROT_ID_REGEX.match(val) else None


def normalize_scalar(value: Any, mode: str = "default") -> Any:
    """
    Нормализует скалярное значение.
    
    Modes:
    - "default": trim + lower (str), round 3 (float)
    - "id": trim + upper (str)
    - "sensitive": trim only (str)
    """
    if value is None:
        return None

    # Safety check for lists/arrays to avoid "truth value of an array is ambiguous" in pd.isna
    if isinstance(value, (list, tuple, dict)):
        # Scalar normalizer should not receive collections, but if it does (wrong schema type),
        # we shouldn't crash.
        if not value:
            return None
        # Fallback: convert to string to process as scalar string
        # This handles cases where a field is defined as string but API returns a list
        return str(value)

    try:
        if pd.isna(value):
            return None
    except ValueError:
        # Probably an array/list that wasn't caught by isinstance check (e.g. numpy array)
        # Treat as non-NA if it raises ValueError (ambiguous truth value usually means it has elements)
        print(f"DEBUG: ValueError in normalize_scalar for value: {value} type: {type(value)}")
        pass

    # If we are here, it's either not NA, or it was an array (and we ignored it)
    
    if isinstance(value, float):
        # User requested: "double (3 знака после запятой)"
        return round(value, 3)
        
    if isinstance(value, int):
        return value

    if isinstance(value, str):
        val = value.strip()
        if not val:
            return None
            
        if mode == "id":
            return val.upper()
        elif mode == "sensitive":
            return val
        else: # default
            return val.lower()

    return value


def serialize_dict(
    value: dict[str, Any], 
    value_normalizer: Optional[Callable[[Any], Any]] = None
) -> Any:
    """
    Преобразует словарь в строку key:value|key:value.
    Пропускает вложенные списки и словари (глубина 1).
    """
    if not value:
        return pd.NA

    parts = []
    norm_func = value_normalizer if value_normalizer else (lambda x: x)

    # Sort keys for determinism
    for k in sorted(value.keys()):
        v = value[k]
        if v is None:
            continue
        if isinstance(v, (list, dict)):
            continue
        
        # Normalize value
        val_norm = norm_func(v)
        if val_norm is not pd.NA and val_norm is not None:
             parts.append(f"{k}:{val_norm}")
        
    if not parts:
        return pd.NA
        
    return "|".join(parts)


def serialize_list(
    value: list[Any],
    value_normalizer: Optional[Callable[[Any], Any]] = None
) -> Any:
    """
    Преобразует список в строку, соединяя элементы через |.
    Для списка словарей объединяет их сериализованные представления.
    """
    if not value:
        return pd.NA

    parts = []
    norm_func = value_normalizer if value_normalizer else (lambda x: x)

    # Check first element to decide strategy (heuristic for homogeneity)
    if len(value) > 0 and isinstance(value[0], dict):
        for item in value:
            if isinstance(item, dict):
                s = serialize_dict(item, value_normalizer=norm_func)
                if s is not pd.NA and s is not None:
                    parts.append(s)
    else:
        for item in value:
            if isinstance(item, (list, dict)):
                continue
            
            val_norm = norm_func(item)
            if val_norm is not pd.NA and val_norm is not None:
                parts.append(str(val_norm))
            
    if not parts:
        return pd.NA
        
    return "|".join(parts)


class NormalizerMixin:
    """
    Миксин для нормализации полей данных.
    
    Выполняет:
    - Сериализацию вложенных структур (list/dict -> str)
    - Нормализацию скалярных типов (float->round, str->trim/lower/upper)
    """

    # Type hint for self to indicate expectation of _config
    _config: Any

    def normalize_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Проходит по полям конфигурации и применяет нормализацию.
        """
        if not hasattr(self, "_config"):
            return df
            
        for field_cfg in self._config.fields:
            name = field_cfg["name"]
            dtype = field_cfg.get("data_type")
            
            if name not in df.columns:
                continue

            # Determine normalization mode
            mode = "default"
            if name in CASE_SENSITIVE_FIELDS:
                mode = "sensitive"
            elif is_id_field(name):
                mode = "id"

            # Create bound normalizer function for this field
            base_normalizer: Callable[[Any], Any]
            if name in CUSTOM_FIELD_NORMALIZERS:
                base_normalizer = CUSTOM_FIELD_NORMALIZERS[name]
            else:
                def _default_normalizer(val: Any) -> Any:
                    return normalize_scalar(val, mode=mode)

                base_normalizer = _default_normalizer

            def _apply_value(val: Any) -> Any:
                try:
                    return base_normalizer(val)
                except ValueError as exc:
                    raise ValueError(
                        f"Ошибка нормализации поля '{name}': {exc}"
                    ) from exc

            if dtype in ("array", "object"):
                # For nested structures, we pass the normalizer down
                def _serialize_wrapper(val: Any) -> Any:
                    try:
                        if val is None:
                            return pd.NA
                        if not isinstance(val, (list, dict, tuple)) and pd.isna(val):
                            return pd.NA
                    except ValueError:
                        pass

                    if isinstance(val, (list, tuple)):
                        try:
                            normalized_list = normalize_array(
                                list(val), item_normalizer=base_normalizer
                            )
                        except ValueError as exc:
                            raise ValueError(
                                f"Ошибка нормализации списка в поле '{name}': {exc}"
                            ) from exc
                        if normalized_list is None:
                            return pd.NA
                        return serialize_list(normalized_list)

                    if isinstance(val, dict):
                        try:
                            normalized_dict = normalize_record(
                                val, value_normalizer=base_normalizer
                            )
                        except ValueError as exc:
                            raise ValueError(
                                f"Ошибка нормализации записи в поле '{name}': {exc}"
                            ) from exc
                        if normalized_dict is None:
                            return pd.NA
                        return serialize_dict(normalized_dict)

                    res = _apply_value(val)
                    return str(res) if res is not pd.NA and res is not None else pd.NA

                df[name] = df[name].apply(_serialize_wrapper)
                df[name] = df[name].astype("string").replace({pd.NA: None})

            elif dtype in ("string", "integer", "number", "float", "boolean"):
                # For scalars, apply directly
                df[name] = df[name].apply(_apply_value)
            
        return df

    # Legacy alias for backward compatibility during refactor
    def normalize_nested_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.normalize_fields(df)
