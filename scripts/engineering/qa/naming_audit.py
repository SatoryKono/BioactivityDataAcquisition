#!/usr/bin/env python3
"""
Naming Convention Audit Tool for BioETL.

Validates naming conventions according to RULES.md v5.24 §2:
- Classes: PascalCase with role-appropriate suffixes
- Modules: snake_case
- Functions: snake_case with semantic prefixes
- Documentation: kebab-case (or NN- prefixed for ordered docs)
- YAML Configs: snake_case
- Constants: UPPER_SNAKE_CASE

Usage:
    python src/tools/naming_audit.py                  # Full audit
    python src/tools/naming_audit.py --check          # CI mode (exit 1 on violations)
    python src/tools/naming_audit.py --output reports/quality/naming-audit.md  # Save report to file
"""

from __future__ import annotations

import argparse
import ast
import logging
import re
import sys
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import yaml

# Configure logging for CLI output
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[3]
NAMING_EXCEPTIONS_PATH = REPO_ROOT / "configs" / "naming_exceptions.yaml"


class ViolationType(StrEnum):
    """Тип нарушения naming convention."""

    CAMELCASE = "camelCase вместо PascalCase/snake_case"
    UPPERCASE_MODULE = "UPPERCASE в имени модуля"
    HYPHEN_IN_MODULE = "дефис в имени Python-модуля"
    MISSING_SUFFIX = "отсутствует обязательный суффикс"
    UNDERSCORE_IN_DOC = "underscore в имени документации"
    UPPERCASE_DOC = "UPPER_SNAKE_CASE в документации"


@dataclass
class Violation:
    """Нарушение naming convention."""

    category: str
    path: str
    line: int | None
    current_name: str
    issue: ViolationType
    recommendation: str


@dataclass(frozen=True)
class StablePublicName:
    """Registry entry for an intentionally stable public identifier."""

    name: str
    location: str
    reason: str


@dataclass(frozen=True)
class ForbiddenAlias:
    """Registry entry for a forbidden legacy alias."""

    legacy_name: str
    canonical_name: str
    export_surface: str
    reason: str


@dataclass(frozen=True)
class BackwardCompatibilitySurface:
    """Structured ADR-024 compatibility surface entry."""

    module: str
    aliases: tuple[str, ...]
    note: str


@dataclass(frozen=True)
class NamingRegistry:
    """Parsed naming exception registry."""

    documentation_exceptions: frozenset[str]
    root_file_exceptions: frozenset[str]
    class_suffix_exceptions: frozenset[str]
    function_prefix_exceptions: frozenset[str]
    stable_pipeline_ids: tuple[StablePublicName, ...]
    stable_pipeline_classes: tuple[StablePublicName, ...]
    stable_transformers: tuple[StablePublicName, ...]
    stable_gold_schemas: tuple[StablePublicName, ...]
    forbidden_domain_entity_aliases: tuple[ForbiddenAlias, ...]
    adr_024_derived_entities: tuple[StablePublicName, ...]
    adr_024_legacy_fields: tuple[StablePublicName, ...]
    adr_024_backward_compatibility: tuple[BackwardCompatibilitySurface, ...]


class AmbiguityClassification(StrEnum):
    """Classification for naming-family overlap."""

    OK = "OK"
    COMPAT = "COMPAT"
    CONFLICT = "CONFLICT"
    DUPLICATE = "DUPLICATE"


@dataclass(frozen=True)
class SymbolSurface:
    """Discovered symbol participating in a naming ambiguity family."""

    name: str
    kind: str
    location: str
    semantic_family: str
    source: str


@dataclass(frozen=True)
class AmbiguityGroup:
    """Deterministic ambiguity-group snapshot."""

    normalized_stem: str
    symbols: tuple[SymbolSurface, ...]
    classification: AmbiguityClassification
    rationale: str


# Суффиксы для классов по ролям
ROLE_SUFFIXES = {
    "Factory": ["Factory"],
    "Client": ["Client"],
    "Facade": ["Facade"],
    "Registry": ["Registry"],
    "Adapter": ["Adapter"],
    "Protocol": ["Protocol", "Port", "ABC"],
    "Config": ["Config", "Model", "Params", "Settings"],
    "Error": ["Error", "Exception"],
    "Impl": ["Impl"],
    "Service": ["Service"],
    "Writer": ["Writer"],
    "Manager": ["Manager"],
    "Monitor": ["Monitor"],
    "Tracker": ["Tracker"],
    "Builder": ["Builder"],
    "Validator": ["Validator"],
    "Exporter": ["Exporter"],
    "Transformer": ["Transformer"],
    "Pipeline": ["Pipeline"],
    "Observer": ["Observer"],
    "Handler": ["Handler"],
    "Processor": ["Processor"],
    "Recorder": ["Recorder"],
    "Aggregator": ["Aggregator"],
    "Orchestrator": ["Orchestrator"],
    "Collector": ["Collector"],
    "Assembler": ["Assembler"],
}

# Directories excluded from doc naming audit (archives, plans, AI content)
_DOC_EXCLUDED_DIRS = {
    "99-archive",
    "plans",
}

