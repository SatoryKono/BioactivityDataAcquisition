import re

with open('src/bioetl/infrastructure/quality/exemptions_registry.py', 'r') as f:
    content = f.read()

# Refactor validate_exemption_target_references to have lower cyclomatic complexity
new_content = content.replace('''
    for registry_name, entries in sorted(registries.items()):
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
                    )
''', '''
    for registry_name, entries in sorted(registries.items()):
        if not isinstance(entries, dict):
            continue
        _check_registry_symbols(registry_name, entries, classes_by_module, class_counts, functions_by_module, function_counts, errors)
''')

helper_func = '''
def _check_registry_symbols(
    registry_name: str,
    entries: dict[str, Any],
    classes_by_module: dict[str, set[str]],
    class_counts: Counter[str],
    functions_by_module: dict[str, set[str]],
    function_counts: Counter[str],
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
'''

new_content = new_content.replace('def validate_exemption_target_references(', helper_func + '\n\ndef validate_exemption_target_references(')

with open('src/bioetl/infrastructure/quality/exemptions_registry.py', 'w') as f:
    f.write(new_content)
