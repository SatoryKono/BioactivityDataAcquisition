"""
Модуль для вычисления канонических хешей (v1_blake2b_256).
"""
import hashlib
import json
import unicodedata
from typing import Any, Iterable
from decimal import Decimal


def normalize_unicode(text: str) -> str:
    """
    Нормализует строку в форму NFC.
    """
    return unicodedata.normalize("NFC", text)


def format_float(value: float | Decimal) -> str:
    """
    Форматирует число с плавающей точкой по спецификации: %.15g.
    """
    # Decimal is treated as float for canonicalization purposes per spec
    # to avoid discrepancies between float and Decimal types in source
    val = float(value)
    
    if val == float('inf') or val == float('-inf') or val != val:  # NaN
        raise ValueError(f"Invalid float value for hashing: {value}")
        
    # %.15g formatting
    return "%.15g" % val


def _prepare_value_for_canonical_json(value: Any) -> Any:
    """
    Рекурсивно подготавливает значение для канонической сериализации.
    
    Rules:
    - None -> None (will be null in JSON)
    - bool -> bool (true/false)
    - float/Decimal -> formatted string (%.15g) to ensure stability
      Note: We convert to string here because standard json dump might produce different
      representations for floats across platforms/versions if left as float.
      However, standard JSON serializers might quote the string. 
      The spec says "float formatting %.15g".
      If we return a string here, json.dumps will quote it. 
      If the requirement is to have a NUMBER in JSON but formatted specifically,
      we have to be careful.
      
      Re-reading spec: "canonical JSON serialization... float formatting %.15g".
      Usually this means the representation in the JSON string should be that format.
      If we use standard json.dumps, we can't easily control float formatting without
      subclassing JSONEncoder.
      
      Let's use a custom recursive serializer that produces the string directly,
      or simpler: Pre-process the dict replacing floats with a special wrapper?
      No, easier to just implement a custom serializer that yields the canonical string
      to ensure exact control over sorting and formatting.
    """
    # This helper is not actually enough if we want exact control over the output string
    # (e.g. no spaces after colons).
    # It is safer to write a full recursive serializer that returns the string.
    pass


def canonical_json_from_record(
    record: dict[str, Any] | list[Any], 
    ordered_keys: Iterable[str] | None = None
) -> str:
    """
    Сериализует запись в канонический JSON (v1).

    Спецификация:
    - UTF-8 (result is string, but implied encoding)
    - ensure_ascii=False
    - Keys sorted (recursively)
    - Arrays preserve order
    - No extra whitespace (separators=(',', ':'))
    - Floats formatted as %.15g
    - Unicode: NFC
    - Missing fields: null (if explicit key list provided and key missing)
    """
    
    # If ordered_keys is provided, we are likely processing the root object 
    # or a specific subset of keys (like for business key).
    if ordered_keys is not None and isinstance(record, dict):
        # Construct a new dict with explicit keys, filling missing with None
        # Note: Spec says "Отсутствующие поля ... сериализоваться как null"
        processed_record = {
            k: record.get(k) for k in ordered_keys
        }
        return _serialize_canonical(processed_record)
    
    return _serialize_canonical(record)


def _serialize_canonical(obj: Any) -> str:
    """
    Рекурсивная функция сериализации в строку.
    """
    if obj is None:
        return "null"
    
    if isinstance(obj, bool):
        return "true" if obj else "false"
    
    if isinstance(obj, (int, float, Decimal)):
        if isinstance(obj, bool): # Python bools are ints
            return "true" if obj else "false"
        if isinstance(obj, int) and not isinstance(obj, bool):
             return str(obj)
        # Float/Decimal
        return format_float(obj)
        
    if isinstance(obj, str):
        # Normalize NFC
        norm_str = normalize_unicode(obj)
        # JSON escape. json.dumps adds quotes and escapes.
        # ensure_ascii=False allows non-ascii chars.
        return json.dumps(norm_str, ensure_ascii=False)
        
    if isinstance(obj, (list, tuple)):
        # Preserve order
        items = [_serialize_canonical(item) for item in obj]
        return "[" + ",".join(items) + "]"
        
    if isinstance(obj, dict):
        # Sort keys
        sorted_keys = sorted(obj.keys())
        items = []
        for k in sorted_keys:
            # Keys must be strings for JSON
            if not isinstance(k, str):
                 raise TypeError(f"Dict keys must be strings, got {type(k)}")
            
            # Serialize key (quoted) and value
            # key is string, so standard json dump is fine (with NFC)
            key_str = json.dumps(normalize_unicode(k), ensure_ascii=False)
            val_str = _serialize_canonical(obj[k])
            items.append(f"{key_str}:{val_str}")
            
        return "{" + ",".join(items) + "}"
        
    raise TypeError(f"Type {type(obj)} not supported for canonical serialization")


def blake2b_hash_hex(data_bytes: bytes, digest_size: int = 32) -> str:
    """
    Вычисляет BLAKE2b хеш.
    
    Args:
        data_bytes: Входные данные в bytes.
        digest_size: Размер дайджеста в байтах (default 32).
        
    Returns:
        Hex строка (lowercase).
    """
    return hashlib.blake2b(data_bytes, digest_size=digest_size).hexdigest()


def compute_hash_business_key(
    record: dict[str, Any], 
    business_key_fields: list[str]
) -> str:
    """
    Вычисляет хеш бизнес-ключа.
    
    Использует canonical JSON массива значений полей в заданном порядке.
    Пример: ["val1", "val2"] -> hash
    """
    # Extract values in order
    values = []
    for field in business_key_fields:
        values.append(record.get(field))
        
    # Serialize list of values
    serialized = _serialize_canonical(values)
    
    # Hash
    return blake2b_hash_hex(serialized.encode("utf-8"))


def compute_hash_row(
    record: dict[str, Any], 
    include_hash_business_key: bool = True
) -> str:
    """
    Вычисляет хеш всей строки.
    
    Если include_hash_business_key=True, предполагается, что поле 'hash_business_key'
    уже присутствует в записи (или должно быть включено).
    
    Спецификация: canonical JSON всего объекта.
    """
    # We pass record directly. _serialize_canonical sorts keys.
    # If we need to exclude something, we should copy/filter.
    # But spec implies hashing the full record as it exists at this stage.
    
    # Note: If hash_business_key is missing but requested to be included, 
    # it effectively treats it as missing (null) or just hashes what's there?
    # Usually hash_row is computed AFTER hash_business_key is added.
    # So we just hash the record.
    
    serialized = _serialize_canonical(record)
    return blake2b_hash_hex(serialized.encode("utf-8"))

