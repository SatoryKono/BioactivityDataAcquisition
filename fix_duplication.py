with open('src/bioetl/application/composite/column_orderer.py', 'r') as f:
    content = f.read()

# Replace the duplicated implementation with a direct import
import_statement = "from bioetl.application.composite.column_service import collect_explicit_group_columns\n"
new_content = content.replace(
    """def collect_explicit_group_columns(
    available: set[str],
    group: ColumnGroupConfig,
    sort_fn: _SortFn,
    extract_field_fn: Callable[[str], str],
    resolve_aliases_fn: Callable[[str], set[str]],
) -> tuple[list[str], set[str]]:
    \"\"\"Collect explicit field matches for a YAML group in declared field order.\"\"\"
    ordered: list[str] = []
    used: set[str] = set()

    # Pre-compute extracted fields to transform O(N*M) into O(N)
    extracted_fields = {col: extract_field_fn(col) for col in available}

    for field_name in group.fields:
        field_matches: list[str] = []
        aliases = resolve_aliases_fn(field_name)
        for column in available:
            if column in used:
                continue
            extracted = extracted_fields[column]
            if extracted in aliases or column in aliases:
                field_matches.append(column)
                used.add(column)
        ordered.extend(sort_fn(field_matches, group.provider_order))

    return ordered, used""",
    import_statement
)

with open('src/bioetl/application/composite/column_orderer.py', 'w') as f:
    f.write(new_content)