# Sub-paths excluded from doc naming audit (relative to docs root)
_DOC_EXCLUDED_SUBPATHS = {
    "00-project/ai",
    "repor",
    "reports",
    "docs/reports",
    "reports/evidence",
}

_GENERIC_FAMILY_TOKENS = frozenset(
    {
        "pipeline",
        "transformer",
        "gold",
        "schema",
        "entity",
        "base",
        "model",
        "record",
    }
)
_CANDIDATE_LABEL_SUFFIX_TOKENS = frozenset(
    {
        "pipeline",
        "transformer",
        "gold",
        "schema",
        "entity",
        "model",
        "record",
        "similarity",
        "term",
        "id",
    }
)
FAMILY_PUBCHEM = "pubchem:molecule"
FAMILY_UNIPROT = "uniprot:target"
FAMILY_CHEMBL = "chembl:publication"

_EXPLICIT_NAME_FAMILIES = {
    "pubchemmolecule": FAMILY_PUBCHEM,
    "pubchemcompound": FAMILY_PUBCHEM,
    "pubchemcompoundpipeline": FAMILY_PUBCHEM,
    "pubchemcompoundtransformer": FAMILY_PUBCHEM,
    "pubchemcompoundgoldschema": FAMILY_PUBCHEM,
    "pubchem_compound": FAMILY_PUBCHEM,
    "uniprottarget": FAMILY_UNIPROT,
    "uniprotprotein": FAMILY_UNIPROT,
    "uniprotproteinpipeline": FAMILY_UNIPROT,
    "uniprotproteintransformer": FAMILY_UNIPROT,
    "uniprotproteingoldschema": FAMILY_UNIPROT,
    "uniprot_protein": FAMILY_UNIPROT,
    "chemblpublication": FAMILY_CHEMBL,
    "chemblpublicationsimilarity": FAMILY_CHEMBL,
    "chemblpublicationterm": FAMILY_CHEMBL,
    "chembl_publication": FAMILY_CHEMBL,
    "chembl_publication_similarity": FAMILY_CHEMBL,
    "chembl_publication_term": FAMILY_CHEMBL,
    "document": FAMILY_CHEMBL,
    "documentsimilarity": FAMILY_CHEMBL,
    "documentterm": FAMILY_CHEMBL,
    "document_id": FAMILY_CHEMBL,
    "documentchemblid": FAMILY_CHEMBL,
    "document_chembl_id": FAMILY_CHEMBL,
    "compound": FAMILY_PUBCHEM,
    "protein": FAMILY_UNIPROT,
}
_EXPLICIT_OK_FAMILY_MEMBERS = {
    FAMILY_PUBCHEM: frozenset(
        {
            "PubchemMolecule",
            "pubchem_compound",
            "PubChemCompoundPipeline",
            "PubChemCompoundTransformer",
            "PubChemCompoundGoldSchema",
        }
    ),
    FAMILY_UNIPROT: frozenset(
        {
            "UniprotTarget",
            "uniprot_protein",
            "UniProtProteinPipeline",
            "UniProtProteinTransformer",
            "UniProtProteinGoldSchema",
        }
    ),
    FAMILY_CHEMBL: frozenset(
        {
            "ChemblPublication",
            "ChemblPublicationSimilarity",
            "ChemblPublicationTerm",
            "chembl_publication",
            "chembl_publication_similarity",
            "chembl_publication_term",
            "DocumentSimilarity",
            "DocumentTerm",
            "document_id",
            "document_chembl_id",
        }
    ),
}


def _normalize_doc_excluded_subpath(subpath: str) -> str:
    """Normalize configured docs exclusion prefixes to docs-root-relative paths."""
    normalized = subpath.replace("\\", "/").strip("/")
    DOCS_PREFIX = "docs/"
    if normalized.startswith(DOCS_PREFIX):
        normalized = normalized.removeprefix(DOCS_PREFIX)
    return normalized


def _flatten_string_values(raw: object) -> list[str]:
    """Flatten nested YAML lists/dicts to strings only."""
    values: list[str] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                values.append(item)
    elif isinstance(raw, dict):
        for value in raw.values():
            values.extend(_flatten_string_values(value))
    return values


def _load_stable_names(raw: object) -> tuple[StablePublicName, ...]:
    """Parse stable public surface entries from YAML."""
    if not isinstance(raw, list):
        return ()
    entries: list[StablePublicName] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        location = str(item.get("location", "")).strip()
        reason = str(item.get("reason", "")).strip()
        if name and location and reason:
            entries.append(
                StablePublicName(name=name, location=location, reason=reason)
            )
    return tuple(entries)


def _load_named_registry_entries(
    raw: object,
    *,
    key: str,
    registry_location: str,
) -> tuple[StablePublicName, ...]:
    """Parse simple ADR-024 exception entries into named registry records."""
    if not isinstance(raw, list):
        return ()

    entries: list[StablePublicName] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get(key, "")).strip()
        location = str(item.get("location", "")).strip() or registry_location
        reason = str(item.get("reason", "")).strip()
        if name and reason:
            entries.append(
                StablePublicName(name=name, location=location, reason=reason)
            )
    return tuple(entries)


