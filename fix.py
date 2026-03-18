with open("src/bioetl/infrastructure/quality/exemptions_registry.py", "r") as f:
    content = f.read()

new_content = content.replace("""    for registry_name, entries in sorted(registries.items()):
        if not isinstance(entries, dict):
            continue
        if registry_name in _CLASS_SYMBOL_REGISTRIES:
            for key in sorted(entries):
                if isinstance(key, str):
                    _validate_symbol_key_reference(
                        registry_name=registry_name,
                        key=key,
                        symbol_kind="class",
                        symbols_by_module=classes_by_module,
                        global_counts=class_counts,
                        errors=errors,
                    )
        elif registry_name in _FUNCTION_SYMBOL_REGISTRIES:
            for key in sorted(entries):
                if isinstance(key, str):
                    _validate_symbol_key_reference(
                        registry_name=registry_name,
                        key=key,
                        symbol_kind="function",
                        symbols_by_module=functions_by_module,
                        global_counts=function_counts,
                        errors=errors,
                    )""", """    for registry_name, entries in sorted(registries.items()):
        if not isinstance(entries, dict):
            continue
        _validate_registry_entries(
            registry_name,
            entries,
            classes_by_module,
            functions_by_module,
            class_counts,
            function_counts,
            errors,
        )""")

new_content += """

def _validate_registry_entries(
    registry_name: str,
    entries: dict[str, object],
    classes_by_module: dict[str, set[str]],
    functions_by_module: dict[str, set[str]],
    class_counts: dict[str, int],
    function_counts: dict[str, int],
    errors: list[str],
) -> None:
    if registry_name in _CLASS_SYMBOL_REGISTRIES:
        for key in sorted(entries):
            if isinstance(key, str):
                _validate_symbol_key_reference(
                    registry_name=registry_name,
                    key=key,
                    symbol_kind="class",
                    symbols_by_module=classes_by_module,
                    global_counts=class_counts,
                    errors=errors,
                )
    elif registry_name in _FUNCTION_SYMBOL_REGISTRIES:
        for key in sorted(entries):
            if isinstance(key, str):
                _validate_symbol_key_reference(
                    registry_name=registry_name,
                    key=key,
                    symbol_kind="function",
                    symbols_by_module=functions_by_module,
                    global_counts=function_counts,
                    errors=errors,
                )
"""

with open("src/bioetl/infrastructure/quality/exemptions_registry.py", "w") as f:
    f.write(new_content)
