with open("src/bioetl/domain/normalization/identifiers.py", "r") as f:
    content = f.read()

old_check = """def normalize_ontology_id(value: str) -> str | None:
    \"\"\"Canonicalize ontology IDs with consistent prefix format.\"\"\"
    if value is None or not isinstance(value, str):
        return None
    normalized = normalize_string(value)
    if normalized is None:
        return None"""

new_check = """def normalize_ontology_id(value: str) -> str | None:
    \"\"\"Canonicalize ontology IDs with consistent prefix format.\"\"\"
    if value is None or not isinstance(value, str):
        return None
    normalized = normalize_string(value)
    if normalized is None:
        return "" if value == "" else None"""

content = content.replace(old_check, new_check)

with open("src/bioetl/domain/normalization/identifiers.py", "w") as f:
    f.write(content)