def _load_forbidden_aliases(raw: object) -> tuple[ForbiddenAlias, ...]:
    """Parse forbidden legacy alias entries from YAML."""
    if not isinstance(raw, list):
        return ()
    entries: list[ForbiddenAlias] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        legacy_name = str(item.get("legacy_name", "")).strip()
        canonical_name = str(item.get("canonical_name", "")).strip()
        export_surface = str(item.get("export_surface", "")).strip()
        reason = str(item.get("reason", "")).strip()
        if legacy_name and canonical_name and export_surface and reason:
            entries.append(
                ForbiddenAlias(
                    legacy_name=legacy_name,
                    canonical_name=canonical_name,
                    export_surface=export_surface,
                    reason=reason,
                )
            )
    return tuple(entries)


def _load_backward_compatibility_surfaces(
    raw: object,
) -> tuple[BackwardCompatibilitySurface, ...]:
    """Parse structured ADR-024 backward compatibility surfaces."""
    if not isinstance(raw, list):
        return ()

    entries: list[BackwardCompatibilitySurface] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        module = str(item.get("module", "")).strip()
        aliases = tuple(
            value for value in _flatten_string_values(item.get("aliases", [])) if value
        )
        note = str(item.get("note", item.get("reason", ""))).strip()
        if module and (aliases or note):
            entries.append(
                BackwardCompatibilitySurface(
                    module=module,
                    aliases=aliases,
                    note=note,
                )
            )
    return tuple(entries)


def load_naming_registry(
    registry_path: Path = NAMING_EXCEPTIONS_PATH,
) -> NamingRegistry:
    """Load the naming exception registry from configs/."""
    if not registry_path.exists():
        raise FileNotFoundError(f"Naming exception registry missing: {registry_path}")

    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(
            "Naming exception registry must be a YAML mapping at top level"
        )

    stable_public_surface = payload.get("stable_public_surface", {})
    if not isinstance(stable_public_surface, dict):
        raise ValueError("stable_public_surface must be a mapping")
    adr_024_known_exceptions = payload.get("adr_024_known_exceptions", {})
    if not isinstance(adr_024_known_exceptions, dict):
        raise ValueError("adr_024_known_exceptions must be a mapping")

    return NamingRegistry(
        documentation_exceptions=frozenset(
            _flatten_string_values(payload.get("documentation_exceptions", []))
        ),
        root_file_exceptions=frozenset(
            _flatten_string_values(payload.get("root_file_exceptions", []))
        ),
        class_suffix_exceptions=frozenset(
            _flatten_string_values(payload.get("class_suffix_exceptions", {}))
        ),
        function_prefix_exceptions=frozenset(
            _flatten_string_values(payload.get("function_prefix_exceptions", []))
        ),
        stable_pipeline_ids=_load_stable_names(
            stable_public_surface.get("pipeline_ids", [])
        ),
        stable_pipeline_classes=_load_stable_names(
            stable_public_surface.get("pipeline_classes", [])
        ),
        stable_transformers=_load_stable_names(
            stable_public_surface.get("transformers", [])
        ),
        stable_gold_schemas=_load_stable_names(
            stable_public_surface.get("gold_schemas", [])
        ),
        forbidden_domain_entity_aliases=_load_forbidden_aliases(
            payload.get("forbidden_domain_entity_aliases", [])
        ),
        adr_024_derived_entities=_load_named_registry_entries(
            adr_024_known_exceptions.get("derived_entities", []),
            key="entity",
            registry_location=str(registry_path),
        ),
        adr_024_legacy_fields=_load_named_registry_entries(
            adr_024_known_exceptions.get("legacy_fields", []),
            key="field",
            registry_location=str(registry_path),
        ),
        adr_024_backward_compatibility=_load_backward_compatibility_surfaces(
            adr_024_known_exceptions.get("backward_compatibility", [])
        ),
    )


def _validate_registry_forbidden_alias_overlap(
    registry: NamingRegistry, errors: list[str]
) -> None:
    overlap = {
        alias.legacy_name for alias in registry.forbidden_domain_entity_aliases
    } & set(registry.class_suffix_exceptions)
    if overlap:
        joined = ", ".join(sorted(overlap))
        errors.append(
            "Forbidden legacy aliases are still declared as class suffix exceptions: "
            f"{joined}"
        )


def _validate_registry_required_pipeline_ids(
    registry: NamingRegistry, errors: list[str]
) -> None:
    stable_id_names = {entry.name for entry in registry.stable_pipeline_ids}
    if not stable_id_names:
        errors.append(
            "stable_public_surface.pipeline_ids must declare at least one entry"
        )
        return

    for required in ("pubchem_compound", "uniprot_protein"):
        if required not in stable_id_names:
            errors.append(
                f"stable_public_surface.pipeline_ids is missing required entry: {required}"
            )


