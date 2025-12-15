import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Rule 5.4.1: Advanced Salt Rotation
def get_salt(version: str = "current") -> str:
    """
    Retrieves the salt for PII hashing.
    In a real implementation, this would fetch from Secrets Manager.
    """
    if version == "current":
        return os.environ.get("BIOETL_SALT_CURRENT", "default_salt_current")
    elif version == "next":
        return os.environ.get("BIOETL_SALT_NEXT", "default_salt_next")
    raise ValueError(f"Unknown salt version: {version}")

def hash_pii(value: str, salt_version: str = "current") -> str:
    """
    Hashes a PII value using SHA256(lowercase(value) + SALT).
    Rule 5.4: PII fields MUST be salted.
    """
    salt = get_salt(salt_version)
    normalized_value = value.lower().strip()
    return hashlib.sha256((normalized_value + salt).encode("utf-8")).hexdigest()

def canonical_json_dumps(record: dict[str, Any]) -> str:
    """
    Rule 2.8: Canonical JSON for Content Hash.
    """
    # Note: Deep float rounding and normalization should be applied before this step
    # or implemented here recursively.
    return json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=True)

def generate_content_hash(provider: str, record: dict[str, Any]) -> str:
    """
    Rule 2.8: Entity ID generation.
    sha256(provider + canonical_json_dumps(record))
    """
    canonical_str = canonical_json_dumps(record)
    return hashlib.sha256((provider + canonical_str).encode("utf-8")).hexdigest()
