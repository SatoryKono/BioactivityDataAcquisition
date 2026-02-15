
"""Generate a full, code-first audit for BioETL.

Outputs:
- files_inventory.csv
- entities.csv
- entities_pipeline_matrix.csv
- dead_code_candidates.csv
- duplicate_names.csv
- duplicate_logic.csv
- architecture_violations.csv
- architecture_report.md
- documentation_audit_report.md
- full_audit_summary.md
- metadata.json
"""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - fallback if pyyaml unavailable
    yaml = None


LAYER_ORDER = ("domain", "application", "infrastructure", "composition", "interfaces")
IDENT_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
REQ_ID_RE = re.compile(r"\bREQ-[A-Z]+-\d+\b")
VERSION_RE = re.compile(r"(?:Version|Версия)\s*[:vV]?\s*([0-9]+(?:\.[0-9]+)+)")
ADR_IDS = ("ADR-010", "ADR-014", "ADR-017")


@dataclass
class EntityRecord:
    name: str
    qualname: str
    entity_type: str
    scope: str
    module: str
    layer: str
    file: str
    line: int
    end_line: int
    loc: int
    body_hash: str | None = None


@dataclass
class ArchitectureViolation:
    category: str
    severity: str
    file: str
    line: int
    source_layer: str
    target: str
    message: str
    rule: str


def find_repo_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "pyproject.toml").exists() and (candidate / "src" / "bioetl").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from script location")


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def git_ls_files(root: Path) -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files"],
        cwd=root,
        text=True,
        encoding="utf-8",
    )
    files = []
    for line in output.splitlines():
        line = line.strip()
        if line:
            files.append(root / line)
    return files


def classify_file(path: Path, root: Path) -> str:
    p = rel(path, root)
    suffix = path.suffix.lower()
    if p.startswith("src/") and suffix == ".py":
        return "src_py"
    if p.startswith("tests/") and suffix == ".py":
        return "tests_py"
    if p.startswith("docs/"):
        return "docs"
    if p in {"README.md", "mkdocs.yml"}:
        return "docs_root"
    if p.startswith("configs/"):
        return "config"
    if suffix in {".py", ".md", ".yaml", ".yml", ".json", ".csv", ".toml", ".ini"}:
        return "other_text"
    return "other"


def module_from_src_path(src_rel_path: str) -> tuple[str, str]:
    # src_rel_path format: src/bioetl/<layer>/...
    parts = src_rel_path.replace("\\", "/").split("/")
    if len(parts) < 4:
        return "", ""
    layer = parts[2]
    module_path = ".".join(parts[1:]).removesuffix(".py")
    if module_path.endswith(".__init__"):
        module_path = module_path[: -len(".__init__")]
    return layer, module_path


def strip_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        return body[1:]
    return body


def hash_body(body: list[ast.stmt]) -> str:
    cleaned = strip_docstring(body)
    node = ast.Module(body=cleaned, type_ignores=[])
    dumped = ast.dump(node, include_attributes=False)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


def iter_target_names(target: ast.expr) -> Iterable[str]:
    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, (ast.Tuple, ast.List)):
        for item in target.elts:
            yield from iter_target_names(item)