def _validate_registry_backward_compatibility(
    registry: NamingRegistry, errors: list[str]
) -> None:
    forbidden_aliases_by_surface: dict[str, set[str]] = {}
    for alias in registry.forbidden_domain_entity_aliases:
        forbidden_aliases_by_surface.setdefault(alias.export_surface, set()).add(
            alias.legacy_name
        )

    for surface in registry.adr_024_backward_compatibility:
        forbidden_aliases = forbidden_aliases_by_surface.get(surface.module)
        if not forbidden_aliases:
            continue
        if not surface.aliases:
            errors.append(
                "ADR-024 backward compatibility entry for "
                f"{surface.module} must list exact aliases or be removed because "
                "that module is also declared as the forbidden legacy alias "
                "export surface"
            )
            continue

        overlap = sorted(forbidden_aliases & set(surface.aliases))
        if overlap:
            joined = ", ".join(overlap)
            errors.append(
                "ADR-024 backward compatibility entry for "
                f"{surface.module} reintroduces forbidden legacy aliases: {joined}"
            )


def validate_naming_registry(registry: NamingRegistry) -> list[str]:
    """Return consistency errors for the loaded naming registry."""
    errors: list[str] = []
    _validate_registry_forbidden_alias_overlap(registry, errors)
    _validate_registry_required_pipeline_ids(registry, errors)
    _validate_registry_backward_compatibility(registry, errors)
    return errors


def is_pascal_case(name: str) -> bool:
    """Проверяет, что имя в PascalCase."""
    return bool(re.match(r"^[A-Z][a-zA-Z0-9]*$", name))


def is_snake_case(name: str) -> bool:
    """Проверяет, что имя в snake_case."""
    return bool(re.match(r"^[a-z][a-z0-9_]*$", name))


def is_kebab_case(name: str) -> bool:
    """Проверяет, что имя в kebab-case."""
    return bool(re.match(r"^[a-z][a-z0-9-]*$", name))


def is_prefixed_doc(name: str) -> bool:
    """Проверяет, что документ имеет числовой префикс (NN-)."""
    return bool(re.match(r"^\d{2}-", name))


def has_valid_suffix(class_name: str, allowed_no_suffix: frozenset[str]) -> bool:
    """Check whether a class name has a valid suffix or registry-backed exception."""
    if class_name in allowed_no_suffix:
        return True

    for suffixes in ROLE_SUFFIXES.values():
        for suffix in suffixes:
            if class_name.endswith(suffix):
                return True

    return False


def _iter_python_files(base_path: Path) -> Iterator[Path]:
    for py_file in base_path.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        yield py_file


def _iter_python_modules_with_trees(
    base_path: Path,
) -> Iterator[tuple[Path, ast.Module]]:
    """Yield parsed AST modules under the requested base path."""
    for py_file in _iter_python_files(base_path):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        yield py_file, tree


def _class_naming_violation(py_file: Path, node: ast.ClassDef) -> Violation | None:
    class_name = node.name

    if class_name.startswith("_") and not class_name.startswith("__"):
        return None

    if is_pascal_case(class_name) or class_name.startswith("_"):
        return None

    return Violation(
        category="class",
        path=str(py_file),
        line=node.lineno,
        current_name=class_name,
        issue=ViolationType.CAMELCASE,
        recommendation=class_name[0].upper() + class_name[1:],
    )


def _exported_names_from_all_assign(node: ast.Assign) -> set[str]:
    """Return exported string names from a __all__ assignment."""
    if not isinstance(node.value, (ast.List, ast.Tuple)):
        return set()
    return {
        elt.value
        for elt in node.value.elts
        if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
    }


def _is_all_assignment(node: ast.AST) -> bool:
    """Check whether a node assigns to __all__."""
    if not isinstance(node, ast.Assign):
        return False
    return any(
        isinstance(target, ast.Name) and target.id == "__all__"
        for target in node.targets
    )


