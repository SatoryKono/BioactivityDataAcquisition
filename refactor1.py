def process_naming_audit():
    with open('scripts/engineering/qa/naming_audit.py', 'r', encoding='utf-8') as f:
        text = f.read()

    # 1. Replace families
    text = text.replace('    "pubchemmolecule": "pubchem:molecule",', 'FAMILY_PUBCHEM = "pubchem:molecule"\nFAMILY_UNIPROT = "uniprot:target"\nFAMILY_CHEMBL = "chembl:publication"\n\n_EXPLICIT_NAME_FAMILIES = {\n    "pubchemmolecule": FAMILY_PUBCHEM,')
    text = text.replace('"pubchem:molecule"', 'FAMILY_PUBCHEM')
    text = text.replace('"uniprot:target"', 'FAMILY_UNIPROT')
    text = text.replace('"chembl:publication"', 'FAMILY_CHEMBL')
    # Since we replaced the constant definitions too, let's fix them:
    text = text.replace('FAMILY_PUBCHEM = FAMILY_PUBCHEM', 'FAMILY_PUBCHEM = "pubchem:molecule"')
    text = text.replace('FAMILY_UNIPROT = FAMILY_UNIPROT', 'FAMILY_UNIPROT = "uniprot:target"')
    text = text.replace('FAMILY_CHEMBL = FAMILY_CHEMBL', 'FAMILY_CHEMBL = "chembl:publication"')

    # 2. Replace docs prefix
    text = text.replace('if normalized.startswith("docs/"):', 'DOCS_PREFIX = "docs/"\n    if normalized.startswith(DOCS_PREFIX):')
    text = text.replace('normalized.removeprefix("docs/")', 'normalized.removeprefix(DOCS_PREFIX)')

    # 3. Refactor function
    func_old = '''def _iter_class_symbol_surfaces(src_path: Path) -> Iterator[SymbolSurface]:
    """Discover relevant class surfaces from code."""
    for py_file, tree in _iter_python_modules_with_trees(src_path):
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if node.name.startswith("_"):
                continue
            if _is_support_surface(node.name):
                continue
            kind = _class_surface_kind(py_file, node.name)
            if kind is None:
                continue
            semantic_family = _resolve_semantic_family(
                node.name
            ) or _lexical_semantic_family(node.name)
            if semantic_family is None:
                continue
            yield SymbolSurface(
                name=node.name,
                kind=kind,
                location=str(py_file),
                semantic_family=semantic_family,
                source="code",
            )'''

    func_new = '''def _is_valid_class_node(node: ast.AST) -> bool:
    if not isinstance(node, ast.ClassDef):
        return False
    if node.name.startswith("_"):
        return False
    return not _is_support_surface(node.name)

def _build_symbol_surface(py_file: Path, node_name: str) -> SymbolSurface | None:
    kind = _class_surface_kind(py_file, node_name)
    if kind is None:
        return None
    semantic_family = _resolve_semantic_family(
        node_name
    ) or _lexical_semantic_family(node_name)
    if semantic_family is None:
        return None
    return SymbolSurface(
        name=node_name,
        kind=kind,
        location=str(py_file),
        semantic_family=semantic_family,
        source="code",
    )

def _iter_class_symbol_surfaces(src_path: Path) -> Iterator[SymbolSurface]:
    """Discover relevant class surfaces from code."""
    for py_file, tree in _iter_python_modules_with_trees(src_path):
        for node in ast.walk(tree):
            if not _is_valid_class_node(node):
                continue
            surface = _build_symbol_surface(py_file, node.name)
            if surface:
                yield surface'''
    text = text.replace(func_old, func_new)

    with open('scripts/engineering/qa/naming_audit.py', 'w', encoding='utf-8') as f:
        f.write(text)

process_naming_audit()
