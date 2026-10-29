with open("src/bioetl/domain/normalization/identifiers.py", "r") as f:
    content = f.read()

import_pattern = "from __future__ import annotations"
new_import = "from __future__ import annotations\n\nfrom bioetl.domain.normalization.text import normalize_string"
content = content.replace(import_pattern, new_import)

old_check = """def normalize_ontology_id(value: str) -> str | None:
    \"\"\"Canonicalize ontology IDs with consistent prefix format.\"\"\"
    if value is None or not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return "" if value == "" else None"""

new_check = """def normalize_ontology_id(value: str) -> str | None:
    \"\"\"Canonicalize ontology IDs with consistent prefix format.\"\"\"
    if value is None or not isinstance(value, str):
        return None
    normalized = normalize_string(value)
    if normalized is None:
        return None"""

content = content.replace(old_check, new_check)


old_caloha_check1 = """        if canonical_prefix:
            if prefix_upper == "CALOHA":
                id_part_upper = id_part.upper()
                if id_part_upper.startswith("TS-"):
                    return id_part_upper
            return f"{canonical_prefix}{id_part}\""""

new_caloha_check1 = """        if canonical_prefix:
            if prefix_upper == "CALOHA":
                id_part_upper = id_part.upper()
                if id_part_upper.startswith("TS-"):
                    return id_part_upper
            return f"{canonical_prefix}{id_part}\""""

old_caloha_check2 = """        if canonical_prefix:
            if canonical_prefix == "TS-" and suffix.upper().startswith("TS-"):
                return suffix.upper()
            return f"{canonical_prefix}{suffix}\""""

new_caloha_check2 = """        if canonical_prefix:
            if prefix_upper == "CALOHA" and suffix.upper().startswith("TS-"):
                return suffix.upper()
            return f"{canonical_prefix}{suffix}\""""

content = content.replace(old_caloha_check2, new_caloha_check2)

old_fast_path = """    # 1. Very fast path: already canonical or correct prefix format
    if upper_val.startswith(_CANONICAL_PREFIXES):
        if normalized.startswith(_CANONICAL_PREFIXES):
            return normalized
        for canonical in _CANONICAL_PREFIXES:
            if upper_val.startswith(canonical):
                return canonical + normalized[len(canonical) :]"""

new_fast_path = """    # 1. Very fast path: already canonical or correct prefix format
    if upper_val.startswith(_CANONICAL_PREFIXES):
        for canonical in _CANONICAL_PREFIXES:
            if upper_val.startswith(canonical):
                suffix = normalized[len(canonical) :]
                # Special case for CALOHA already starting with TS-
                if canonical == ONTOLOGY_PREFIXES["CALOHA"] and suffix.upper().startswith("TS-"):
                    return suffix.upper()
                return canonical + suffix"""

content = content.replace(old_fast_path, new_fast_path)

with open("src/bioetl/domain/normalization/identifiers.py", "w") as f:
    f.write(content)