class EntityCollector(ast.NodeVisitor):
    def __init__(self, root: Path, file_path: Path, module: str, layer: str):
        self.root = root
        self.file_path = file_path
        self.file_rel = rel(file_path, root)
        self.module = module
        self.layer = layer
        self.stack: list[tuple[str, str]] = []
        self.records: list[EntityRecord] = []
        self._seen_scope_names: set[tuple[str, str, str]] = set()

    def _scope_name(self) -> str:
        if not self.stack:
            return "<module>"
        return ".".join(name for _, name in self.stack)

    def _current_scope_kind(self) -> str:
        if not self.stack:
            return "module"
        kind, _ = self.stack[-1]
        if kind == "class":
            return "class"
        if kind in {"function", "method"}:
            return kind
        return kind

    def _qualname(self, name: str) -> str:
        if not self.stack:
            return f"{self.module}.{name}"
        suffix = ".".join(part for _, part in self.stack)
        return f"{self.module}.{suffix}.{name}"

    def _add_record(
        self,
        *,
        name: str,
        entity_type: str,
        scope: str,
        node: ast.AST,
        body_hash_value: str | None = None,
    ) -> None:
        line = int(getattr(node, "lineno", 1))
        end_line = int(getattr(node, "end_lineno", line))
        loc = max(end_line - line + 1, 1)
        self.records.append(
            EntityRecord(
                name=name,
                qualname=self._qualname(name),
                entity_type=entity_type,
                scope=scope,
                module=self.module,
                layer=self.layer,
                file=self.file_rel,
                line=line,
                end_line=end_line,
                loc=loc,
                body_hash=body_hash_value,
            )
        )

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        self._add_record(
            name=node.name,
            entity_type="class",
            scope=self._current_scope_kind(),
            node=node,
            body_hash_value=hash_body(node.body),
        )
        self.stack.append(("class", node.name))
        for item in node.body:
            self.visit(item)
        self.stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self._visit_function_like(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self._visit_function_like(node)

    def _visit_function_like(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        is_method = bool(self.stack and self.stack[-1][0] == "class")
        kind = "method" if is_method else "function"
        self._add_record(
            name=node.name,
            entity_type=kind,
            scope=self._current_scope_kind(),
            node=node,
            body_hash_value=hash_body(node.body),
        )

        # Parameters are tracked as variables to satisfy exhaustive request.
        all_args = list(node.args.posonlyargs) + list(node.args.args)
        all_args.extend(node.args.kwonlyargs)
        if node.args.vararg:
            all_args.append(node.args.vararg)
        if node.args.kwarg:
            all_args.append(node.args.kwarg)
        for arg in all_args:
            key = (self._scope_name(), arg.arg, "parameter")
            if key in self._seen_scope_names:
                continue
            self._seen_scope_names.add(key)
            self._add_record(
                name=arg.arg,
                entity_type="parameter",
                scope=kind,
                node=arg,
            )

        self.stack.append((kind, node.name))
        for item in node.body:
            self.visit(item)
        self.stack.pop()

    def visit_Assign(self, node: ast.Assign) -> Any:
        self._record_assignment_targets(node.targets, node)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> Any:
        self._record_assignment_targets([node.target], node)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> Any:
        self._record_assignment_targets([node.target], node)
        self.generic_visit(node)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> Any:
        self._record_assignment_targets([node.target], node)
        self.generic_visit(node)

    def _record_assignment_targets(self, targets: list[ast.expr], node: ast.AST) -> None:
        scope = self._current_scope_kind()
        for target in targets:
            for name in iter_target_names(target):
                record_type = "constant" if name.isupper() and scope in {"module", "class"} else "variable"
                key = (self._scope_name(), name, record_type)
                if key in self._seen_scope_names:
                    continue
                self._seen_scope_names.add(key)
                self._add_record(
                    name=name,
                    entity_type=record_type,
                    scope=scope,
                    node=node,
                )


def collect_entities(root: Path, src_py_files: list[Path]) -> list[EntityRecord]:
    entities: list[EntityRecord] = []
    for path in src_py_files:
        file_rel = rel(path, root)
        layer, module = module_from_src_path(file_rel)
        if not module:
            continue
        source = read_text(path)
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        collector = EntityCollector(root, path, module=module, layer=layer)
        collector.visit(tree)
        entities.extend(collector.records)
    entities.sort(key=lambda r: (LAYER_ORDER.index(r.layer) if r.layer in LAYER_ORDER else 999, r.file, r.line))
    return entities


def collect_tokens_by_group(
    root: Path, files: list[Path]
) -> tuple[
    dict[str, Counter[str]],
    dict[str, dict[str, set[str]]],
    dict[str, Counter[str]],
]:
    counts_by_group: dict[str, Counter[str]] = {
        "src": Counter(),
        "tests": Counter(),
        "docs": Counter(),
    }
    files_by_group: dict[str, dict[str, set[str]]] = {
        "src": defaultdict(set),
        "tests": defaultdict(set),
        "docs": defaultdict(set),
    }
    file_token_counts: dict[str, Counter[str]] = {}

    for path in files:
        kind = classify_file(path, root)
        if kind not in {"src_py", "tests_py", "docs", "docs_root"}:
            continue
        suffix = path.suffix.lower()
        if kind in {"docs", "docs_root"} and suffix not in {".md", ".yml", ".yaml"}:
            continue
        group = "src" if kind == "src_py" else "tests" if kind == "tests_py" else "docs"
        try:
            text = read_text(path)
        except OSError:
            continue
        tokens = IDENT_RE.findall(text)
        counter = Counter(tokens)
        file_rel = rel(path, root)
        file_token_counts[file_rel] = counter
        for token, cnt in counter.items():
            counts_by_group[group][token] += cnt
            files_by_group[group][token].add(file_rel)
    return counts_by_group, files_by_group, file_token_counts

def extract_symbol_names(expr: ast.AST | None) -> list[str]:
    if expr is None:
        return []
    if isinstance(expr, ast.Name):
        return [expr.id]
    if isinstance(expr, ast.Attribute):
        return [expr.attr]
    if isinstance(expr, (ast.Tuple, ast.List, ast.Set)):
        names: list[str] = []
        for item in expr.elts:
            names.extend(extract_symbol_names(item))
        return names
    if isinstance(expr, ast.Dict):
        names: list[str] = []
        for key in expr.keys:
            names.extend(extract_symbol_names(key))
        for value in expr.values:
            names.extend(extract_symbol_names(value))
        return names
    if isinstance(expr, ast.Call):
        names = extract_symbol_names(expr.func)
        for arg in expr.args:
            names.extend(extract_symbol_names(arg))
        for kw in expr.keywords:
            names.extend(extract_symbol_names(kw.value))
        return names
    return []


def literal_string(expr: ast.AST | None) -> str | None:
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return expr.value
    return None


def extract_pipeline_configs(root: Path) -> list[dict[str, Any]]:
    pf = root / "src" / "bioetl" / "composition" / "factories" / "pipeline_factories.py"
    if not pf.exists():
        return []
    source = read_text(pf)
    tree = ast.parse(source)
    configs: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "PipelineFactoryConfig":
            continue
        kwargs = {kw.arg: kw.value for kw in node.keywords if kw.arg}
        pipeline_name = literal_string(kwargs.get("pipeline_name"))
        provider = literal_string(kwargs.get("provider")) or ""
        if not pipeline_name:
            continue
        symbols: list[str] = []
        for key in ("transformer_class", "silver_schema", "gold_schema", "pandera_silver_schema"):
            symbols.extend(extract_symbol_names(kwargs.get(key)))
        configs.append(
            {
                "pipeline_name": pipeline_name,
                "provider": provider,
                "symbols": sorted(set(symbols)),
            }
        )
    configs.sort(key=lambda item: item["pipeline_name"])
    return configs


def build_pipeline_scopes(
    root: Path,
    pipeline_configs: list[dict[str, Any]],
    name_to_decl_files: dict[str, set[str]],
    file_token_counts: dict[str, Counter[str]],
) -> dict[str, set[str]]:
    scopes: dict[str, set[str]] = {}
    for cfg in pipeline_configs:
        pipeline_name = cfg["pipeline_name"]
        provider = cfg["provider"]
        scope_files: set[str] = set()

        # Files that explicitly mention the pipeline key.
        for file_rel, counter in file_token_counts.items():
            if pipeline_name in counter:
                scope_files.add(file_rel)

        # Provider-local code and configs.
        provider_paths = [
            root / "src" / "bioetl" / "application" / "pipelines" / provider,
            root / "src" / "bioetl" / "infrastructure" / "adapters" / provider,
            root / "src" / "bioetl" / "domain" / "schemas" / provider,
            root / "configs" / "pipelines" / provider,
        ]
        for p in provider_paths:
            if not p.exists():
                continue
            for child in p.rglob("*"):
                if child.is_file():
                    scope_files.add(rel(child, root))

        # Files that define core symbols selected in the pipeline config.
        for symbol in cfg["symbols"]:
            scope_files.update(name_to_decl_files.get(symbol, set()))

        # Core composition files always involved in registration/runtime assembly.
        always = (
            "src/bioetl/composition/factories/pipeline_factories.py",
            "src/bioetl/composition/factories/pipeline_factory.py",
            "src/bioetl/composition/factories/services_factory.py",
            "src/bioetl/composition/providers/registration.py",
        )
        for file_rel in always:
            if (root / file_rel).exists():
                scope_files.add(file_rel)

        scopes[pipeline_name] = scope_files
    return scopes


def classify_entity(
    entity: EntityRecord,
    token_counts: dict[str, Counter[str]],
    file_token_counts: dict[str, Counter[str]],
) -> tuple[str, int, int, int]:
    src_refs = token_counts["src"].get(entity.name, 0)
    test_refs = token_counts["tests"].get(entity.name, 0)
    docs_refs = token_counts["docs"].get(entity.name, 0)

    self_refs = file_token_counts.get(entity.file, Counter()).get(entity.name, 0)
    external_src_refs = max(src_refs - self_refs, 0)

    if external_src_refs > 0 and test_refs > 0:
        classification = "ACTIVE"
    elif external_src_refs > 0 and test_refs == 0:
        classification = "PRODUCTION_ONLY"
    elif external_src_refs == 0 and test_refs > 0:
        classification = "TEST_ONLY"
    else:
        classification = "DEAD"
    return classification, external_src_refs, test_refs, docs_refs


def is_pascal_case(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Z][A-Za-z0-9]*", name))


def is_snake_case(name: str) -> bool:
    return bool(re.fullmatch(r"[a-z_][a-z0-9_]*", name))


def collect_naming_violations(entities: list[EntityRecord]) -> list[ArchitectureViolation]:
    violations: list[ArchitectureViolation] = []
    for entity in entities:
        if entity.entity_type == "class" and not is_pascal_case(entity.name):
            violations.append(
                ArchitectureViolation(
                    category="naming",
                    severity="MEDIUM",
                    file=entity.file,
                    line=entity.line,
                    source_layer=entity.layer,
                    target=entity.name,
                    message="Class name is not PascalCase",
                    rule="Naming policy: classes must be PascalCase",
                )
            )
        if entity.entity_type in {"function", "method"}:
            if entity.name.startswith("__") and entity.name.endswith("__"):
                continue
            if not is_snake_case(entity.name):
                violations.append(
                    ArchitectureViolation(
                        category="naming",
                        severity="LOW",
                        file=entity.file,
                        line=entity.line,
                        source_layer=entity.layer,
                        target=entity.name,
                        message="Function/method name is not snake_case",
                        rule="Naming policy: functions must be snake_case",
                    )
                )
    return violations


def is_type_checking_expr(node: ast.expr) -> bool:
    if isinstance(node, ast.Name):
        return node.id == "TYPE_CHECKING"
    if isinstance(node, ast.Attribute):
        return node.attr == "TYPE_CHECKING"
    if isinstance(node, ast.Compare):
        return is_type_checking_expr(node.left)
    if isinstance(node, ast.BoolOp):
        return any(is_type_checking_expr(v) for v in node.values)
    return False


def resolve_relative_import(current_module: str, level: int, module: str | None) -> str:
    if level == 0:
        return module or ""
    parts = current_module.split(".")
    # Remove module name by one level for relative import logic.
    if len(parts) > 0:
        parts = parts[:-1]
    if level > len(parts):
        base: list[str] = []
    else:
        base = parts[: len(parts) - level + 1]
    if module:
        return ".".join(base + module.split("."))
    return ".".join(base)


class ImportCollector(ast.NodeVisitor):
    def __init__(self, current_module: str):
        self.current_module = current_module
        self.in_type_checking = 0
        self.imports: list[tuple[str, int, bool]] = []

    def visit_If(self, node: ast.If) -> Any:
        if is_type_checking_expr(node.test):
            self.in_type_checking += 1
            for stmt in node.body:
                self.visit(stmt)
            self.in_type_checking -= 1
            for stmt in node.orelse:
                self.visit(stmt)
            return
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> Any:
        for alias in node.names:
            self.imports.append((alias.name, node.lineno, self.in_type_checking > 0))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        target = resolve_relative_import(self.current_module, node.level, node.module)
        self.imports.append((target, node.lineno, self.in_type_checking > 0))


def collect_layer_import_violations(root: Path, src_py_files: list[Path]) -> list[ArchitectureViolation]:
    allowed = {
        "domain": {"domain"},
        "application": {"application", "domain"},
        "infrastructure": {"infrastructure", "domain"},
        "composition": {"composition", "infrastructure", "application", "domain"},
        "interfaces": {"interfaces", "composition", "infrastructure", "application", "domain"},
    }
    violations: list[ArchitectureViolation] = []

    for path in src_py_files:
        file_rel = rel(path, root)
        source_layer, current_module = module_from_src_path(file_rel)
        if source_layer not in allowed:
            continue
        source = read_text(path)
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        collector = ImportCollector(current_module=current_module)
        collector.visit(tree)

        for import_target, line, type_checking in collector.imports:
            if type_checking:
                continue
            if not import_target:
                continue
            # Enforce "domain has no external IO imports"
            if source_layer == "domain":
                if any(
                    import_target.startswith(prefix)
                    for prefix in (
                        "requests",
                        "httpx",
                        "aiohttp",
                        "sqlalchemy",
                        "deltalake",
                        "boto3",
                        "psycopg2",
                        "pymongo",
                    )
                ):
                    violations.append(
                        ArchitectureViolation(
                            category="import_boundary",
                            severity="CRITICAL",
                            file=file_rel,
                            line=line,
                            source_layer=source_layer,
                            target=import_target,
                            message="Domain layer imports external IO dependency",
                            rule="Domain must be pure and contain no IO imports",
                        )
                    )

            if not import_target.startswith("bioetl."):
                continue
            target_parts = import_target.split(".")
            if len(target_parts) < 2:
                continue
            target_layer = target_parts[1]
            if target_layer not in allowed:
                continue

            # Allowed exceptions from architecture-guardian skill.
            if import_target.startswith("bioetl.domain.types"):
                continue
            if import_target.startswith("bioetl.domain.exceptions"):
                continue
            if source_layer == "infrastructure" and import_target.startswith("bioetl.domain.ports"):
                continue

            if target_layer not in allowed[source_layer]:
                violations.append(
                    ArchitectureViolation(
                        category="import_boundary",
                        severity="CRITICAL",
                        file=file_rel,
                        line=line,
                        source_layer=source_layer,
                        target=import_target,
                        message=f"Disallowed layer import: {source_layer} -> {target_layer}",
                        rule="Hexagonal import matrix (architecture-guardian)",
                    )
                )
    return violations

def collect_antipattern_violations(root: Path, src_py_files: list[Path]) -> list[ArchitectureViolation]:
    violations: list[ArchitectureViolation] = []
    for path in src_py_files:
        file_rel = rel(path, root)
        layer, _ = module_from_src_path(file_rel)
        source = read_text(path)
        for idx, line in enumerate(source.splitlines(), start=1):
            stripped = line.strip()
            if "print(" in line and "# noqa" not in line:
                violations.append(
                    ArchitectureViolation(
                        category="anti_pattern",
                        severity="MEDIUM",
                        file=file_rel,
                        line=idx,
                        source_layer=layer,
                        target="print(",
                        message="print() usage detected",
                        rule="Use LoggerPort/structured logging",
                    )
                )
            if layer in {"application", "interfaces", "domain"} and (
                re.search(r"^\s*import\s+structlog\b", line)
                or re.search(r"^\s*from\s+structlog\b", line)
            ):
                violations.append(
                    ArchitectureViolation(
                        category="anti_pattern",
                        severity="HIGH",
                        file=file_rel,
                        line=idx,
                        source_layer=layer,
                        target="structlog",
                        message="Direct structlog import in high-level layer",
                        rule="Use LoggerPort abstraction in non-infrastructure layers",
                    )
                )
            if layer in {"application", "domain"} and re.search(
                r"\bself\.[A-Za-z_][A-Za-z0-9_]*\s*=\s*[A-Z][A-Za-z0-9_]*\s*\(",
                line,
            ):
                violations.append(
                    ArchitectureViolation(
                        category="di_violation",
                        severity="HIGH",
                        file=file_rel,
                        line=idx,
                        source_layer=layer,
                        target=stripped,
                        message="Possible hard-coded dependency instantiation in class",
                        rule="Dependencies should be injected, not instantiated in application/domain",
                    )
                )
            if layer in {"application", "domain"} and re.search(
                r"^\s{4,}[a-z_][a-z0-9_]*\s*=\s*[A-Z][A-Za-z0-9_]*\s*\(",
                line,
            ):
                violations.append(
                    ArchitectureViolation(
                        category="di_violation",
                        severity="MEDIUM",
                        file=file_rel,
                        line=idx,
                        source_layer=layer,
                        target=stripped,
                        message="Possible method-level concrete instantiation",
                        rule="Avoid method-level concrete construction in business layers",
                    )
                )
            if re.search(r"(ServiceLocator|Container\.resolve|Locator\.get)\b", line):
                violations.append(
                    ArchitectureViolation(
                        category="di_violation",
                        severity="CRITICAL",
                        file=file_rel,
                        line=idx,
                        source_layer=layer,
                        target=stripped,
                        message="Service locator pattern detected",
                        rule="Disallow service locator in codebase",
                    )
                )
            if re.search(r"=\s*(-1|9999|['\"]N/A['\"])\b", line):
                violations.append(
                    ArchitectureViolation(
                        category="anti_pattern",
                        severity="MEDIUM",
                        file=file_rel,
                        line=idx,
                        source_layer=layer,
                        target=stripped,
                        message="Sentinel value detected",
                        rule="Prefer None/Optional over sentinel values",
                    )
                )
    return violations


def parse_markdown_links(text: str) -> list[str]:
    links = re.findall(r"\[[^\]]*\]\(([^)]+)\)", text)
    links.extend(re.findall(r"<((?:\.\.?/|/)?[^>]+\.md(?:#[^>]*)?)>", text))
    return links


def normalize_doc_ref(base_doc_rel: str, link: str) -> str | None:
    link = link.strip()
    if not link or link.startswith(("http://", "https://", "mailto:", "#")):
        return None
    link = link.split("#", 1)[0].split("?", 1)[0]
    if not link:
        return None
    # README and absolute-style doc links.
    if link.startswith("docs/"):
        return link
    base_path = Path(base_doc_rel)
    if base_doc_rel.startswith("docs/"):
        resolved = (base_path.parent / link).as_posix()
        if resolved.startswith("docs/"):
            return resolved
        return f"docs/{resolved}".replace("//", "/")
    return link


def collect_doc_refs(root: Path, tracked_files: list[Path]) -> tuple[set[str], dict[str, set[str]], dict[str, str]]:
    docs_md_files: set[str] = set()
    doc_contents: dict[str, str] = {}
    for path in tracked_files:
        rel_path = rel(path, root)
        if rel_path.startswith("docs/") and path.suffix.lower() == ".md":
            docs_md_files.add(rel_path)
            doc_contents[rel_path] = read_text(path)
    if (root / "README.md").exists():
        doc_contents["README.md"] = read_text(root / "README.md")
    if (root / "mkdocs.yml").exists():
        doc_contents["mkdocs.yml"] = read_text(root / "mkdocs.yml")

    inbound: dict[str, set[str]] = defaultdict(set)
    nav_refs: set[str] = set()

    mkdocs_path = root / "mkdocs.yml"
    if mkdocs_path.exists():
        mkdocs_text = read_text(mkdocs_path)
        if yaml is not None:
            try:
                mkdocs_data = yaml.safe_load(mkdocs_text) or {}
            except Exception:
                mkdocs_data = {}

            def walk_nav(node: Any) -> None:
                if isinstance(node, dict):
                    for _, value in node.items():
                        walk_nav(value)
                elif isinstance(node, list):
                    for item in node:
                        walk_nav(item)
                elif isinstance(node, str) and node.endswith(".md"):
                    nav_refs.add(f"docs/{node}".replace("//", "/"))

            walk_nav(mkdocs_data.get("nav", []))
        else:
            for match in re.findall(r":\s*([A-Za-z0-9_\-./]+\.md)\s*$", mkdocs_text, flags=re.MULTILINE):
                nav_refs.add(f"docs/{match}".replace("//", "/"))

    for target in nav_refs:
        inbound[target].add("mkdocs.yml")

    for source_rel, text in doc_contents.items():
        for raw_link in parse_markdown_links(text):
            target = normalize_doc_ref(source_rel, raw_link)
            if not target:
                continue
            if target.startswith("docs/") and target.endswith(".md"):
                inbound[target].add(source_rel)

    return docs_md_files, inbound, doc_contents


def extract_rules_requirements_versions(rules_text: str, req_text: str) -> tuple[str | None, str | None, str | None]:
    rules_version = None
    req_version = None
    req_synced_rules_version = None

    rules_match = VERSION_RE.search(rules_text)
    if rules_match:
        rules_version = rules_match.group(1)
    req_match = VERSION_RE.search(req_text)
    if req_match:
        req_version = req_match.group(1)
    sync_match = re.search(r"RULES\.md\s*v([0-9]+(?:\.[0-9]+)+)", req_text, flags=re.IGNORECASE)
    if sync_match:
        req_synced_rules_version = sync_match.group(1)
    return rules_version, req_version, req_synced_rules_version


def build_documentation_findings(
    root: Path,
    docs_md_files: set[str],
    inbound_refs: dict[str, set[str]],
    doc_contents: dict[str, str],
    pipeline_names: list[str],
) -> tuple[list[tuple[str, str]], list[str], list[str], list[str], list[str]]:
    findings: list[tuple[str, str]] = []

    # Orphan docs (exclude archives and known entry points).
    orphan_candidates: list[str] = []
    for doc in sorted(docs_md_files):
        if doc.startswith("docs/99-archive/"):
            continue
        if doc.endswith("/README.md") or doc.endswith("/index.md"):
            continue
        if not inbound_refs.get(doc):
            orphan_candidates.append(doc)

    for orphan in orphan_candidates:
        findings.append(
            (
                "Medium",
                f"Potential orphan documentation file (no inbound refs): `{orphan}`",
            )
        )

    # ADR visibility checks in main docs.
    top_docs = {
        "README.md": doc_contents.get("README.md", ""),
        "docs/00-project/RULES.md": doc_contents.get("docs/00-project/RULES.md", ""),
        "docs/01-requirements/REQUIREMENTS.md": doc_contents.get("docs/01-requirements/REQUIREMENTS.md", ""),
    }
    for adr in ADR_IDS:
        present_in = [path for path, text in top_docs.items() if adr in text]
        if not present_in:
            findings.append(("High", f"{adr} is not referenced in top-level governance docs"))

    # RULES and REQUIREMENTS sync checks.
    rules_text = top_docs.get("docs/00-project/RULES.md", "")
    req_text = top_docs.get("docs/01-requirements/REQUIREMENTS.md", "")
    rules_version, req_version, req_synced_rules_version = extract_rules_requirements_versions(
        rules_text, req_text
    )
    if rules_version and req_synced_rules_version and rules_version != req_synced_rules_version:
        findings.append(
            (
                "High",
                "REQUIREMENTS sync declaration does not match RULES version "
                f"(RULES={rules_version}, REQUIREMENTS says RULES v{req_synced_rules_version})",
            )
        )
    if not rules_version or not req_version:
        findings.append(("Medium", "Could not reliably parse RULES/REQUIREMENTS version headers"))

    req_ids = sorted(set(REQ_ID_RE.findall(req_text)))
    rules_req_mentions = sorted(set(REQ_ID_RE.findall(rules_text)))
    if req_ids and not rules_req_mentions:
        findings.append(
            (
                "Medium",
                "RULES does not reference any REQ-* IDs from REQUIREMENTS (traceability gap)",
            )
        )

    # Pipeline documentation coverage.
    combined_docs_text = "\n".join(doc_contents.values())
    missing_pipeline_docs: list[str] = []
    for pipeline in pipeline_names:
        variants = {pipeline, pipeline.replace("_", "-"), pipeline.replace("_", " ")}
        if not any(re.search(rf"\b{re.escape(v)}\b", combined_docs_text, flags=re.IGNORECASE) for v in variants):
            missing_pipeline_docs.append(pipeline)
    if missing_pipeline_docs:
        findings.append(
            (
                "High",
                "Pipelines with no explicit documentation mention: "
                + ", ".join(missing_pipeline_docs),
            )
        )

    # Provider documentation coverage.
    providers = sorted({name.split("_", 1)[0] for name in pipeline_names if "_" in name})
    missing_provider_docs: list[str] = []
    for provider in providers:
        has_ref_provider_dir = any(
            p.startswith(f"docs/04-reference/providers/{provider}/") for p in docs_md_files
        )
        has_legacy_provider_doc = f"docs/providers/{provider}.md" in docs_md_files
        if not has_ref_provider_dir and not has_legacy_provider_doc:
            missing_provider_docs.append(provider)
    if missing_provider_docs:
        findings.append(
            (
                "High",
                "Providers without docs in `docs/04-reference/providers/` or `docs/providers/`: "
                + ", ".join(missing_provider_docs),
            )
        )

    # Contract coverage: expect one gold schema JSON per pipeline.
    contract_dir = root / "docs" / "04-reference" / "contracts" / "gold"
    contract_files = {
        p.name for p in contract_dir.glob("*.json")
    } if contract_dir.exists() else set()
    missing_contract_docs: list[str] = []
    for pipeline in pipeline_names:
        expected = f"{pipeline}_v1.0.json"
        if expected not in contract_files:
            missing_contract_docs.append(expected)
    if missing_contract_docs:
        findings.append(
            (
                "Medium",
                "Missing gold contract docs for pipelines: " + ", ".join(missing_contract_docs),
            )
        )

    # Broken mkdocs nav references.
    broken_nav: list[str] = []
    mkdocs_refs = sorted(
        target for target, sources in inbound_refs.items() if "mkdocs.yml" in sources
    )
    for target in mkdocs_refs:
        if not (root / target).exists():
            broken_nav.append(target)
    if broken_nav:
        findings.append(
            (
                "Critical",
                "Broken mkdocs nav references: " + ", ".join(broken_nav),
            )
        )

    return findings, orphan_candidates, missing_pipeline_docs, missing_provider_docs, missing_contract_docs


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

def main() -> None:
    started_at = datetime.now(timezone.utc)
    script_path = Path(__file__).resolve()
    root = find_repo_root(script_path)
    out_dir = script_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    tracked_files = git_ls_files(root)
    src_py_files = [p for p in tracked_files if classify_file(p, root) == "src_py"]
    tests_py_files = [p for p in tracked_files if classify_file(p, root) == "tests_py"]

    # File inventory (all tracked files)
    file_inventory_rows: list[dict[str, Any]] = []
    for path in tracked_files:
        kind = classify_file(path, root)
        file_inventory_rows.append(
            {
                "file": rel(path, root),
                "kind": kind,
                "size_bytes": path.stat().st_size if path.exists() else 0,
            }
        )
    file_inventory_rows.sort(key=lambda r: r["file"])
    write_csv(
        out_dir / "files_inventory.csv",
        file_inventory_rows,
        ["file", "kind", "size_bytes"],
    )

    # Entities and token usage.
    entities = collect_entities(root, src_py_files)
    token_counts, token_files, file_token_counts = collect_tokens_by_group(root, tracked_files)

    name_to_decl_files: dict[str, set[str]] = defaultdict(set)
    for entity in entities:
        name_to_decl_files[entity.name].add(entity.file)

    pipeline_configs = extract_pipeline_configs(root)
    pipeline_names = [cfg["pipeline_name"] for cfg in pipeline_configs]
    pipeline_scopes = build_pipeline_scopes(root, pipeline_configs, name_to_decl_files, file_token_counts)

    # Build entity rows.
    entity_rows: list[dict[str, Any]] = []
    dead_rows: list[dict[str, Any]] = []
    for entity in entities:
        classification, src_refs, test_refs, docs_refs = classify_entity(
            entity,
            token_counts,
            file_token_counts,
        )
        tests_files = sorted(token_files["tests"].get(entity.name, set()))
        docs_files = sorted(token_files["docs"].get(entity.name, set()))
        tests_files_short = ";".join(tests_files[:25])
        docs_files_short = ";".join(docs_files[:25])

        row: dict[str, Any] = {
            "entity_type": entity.entity_type,
            "name": entity.name,
            "qualname": entity.qualname,
            "scope": entity.scope,
            "layer": entity.layer,
            "module": entity.module,
            "declaration": f"{entity.file}:{entity.line}",
            "line_start": entity.line,
            "line_end": entity.end_line,
            "loc": entity.loc,
            "src_refs_external": src_refs,
            "test_refs": test_refs,
            "docs_refs": docs_refs,
            "classification": classification,
            "tests_files": tests_files_short,
            "docs_files": docs_files_short,
            "tests_files_count": len(tests_files),
            "docs_files_count": len(docs_files),
        }

        for pipeline_name in pipeline_names:
            scope_files = pipeline_scopes.get(pipeline_name, set())
            pipeline_ref_count = 0
            for scope_file in scope_files:
                pipeline_ref_count += file_token_counts.get(scope_file, Counter()).get(entity.name, 0)
            row[pipeline_name] = pipeline_ref_count

        entity_rows.append(row)

        exempt = False
        exempt_reason = ""
        if classification == "DEAD":
            if entity.entity_type == "class" and (
                entity.name.endswith("Port")
                or entity.name.endswith("Schema")
                or entity.name.endswith("Protocol")
            ):
                exempt = True
                exempt_reason = "Port/Schema/Protocol contract"
        if classification == "DEAD":
            dead_rows.append(
                {
                    **row,
                    "exempt": exempt,
                    "exempt_reason": exempt_reason,
                }
            )

    # Main entity outputs.
    base_fields = [
        "entity_type",
        "name",
        "qualname",
        "scope",
        "layer",
        "module",
        "declaration",
        "line_start",
        "line_end",
        "loc",
        "src_refs_external",
        "test_refs",
        "docs_refs",
        "classification",
        "tests_files_count",
        "tests_files",
        "docs_files_count",
        "docs_files",
    ]
    entity_rows.sort(key=lambda r: (r["layer"], r["module"], r["line_start"], r["name"]))
    write_csv(
        out_dir / "entities.csv",
        entity_rows,
        base_fields,
    )
    write_csv(
        out_dir / "entities_pipeline_matrix.csv",
        entity_rows,
        base_fields + pipeline_names,
    )
    write_csv(
        out_dir / "dead_code_candidates.csv",
        dead_rows,
        base_fields + ["exempt", "exempt_reason"] + pipeline_names,
    )

    # Duplicate names.
    dup_name_rows: list[dict[str, Any]] = []
    by_name_type: dict[tuple[str, str], list[EntityRecord]] = defaultdict(list)
    for entity in entities:
        by_name_type[(entity.entity_type, entity.name)].append(entity)
    for (entity_type, name), items in by_name_type.items():
        unique_modules = sorted({item.module for item in items})
        if len(unique_modules) <= 1:
            continue
        dup_name_rows.append(
            {
                "entity_type": entity_type,
                "name": name,
                "definitions": len(items),
                "modules": ";".join(unique_modules),
                "locations": ";".join(f"{i.file}:{i.line}" for i in sorted(items, key=lambda x: (x.file, x.line))[:50]),
            }
        )
    dup_name_rows.sort(key=lambda r: (-r["definitions"], r["name"]))
    write_csv(
        out_dir / "duplicate_names.csv",
        dup_name_rows,
        ["entity_type", "name", "definitions", "modules", "locations"],
    )

    # Duplicate logic by body hash.
    dup_logic_rows: list[dict[str, Any]] = []
    by_hash: dict[str, list[EntityRecord]] = defaultdict(list)
    for entity in entities:
        if entity.body_hash and entity.entity_type in {"class", "function", "method"} and entity.loc >= 3:
            by_hash[entity.body_hash].append(entity)
    for body_hash_value, items in by_hash.items():
        if len(items) <= 1:
            continue
        rows = sorted(items, key=lambda x: (x.file, x.line))
        dup_logic_rows.append(
            {
                "hash": body_hash_value,
                "count": len(rows),
                "loc": rows[0].loc,
                "entities": ";".join(f"{r.qualname}@{r.file}:{r.line}" for r in rows[:80]),
            }
        )
    dup_logic_rows.sort(key=lambda r: (-r["count"], -r["loc"]))
    write_csv(
        out_dir / "duplicate_logic.csv",
        dup_logic_rows,
        ["hash", "count", "loc", "entities"],
    )

    # Architecture audit.
    arch_violations = []
    arch_violations.extend(collect_layer_import_violations(root, src_py_files))
    arch_violations.extend(collect_antipattern_violations(root, src_py_files))
    arch_violations.extend(collect_naming_violations(entities))
    arch_violations_rows = [asdict(v) for v in arch_violations]
    arch_violations_rows.sort(key=lambda r: (r["severity"], r["file"], r["line"]))
    write_csv(
        out_dir / "architecture_violations.csv",
        arch_violations_rows,
        ["category", "severity", "file", "line", "source_layer", "target", "message", "rule"],
    )

    # Documentation audit.
    docs_md_files, inbound_refs, doc_contents = collect_doc_refs(root, tracked_files)
    (
        doc_findings,
        orphan_docs,
        missing_pipeline_docs,
        missing_provider_docs,
        missing_contract_docs,
    ) = build_documentation_findings(
        root=root,
        docs_md_files=docs_md_files,
        inbound_refs=inbound_refs,
        doc_contents=doc_contents,
        pipeline_names=pipeline_names,
    )

    # Architecture markdown report.
    arch_report_path = out_dir / "architecture_report.md"
    by_severity = Counter(v.severity for v in arch_violations)
    by_category = Counter(v.category for v in arch_violations)
    top_critical = [
        v for v in sorted(arch_violations, key=lambda x: (x.file, x.line)) if v.severity == "CRITICAL"
    ][:120]
    arch_report = [
        "# Architecture Validation Report",
        "",
        f"**Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "**Scope**: `src/bioetl/**/*.py`",
        f"**Status**: {'FAIL' if by_severity.get('CRITICAL', 0) else 'WARN' if arch_violations else 'PASS'}",
        "",
        "## Summary",
        "| Category | Issues |",
        "|---|---:|",
    ]
    for category, count in sorted(by_category.items()):
        arch_report.append(f"| {category} | {count} |")
    arch_report.extend(
        [
            "",
            "## Severity",
            "| Severity | Count |",
            "|---|---:|",
        ]
    )
    for severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        arch_report.append(f"| {severity} | {by_severity.get(severity, 0)} |")
    arch_report.extend(
        [
            "",
            "## Critical Issues",
        ]
    )
    if top_critical:
        for issue in top_critical:
            arch_report.extend(
                [
                    f"### {issue.category}",
                    f"- **File**: `{issue.file}:{issue.line}`",
                    f"- **Violation**: {issue.message}",
                    f"- **Target**: `{issue.target}`",
                    f"- **Rule**: {issue.rule}",
                    "",
                ]
            )
    else:
        arch_report.append("- No critical architecture violations detected.")
    arch_report_path.write_text("\n".join(arch_report), encoding="utf-8")

    # Documentation report using skill template.
    doc_report_path = out_dir / "documentation_audit_report.md"
    findings_by_severity: dict[str, list[str]] = defaultdict(list)
    for sev, msg in doc_findings:
        findings_by_severity[sev].append(msg)

    def section_lines(severity: str) -> list[str]:
        entries = findings_by_severity.get(severity, [])
        if not entries:
            return ["- None"]
        return [f"- {entry}" for entry in entries]

    doc_report_lines = [
        "# Documentation Audit Report (BioETL v5.14+)",
        "",
        "## Summary",
        f"- Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "- Scope: `docs/**`, `README.md`, `mkdocs.yml`, alignment with code in `src/bioetl/**`",
        "- Overall status: "
        + ("FAIL" if findings_by_severity.get("Critical") else "WARN" if doc_findings else "PASS"),
        "",
        "## Inventory",
        f"- Docs scanned: {len(docs_md_files)} markdown files under `docs/`",
        "- Entry points (README.md, mkdocs.yml): scanned",
        "",
        "## Findings by severity",
        "### Critical",
        *section_lines("Critical"),
        "",
        "### High",
        *section_lines("High"),
        "",
        "### Medium",
        *section_lines("Medium"),
        "",
        "### Low",
        *section_lines("Low"),
        "",
        "## Proposed changes (prioritized)",
        "1. Fix Critical/High nav and coverage gaps first (`mkdocs.yml` broken refs, missing provider/pipeline docs).",
        "2. Resolve RULES/REQUIREMENTS traceability gaps and enforce REQ-ID cross links.",
        "3. Archive or re-link orphan docs that are still relevant.",
        "",
        "## Required decisions",
        "- Confirm whether orphan docs should be archived (`docs/99-archive`) or linked into nav.",
        "- Confirm expected contract versioning pattern (`*_v1.0.json`) for all active pipelines.",
        "",
        "## Updated files (if changes applied)",
        "- No documentation files were modified by this audit run.",
        "",
        "## Dead or orphan docs (candidates)",
    ]
    if orphan_docs:
        doc_report_lines.extend(f"- `{item}`" for item in orphan_docs[:300])
    else:
        doc_report_lines.append("- None")
    doc_report_lines.extend(
        [
            "",
            "## Verification",
            f"- RULES.md and REQUIREMENTS.md sync: {'WARN' if findings_by_severity.get('High') else 'OK/No critical mismatch detected'}",
            "- ADR alignment (ADR-010, ADR-014, ADR-017): "
            + ("WARN" if any("ADR-" in msg for _, msg in doc_findings) else "OK"),
            f"- Link check: {'FAIL' if findings_by_severity.get('Critical') else 'WARN/OK'}",
            "",
            "## Extra Coverage Gaps",
            f"- Missing pipeline docs mentions: {', '.join(missing_pipeline_docs) if missing_pipeline_docs else 'none'}",
            f"- Missing provider docs: {', '.join(missing_provider_docs) if missing_provider_docs else 'none'}",
            f"- Missing contract docs: {', '.join(missing_contract_docs) if missing_contract_docs else 'none'}",
        ]
    )
    doc_report_path.write_text("\n".join(doc_report_lines), encoding="utf-8")

    # Global summary for the user's requested deliverable.
    summary_path = out_dir / "full_audit_summary.md"
    classification_counts = Counter(row["classification"] for row in entity_rows)
    dead_non_exempt = [r for r in dead_rows if not r.get("exempt")]
    duplicate_name_count = len(dup_name_rows)
    duplicate_logic_count = len(dup_logic_rows)
    summary_lines = [
        "# Full Codebase Audit Summary",
        "",
        f"- Timestamp (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Total tracked files audited: {len(tracked_files)}",
        f"- Python source files audited (`src/`): {len(src_py_files)}",
        f"- Python test files indexed (`tests/`): {len(tests_py_files)}",
        f"- Entities cataloged (classes/functions/constants/variables/parameters): {len(entity_rows)}",
        f"- Pipelines in matrix: {len(pipeline_names)}",
        "",
        "## Entity Classification",
        "| Classification | Count |",
        "|---|---:|",
        f"| ACTIVE | {classification_counts.get('ACTIVE', 0)} |",
        f"| PRODUCTION_ONLY | {classification_counts.get('PRODUCTION_ONLY', 0)} |",
        f"| TEST_ONLY | {classification_counts.get('TEST_ONLY', 0)} |",
        f"| DEAD | {classification_counts.get('DEAD', 0)} |",
        "",
        "## Risk Highlights",
        f"- Dead code candidates (non-exempt): {len(dead_non_exempt)}",
        f"- Duplicate names: {duplicate_name_count}",
        f"- Duplicate logic groups: {duplicate_logic_count}",
        f"- Architecture violations: {len(arch_violations)}",
        f"- Documentation findings: {len(doc_findings)}",
        "",
        "## Output Files",
        "- `files_inventory.csv`",
        "- `entities.csv`",
        "- `entities_pipeline_matrix.csv`",
        "- `dead_code_candidates.csv`",
        "- `duplicate_names.csv`",
        "- `duplicate_logic.csv`",
        "- `architecture_violations.csv`",
        "- `architecture_report.md`",
        "- `documentation_audit_report.md`",
        "- `metadata.json`",
        "",
        "## Notes on Method",
        "- The matrix columns for pipelines are generated from `PIPELINE_CONFIGS` in "
        "`src/bioetl/composition/factories/pipeline_factories.py`.",
        "- Pipeline usage counts are direct lexical references of entity names inside "
        "pipeline scopes (provider files + config-linked symbols + runtime composition files).",
        "- Dead/duplicate classification is static and should be validated against runtime behavior "
        "for removals.",
    ]
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")

    finished_at = datetime.now(timezone.utc)
    metadata = {
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": finished_at.isoformat(),
        "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
        "repo_root": str(root),
        "output_dir": str(out_dir),
        "tracked_files": len(tracked_files),
        "src_py_files": len(src_py_files),
        "tests_py_files": len(tests_py_files),
        "entities": len(entity_rows),
        "pipelines": pipeline_names,
        "dead_non_exempt": len(dead_non_exempt),
        "duplicate_names": duplicate_name_count,
        "duplicate_logic_groups": duplicate_logic_count,
        "architecture_violations": len(arch_violations),
        "documentation_findings": len(doc_findings),
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