def _extract_all_exports(path: Path) -> set[str]:
    """Extract string exports from a module __all__ assignment."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return set()
    for node in tree.body:
        if _is_all_assignment(node):
            return _exported_names_from_all_assign(node)
    return set()


def _tokenize_symbol_name(name: str) -> list[str]:
    """Tokenize snake_case and PascalCase names into lowercase semantic parts."""
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", name).replace("-", "_")
    return [part for part in snake.lower().split("_") if part]


def _lexical_semantic_family(name: str) -> str | None:
    """Conservative fallback family for synthetic duplicate detection."""
    tokens = [
        token
        for token in _tokenize_symbol_name(name)
        if token not in _GENERIC_FAMILY_TOKENS
    ]
    if not tokens:
        return None
    return "candidate:" + "_".join(tokens)


def _resolve_semantic_family(name: str) -> str | None:
    """Resolve a semantic family using explicit mappings before lexical fallback."""
    return _EXPLICIT_NAME_FAMILIES.get(name) or _EXPLICIT_NAME_FAMILIES.get(
        name.replace("_", "").lower()
    )


def _candidate_family_label(name: str) -> str:
    """Collapse role suffixes so routine entity/pipeline pairs do not form ambiguity groups."""
    tokens = _tokenize_symbol_name(name)
    while len(tokens) > 1 and tokens[-1] in _CANDIDATE_LABEL_SUFFIX_TOKENS:
        tokens.pop()
    return "_".join(tokens)


def _is_support_surface(name: str) -> bool:
    """Exclude abstract/base support symbols from ambiguity inventory."""
    return name.startswith("Base") or name.endswith("Base") or name.endswith("Record")


def _class_surface_kind(py_file: Path, class_name: str) -> str | None:
    """Classify active code surfaces relevant to ambiguity detection."""
    normalized = py_file.as_posix()
    if normalized.endswith("/domain/entities/__init__.py"):
        return None
    if "/application/pipelines/" in normalized and class_name.endswith("Pipeline"):
        return "pipeline_class"
    if "/application/pipelines/" in normalized and class_name.endswith("Transformer"):
        return "transformer"
    if "/domain/contracts/gold/" in normalized and class_name.endswith("Schema"):
        return "gold_schema"
    if "/domain/entities/" in normalized and not class_name.endswith("Record"):
        return "domain_entity"
    return None


def _is_valid_class_node(node: ast.AST) -> bool:
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
                yield surface


def _iter_domain_export_surfaces(
    src_path: Path,
    registry: NamingRegistry,
) -> Iterator[SymbolSurface]:
    """Discover exported domain entity facade symbols."""
    exports_path = src_path / "domain" / "entities" / "__init__.py"
    exports = _extract_all_exports(exports_path)
    forbidden_alias_names = {
        alias.legacy_name for alias in registry.forbidden_domain_entity_aliases
    }

    for name in sorted(exports):
        if _is_support_surface(name):
            continue
        semantic_family = _resolve_semantic_family(name) or _lexical_semantic_family(
            name
        )
        if semantic_family is None:
            continue
        kind = "forbidden_alias" if name in forbidden_alias_names else "domain_export"
        yield SymbolSurface(
            name=name,
            kind=kind,
            location=str(exports_path),
            semantic_family=semantic_family,
            source="code",
        )


def _iter_pipeline_id_surfaces(configs_path: Path) -> Iterator[SymbolSurface]:
    """Discover active pipeline IDs from entity configs."""
    entities_root = configs_path / "entities"
    if not entities_root.exists():
        return

    for yaml_file in sorted(entities_root.rglob("*.yaml")):
        try:
            payload = yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        if not isinstance(payload, dict):
            continue
        pipeline = payload.get("pipeline")
        if not isinstance(pipeline, dict):
            continue
        pipeline_name = str(pipeline.get("pipeline_name", "")).strip()
        if not pipeline_name:
            continue
        semantic_family = _resolve_semantic_family(
            pipeline_name
        ) or _lexical_semantic_family(pipeline_name)
        if semantic_family is None:
            continue
        yield SymbolSurface(
            name=pipeline_name,
            kind="pipeline_id",
            location=str(yaml_file),
            semantic_family=semantic_family,
            source="config",
        )


def _iter_registry_symbol_surfaces(registry: NamingRegistry) -> Iterator[SymbolSurface]:
    """Materialize registry-backed ambiguity surfaces not otherwise visible in code."""
    for entry in registry.adr_024_derived_entities:
        semantic_family = _resolve_semantic_family(
            entry.name
        ) or _lexical_semantic_family(entry.name)
        if semantic_family is None:
            continue
        yield SymbolSurface(
            name=entry.name,
            kind="derived_entity",
            location=entry.location,
            semantic_family=semantic_family,
            source="registry",
        )

    for entry in registry.adr_024_legacy_fields:
        semantic_family = _resolve_semantic_family(
            entry.name
        ) or _lexical_semantic_family(entry.name)
        if semantic_family is None:
            continue
        yield SymbolSurface(
            name=entry.name,
            kind="legacy_field",
            location=entry.location,
            semantic_family=semantic_family,
            source="registry",
        )


def _iter_all_symbol_surfaces(
    src_path: Path,
    configs_path: Path,
    registry: NamingRegistry,
) -> Iterator[SymbolSurface]:
    """Enumerate all naming surfaces participating in ambiguity detection."""
    yield from _iter_class_symbol_surfaces(src_path)
    yield from _iter_domain_export_surfaces(src_path, registry)
    yield from _iter_pipeline_id_surfaces(configs_path)
    yield from _iter_registry_symbol_surfaces(registry)


def _stable_registry_name_index(registry: NamingRegistry) -> set[str]:
    """Return all explicitly registered stable or exceptional names."""
    return {
        entry.name
        for entry in (
            *registry.stable_pipeline_ids,
            *registry.stable_pipeline_classes,
            *registry.stable_transformers,
            *registry.stable_gold_schemas,
            *registry.adr_024_derived_entities,
            *registry.adr_024_legacy_fields,
        )
    }


def _compatibility_alias_index(registry: NamingRegistry) -> set[str]:
    """Return exact compatibility aliases declared in the registry."""
    aliases: set[str] = set()
    for entry in registry.adr_024_backward_compatibility:
        aliases.update(entry.aliases)
    return aliases


def _forbidden_alias_group_rationale() -> str:
    return (
        "Forbidden ADR-024 alias surfaced on an active export without an "
        "explicit compatibility decision."
    )


def _compatibility_alias_group_rationale() -> str:
    return (
        "Exact compatibility alias is registered in ADR-024 backward "
        "compatibility metadata."
    )


def _duplicate_group_rationale(unresolved_summary: str) -> str:
    return (
        "Overlap family has active surfaces without registry-backed "
        f"distinction: {unresolved_summary}"
    )


def _classify_forbidden_alias_group(
    normalized_stem: str, symbols: tuple[SymbolSurface, ...]
) -> AmbiguityGroup:
    return AmbiguityGroup(
        normalized_stem=normalized_stem,
        symbols=symbols,
        classification=AmbiguityClassification.CONFLICT,
        rationale=_forbidden_alias_group_rationale(),
    )


def _classify_compat_alias_group(
    normalized_stem: str, symbols: tuple[SymbolSurface, ...]
) -> AmbiguityGroup:
    return AmbiguityGroup(
        normalized_stem=normalized_stem,
        symbols=symbols,
        classification=AmbiguityClassification.COMPAT,
        rationale=_compatibility_alias_group_rationale(),
    )


def _classify_duplicate_group(
    normalized_stem: str,
    symbols: tuple[SymbolSurface, ...],
    unresolved_summary: str,
) -> AmbiguityGroup:
    return AmbiguityGroup(
        normalized_stem=normalized_stem,
        symbols=symbols,
        classification=AmbiguityClassification.DUPLICATE,
        rationale=_duplicate_group_rationale(unresolved_summary),
    )


def classify_ambiguity_group(
    normalized_stem: str,
    symbols: tuple[SymbolSurface, ...],
    registry: NamingRegistry,
) -> AmbiguityGroup:
    """Classify one ambiguity group using registry-backed policy rules."""
    ordered_symbols = tuple(
        sorted(symbols, key=lambda symbol: (symbol.name, symbol.kind, symbol.location))
    )
    if any(symbol.kind == "forbidden_alias" for symbol in ordered_symbols):
        return _classify_forbidden_alias_group(normalized_stem, ordered_symbols)

    exact_compat_aliases = _compatibility_alias_index(registry)
    if any(symbol.name in exact_compat_aliases for symbol in ordered_symbols):
        return _classify_compat_alias_group(normalized_stem, ordered_symbols)

    allowlisted_names = _stable_registry_name_index(registry) | set(
        _EXPLICIT_OK_FAMILY_MEMBERS.get(normalized_stem, frozenset())
    )
    unresolved = [
        symbol for symbol in ordered_symbols if symbol.name not in allowlisted_names
    ]
    if unresolved:
        unresolved_summary = ", ".join(
            sorted(f"{symbol.name}:{symbol.kind}" for symbol in unresolved)
        )
        return _classify_duplicate_group(
            normalized_stem,
            ordered_symbols,
            unresolved_summary,
        )

    return AmbiguityGroup(
        normalized_stem=normalized_stem,
        symbols=ordered_symbols,
        classification=AmbiguityClassification.OK,
        rationale="All non-canonical overlap surfaces are explicitly registered.",
    )


def build_ambiguity_groups(
    src_path: Path,
    configs_path: Path,
    registry: NamingRegistry,
) -> list[AmbiguityGroup]:
    """Build a deterministic ambiguity map for naming-family overlap."""
    grouped: dict[str, dict[tuple[str, str, str], SymbolSurface]] = defaultdict(dict)
    for symbol in _iter_all_symbol_surfaces(src_path, configs_path, registry):
        grouped[symbol.semantic_family][(symbol.name, symbol.kind, symbol.location)] = (
            symbol
        )

    groups: list[AmbiguityGroup] = []
    for semantic_family in sorted(grouped):
        symbols = tuple(grouped[semantic_family].values())
        if _should_skip_ambiguity_group(semantic_family, symbols):
            continue
        groups.append(classify_ambiguity_group(semantic_family, symbols, registry))
    return groups


def _should_skip_ambiguity_group(
    semantic_family: str,
    symbols: tuple[SymbolSurface, ...],
) -> bool:
    if len(symbols) < 2 and not any(
        symbol.kind == "forbidden_alias" for symbol in symbols
    ):
        return True
    if not semantic_family.startswith("candidate:"):
        return False
    labels = {_candidate_family_label(symbol.name) for symbol in symbols}
    return len(labels) < 2 and not any(
        symbol.kind == "forbidden_alias" for symbol in symbols
    )


def _doc_relative_parts(
    docs_path: Path, md_file: Path
) -> tuple[Path | None, tuple[str, ...]]:
    try:
        rel = md_file.relative_to(docs_path)
        return rel, rel.parts
    except ValueError:
        return None, ()


def _normalize_doc_exception_path(value: str) -> str:
    """Normalize docs exception paths to docs-root-relative slash form."""
    normalized = value.replace("\\", "/").strip("/")
    DOCS_PREFIX = "docs/"
    if normalized.startswith(DOCS_PREFIX):
        normalized = normalized.removeprefix(DOCS_PREFIX)
    return normalized


def _is_documentation_exception(
    docs_path: Path,
    md_file: Path,
    documentation_exceptions: frozenset[str],
) -> bool:
    """Match documentation exceptions by filename or docs-relative path."""
    if md_file.name in documentation_exceptions:
        return True
    rel, _ = _doc_relative_parts(docs_path, md_file)
    if rel is None:
        return False
    normalized_rel = _normalize_doc_exception_path(str(rel))
    normalized_exceptions = {
        _normalize_doc_exception_path(value)
        for value in documentation_exceptions
        if "/" in value or "\\" in value
    }
    return normalized_rel in normalized_exceptions


def _is_excluded_doc_path(docs_path: Path, md_file: Path) -> bool:
    rel, rel_parts = _doc_relative_parts(docs_path, md_file)
    if rel_parts and rel_parts[0] in _DOC_EXCLUDED_DIRS:
        return True
    if rel is None:
        return False
    normalized_rel = str(rel).replace("\\", "/")
    return any(
        normalized_rel.startswith(_normalize_doc_excluded_subpath(subpath))
        for subpath in _DOC_EXCLUDED_SUBPATHS
    )


def check_python_modules(base_path: Path) -> Iterator[Violation]:
    """Проверяет naming conventions для Python-модулей."""
    for py_file in _iter_python_files(base_path):
        filename = py_file.stem
        if filename.startswith("__"):  # __init__, __main__
            continue

        # Проверка на uppercase
        if any(c.isupper() for c in filename):
            yield Violation(
                category="module",
                path=str(py_file),
                line=None,
                current_name=filename,
                issue=ViolationType.UPPERCASE_MODULE,
                recommendation=filename.lower(),
            )

        # Проверка на дефисы
        if "-" in filename:
            yield Violation(
                category="module",
                path=str(py_file),
                line=None,
                current_name=filename,
                issue=ViolationType.HYPHEN_IN_MODULE,
                recommendation=filename.replace("-", "_"),
            )


def check_classes(base_path: Path) -> Iterator[Violation]:
    """Проверяет naming conventions для классов."""
    for py_file in _iter_python_files(base_path):
        try:
            with open(py_file, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(py_file))
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if violation := _class_naming_violation(py_file, node):
                yield violation


def check_documentation(
    docs_path: Path, documentation_exceptions: frozenset[str]
) -> Iterator[Violation]:
    """Проверяет naming conventions для файлов документации."""
    for md_file in docs_path.rglob("*.md"):
        filename = md_file.name

        # Исключения для конвенционных файлов
        if _is_documentation_exception(docs_path, md_file, documentation_exceptions):
            continue

        if _is_excluded_doc_path(docs_path, md_file):
            continue

        basename = md_file.stem

        # Проверка на underscore (должен быть kebab-case)
        if "_" in basename and not is_prefixed_doc(basename):
            yield Violation(
                category="doc",
                path=str(md_file),
                line=None,
                current_name=filename,
                issue=ViolationType.UNDERSCORE_IN_DOC,
                recommendation=basename.replace("_", "-") + ".md",
            )

        # Проверка на UPPER_SNAKE_CASE (без числового префикса)
        if re.match(r"^[A-Z][A-Z_]+$", basename) and not is_prefixed_doc(basename):
            yield Violation(
                category="doc",
                path=str(md_file),
                line=None,
                current_name=filename,
                issue=ViolationType.UPPERCASE_DOC,
                recommendation=basename.lower().replace("_", "-") + ".md",
            )


def check_yaml_configs(configs_path: Path) -> Iterator[Violation]:
    """Проверяет naming conventions для YAML-конфигов."""
    for yaml_file in configs_path.rglob("*.yaml"):
        filename = yaml_file.stem

        # Проверка на uppercase
        if any(c.isupper() for c in filename):
            yield Violation(
                category="config",
                path=str(yaml_file),
                line=None,
                current_name=filename,
                issue=ViolationType.UPPERCASE_MODULE,
                recommendation=filename.lower(),
            )

        # Проверка на дефисы (YAML должен быть snake_case)
        if "-" in filename:
            yield Violation(
                category="config",
                path=str(yaml_file),
                line=None,
                current_name=filename,
                issue=ViolationType.HYPHEN_IN_MODULE,
                recommendation=filename.replace("-", "_"),
            )


def run_audit(
    src_path: Path,
    docs_path: Path,
    configs_path: Path,
    registry: NamingRegistry,
) -> dict[str, list[Violation]]:
    """Запускает полный аудит naming conventions."""
    results: dict[str, list[Violation]] = {
        "modules": [],
        "classes": [],
        "docs": [],
        "configs": [],
    }

    # Проверка Python-модулей
    results["modules"].extend(check_python_modules(src_path))

    # Проверка классов
    results["classes"].extend(check_classes(src_path))

    # Проверка документации
    if docs_path.exists():
        results["docs"].extend(
            check_documentation(docs_path, registry.documentation_exceptions)
        )

    # Проверка YAML-конфигов
    if configs_path.exists():
        results["configs"].extend(check_yaml_configs(configs_path))

    return results


def format_report(results: dict[str, list[Violation]]) -> str:
    """Форматирует отчёт об аудите."""
    lines = [
        "# Naming Convention Audit Report",
        "",
        "## Summary",
        "",
    ]

    total_violations = sum(len(v) for v in results.values())

    lines.append(f"**Total violations: {total_violations}**")
    lines.append("")
    lines.append("| Category | Violations |")
    lines.append("|----------|------------|")
    for category, violations in results.items():
        lines.append(f"| {category.title()} | {len(violations)} |")

    lines.append("")

    for category, violations in results.items():
        if violations:
            lines.append(f"## {category.title()} Violations")
            lines.append("")
            lines.append("| Path | Line | Current | Issue | Recommendation |")
            lines.append("|------|------|---------|-------|----------------|")
            for v in violations:
                line = v.line if v.line else "-"
                lines.append(
                    f"| `{v.path}` | {line} | `{v.current_name}` | "
                    f"{v.issue.value} | `{v.recommendation}` |"
                )
            lines.append("")

    if total_violations == 0:
        lines.append(
            "OK: **No violations found. All naming conventions are followed.**"
        )

    return "\n".join(lines)


def _format_symbol_list(symbols: tuple[SymbolSurface, ...]) -> str:
    """Render ambiguity-group symbols deterministically."""
    return ", ".join(f"{symbol.name} ({symbol.kind})" for symbol in symbols)


def _format_path_list(symbols: tuple[SymbolSurface, ...]) -> str:
    """Render unique source paths for one ambiguity group."""
    unique_paths = sorted({symbol.location for symbol in symbols})
    return ", ".join(f"`{path}`" for path in unique_paths)


def format_ambiguity_section(ambiguity_groups: list[AmbiguityGroup]) -> str:
    """Format ambiguity groups as a markdown report section."""
    lines = [
        "## Ambiguity Groups",
        "",
        "| Family | Symbols | Classification | Paths | Rationale |",
        "|--------|---------|----------------|-------|-----------|",
    ]
    if not ambiguity_groups:
        lines.append("| - | - | - | - | No ambiguity groups detected. |")
        lines.append("")
        return "\n".join(lines)

    for group in ambiguity_groups:
        lines.append(
            "| "
            f"`{group.normalized_stem}` | {_format_symbol_list(group.symbols)} | "
            f"{group.classification.value} | {_format_path_list(group.symbols)} | "
            f"{group.rationale} |"
        )
    lines.append("")
    return "\n".join(lines)


def format_full_report(
    results: dict[str, list[Violation]],
    ambiguity_groups: list[AmbiguityGroup],
) -> str:
    """Format the standard report plus ambiguity-classifier output."""
    return format_report(results) + "\n\n" + format_ambiguity_section(ambiguity_groups)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Naming Convention Audit Tool for BioETL"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI mode: exit with code 1 if violations found",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save report to file",
    )
    parser.add_argument(
        "--src",
        type=str,
        default="src/bioetl",
        help="Source code path (default: src/bioetl)",
    )
    parser.add_argument(
        "--docs",
        type=str,
        default="docs",
        help="Documentation path (default: docs)",
    )
    parser.add_argument(
        "--configs",
        type=str,
        default="configs",
        help="Configs path (default: configs)",
    )
    return parser.parse_args()


def _audit_paths(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    base_dir = REPO_ROOT
    return base_dir / args.src, base_dir / args.docs, base_dir / args.configs


def _load_validated_registry() -> NamingRegistry | None:
    try:
        registry = load_naming_registry()
    except (FileNotFoundError, OSError, ValueError, yaml.YAMLError) as exc:
        logger.error("Failed to load naming exception registry: %s", exc)
        return None

    registry_errors = validate_naming_registry(registry)
    if registry_errors:
        for error in registry_errors:
            logger.error("Naming exception registry error: %s", error)
        return None

    return registry


def _emit_report(report: str, output: str | None) -> None:
    if output:
        output_path = Path(output)
        output_path.write_text(report, encoding="utf-8")
        logger.info("Report saved to %s", output_path)
        return
    logger.info("%s", report)


def main() -> int:
    """Точка входа."""
    args = parse_args()
    src_path, docs_path, configs_path = _audit_paths(args)

    registry = _load_validated_registry()
    if registry is None:
        return 1

    results = run_audit(src_path, docs_path, configs_path, registry)
    ambiguity_groups = build_ambiguity_groups(src_path, configs_path, registry)
    report = format_full_report(results, ambiguity_groups)
    _emit_report(report, args.output)

    # CI mode
    total_violations = sum(len(v) for v in results.values())
    blocking_ambiguity_groups = [
        group
        for group in ambiguity_groups
        if group.classification
        in {AmbiguityClassification.CONFLICT, AmbiguityClassification.DUPLICATE}
    ]
    if args.check and (total_violations > 0 or blocking_ambiguity_groups):
        if total_violations > 0:
            logger.error("Found %d naming violations", total_violations)
        if blocking_ambiguity_groups:
            logger.error(
                "Found %d blocking ambiguity groups",
                len(blocking_ambiguity_groups),
            )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
