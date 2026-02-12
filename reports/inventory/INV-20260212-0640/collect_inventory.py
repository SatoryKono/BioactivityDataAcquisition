"""Inventory audit helper for BioETL.

Builds object registry, reference counts, duplicate detection, and
dependency map for src/bioetl and renders markdown report.
"""

from __future__ import annotations

# ruff: noqa

import ast
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from hashlib import sha256
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "bioetl"
TESTS = ROOT / "tests"
TASK_ID = Path(__file__).parent.name
OUT_DIR = Path(__file__).parent
LAYER_ORDER = ["domain", "application", "infrastructure", "composition", "interfaces"]


def atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def path_to_module(path: Path) -> Tuple[str, str]:
    rel = path.relative_to(SRC)
    parts = rel.with_suffix("").parts
    layer = parts[0]
    module = ".".join(["bioetl"] + list(parts))
    return layer, module


def format_args(args: ast.arguments) -> str:
    def fmt_default(node: Optional[ast.AST]) -> Optional[str]:
        if node is None:
            return None
        return ast.unparse(node).strip()

    def fmt_arg(arg: ast.arg, default: Optional[str] = None) -> str:
        ann = ast.unparse(arg.annotation).strip() if arg.annotation else ""
        prefix = f"{arg.arg}: {ann}" if ann else arg.arg
        if default is None:
            return prefix
        return f"{prefix} = {default}"

    items: List[str] = []

    positional = list(args.posonlyargs) + list(args.args)
    defaults_raw = [fmt_default(d) for d in args.defaults]
    defaults: List[Optional[str]] = [None] * (
        len(positional) - len(defaults_raw)
    ) + defaults_raw

    for idx, (arg, default) in enumerate(zip(positional, defaults)):
        items.append(fmt_arg(arg, default))
        if args.posonlyargs and idx + 1 == len(args.posonlyargs):
            items.append("/")

    if args.vararg:
        var_ann = (
            ast.unparse(args.vararg.annotation).strip()
            if args.vararg.annotation
            else ""
        )
        var_piece = f"*{args.vararg.arg}"
        if var_ann:
            var_piece += f": {var_ann}"
        items.append(var_piece)
    elif args.kwonlyargs:
        items.append("*")

    kw_defaults = [fmt_default(d) for d in args.kw_defaults]
    items.extend(
        fmt_arg(arg, default) for arg, default in zip(args.kwonlyargs, kw_defaults)
    )

    if args.kwarg:
        kw_ann = (
            ast.unparse(args.kwarg.annotation).strip() if args.kwarg.annotation else ""
        )
        kw_piece = f"**{args.kwarg.arg}"
        if kw_ann:
            kw_piece += f": {kw_ann}"
        items.append(kw_piece)

    return "(" + ", ".join(items) + ")"


def class_suffix(name: str) -> Optional[str]:
    suffixes = [
        "Factory",
        "Client",
        "Port",
        "Service",
        "Transformer",
        "Error",
        "Exception",
        "Schema",
        "Config",
    ]
    for suffix in suffixes:
        if name.endswith(suffix):
            return suffix
    return None


def is_upper_constant(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Z][A-Z0-9_]*", name))


def is_type_alias(name: str, value_src: str) -> bool:
    if not re.fullmatch(r"[A-Z][A-Za-z0-9_]*", name):
        return False
    patterns = [
        "TypeAlias",
        "TypeVar",
        "ParamSpec",
        "Annotated",
        "Union",
        "dict[",
        "list[",
        "tuple[",
    ]
    return any(pat in value_src for pat in patterns)


def strip_docstring(body: List[ast.stmt]) -> List[ast.stmt]:
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        return body[1:]
    return body


def body_hash(body: List[ast.stmt]) -> str:
    cleaned = strip_docstring(body)
    module = ast.Module(body=cleaned, type_ignores=[])
    dump = ast.dump(module, include_attributes=False)
    return sha256(dump.encode("utf-8")).hexdigest()


@dataclass
class ObjectRecord:
    layer: str
    module: str
    file: str
    type: str
    name: str
    line: int
    loc: int
    suffix: Optional[str] = None
    base_classes: Optional[List[str]] = None
    public_methods: Optional[List[str]] = None
    private_methods: Optional[List[str]] = None
    is_public: Optional[bool] = None
    signature: Optional[str] = None
    return_annotation: Optional[str] = None
    exports: Optional[List[str]] = None
    body_hash: Optional[str] = None

    @property
    def qualname(self) -> str:
        return f"{self.module}.{self.name}"


def parse_file(
    path: Path,
) -> Tuple[List[ObjectRecord], Counter, Counter, List[str], List[str]]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    layer, module = path_to_module(path)
    objects: List[ObjectRecord] = []
    names_counter: Counter = Counter()
    attrs_counter: Counter = Counter()
    defined_names: List[str] = []
    all_exports: List[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names_counter[node.id] += 1
        elif isinstance(node, ast.Attribute):
            attrs_counter[node.attr] += 1
        elif isinstance(node, ast.Import):
            for alias in node.names:
                target = alias.asname or alias.name.split(".")[-1]
                names_counter[target] += 1
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                target = alias.asname or alias.name
                names_counter[target] += 1

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            sig = format_args(node.args)
            ret = ast.unparse(node.returns).strip() if node.returns else None
            loc = (node.end_lineno or node.lineno) - node.lineno + 1
            obj = ObjectRecord(
                layer=layer,
                module=module,
                file=str(path),
                type="function",
                name=node.name,
                line=node.lineno,
                loc=loc,
                is_public=not node.name.startswith("_"),
                signature=sig,
                return_annotation=ret,
                body_hash=body_hash(node.body),
            )
            objects.append(obj)
            defined_names.append(node.name)
        elif isinstance(node, ast.ClassDef):
            bases = (
                [ast.unparse(base).strip() for base in node.bases] if node.bases else []
            )
            public_methods: List[str] = []
            private_methods: List[str] = []
            for m in node.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if m.name.startswith("_"):
                        private_methods.append(m.name)
                    else:
                        public_methods.append(m.name)
            loc = (node.end_lineno or node.lineno) - node.lineno + 1
            obj = ObjectRecord(
                layer=layer,
                module=module,
                file=str(path),
                type="class",
                name=node.name,
                line=node.lineno,
                loc=loc,
                base_classes=bases,
                suffix=class_suffix(node.name),
                public_methods=sorted(public_methods),
                private_methods=sorted(private_methods),
                body_hash=body_hash(node.body),
            )
            objects.append(obj)
            defined_names.append(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets: Iterable[ast.expr]
            if isinstance(node, ast.Assign):
                targets = node.targets
                value_src = ast.unparse(node.value).strip() if node.value else ""
            else:
                targets = [node.target]
                value_src = (
                    ast.unparse(node.annotation).strip() if node.annotation else ""
                )
            for t in targets:
                if isinstance(t, ast.Name):
                    name = t.id
                    if name == "__all__":
                        if isinstance(node, ast.Assign) and isinstance(
                            node.value, (ast.List, ast.Tuple)
                        ):
                            exports = [
                                elt.value
                                for elt in node.value.elts
                                if isinstance(elt, ast.Constant)
                                and isinstance(elt.value, str)
                            ]
                            all_exports.extend(exports)
                            objects.append(
                                ObjectRecord(
                                    layer=layer,
                                    module=module,
                                    file=str(path),
                                    type="__all__",
                                    name="__all__",
                                    line=node.lineno,
                                    loc=1,
                                    exports=exports,
                                )
                            )
                    elif is_upper_constant(name):
                        objects.append(
                            ObjectRecord(
                                layer=layer,
                                module=module,
                                file=str(path),
                                type="constant",
                                name=name,
                                line=node.lineno,
                                loc=1,
                                is_public=not name.startswith("_"),
                            )
                        )
                        defined_names.append(name)
                    elif is_type_alias(name, value_src):
                        objects.append(
                            ObjectRecord(
                                layer=layer,
                                module=module,
                                file=str(path),
                                type="type_alias",
                                name=name,
                                line=node.lineno,
                                loc=1,
                                is_public=not name.startswith("_"),
                            )
                        )
                        defined_names.append(name)

    return objects, names_counter, attrs_counter, defined_names, all_exports


def collect_objects() -> Tuple[List[ObjectRecord], dict, dict, dict]:
    objects: List[ObjectRecord] = []
    file_name_counts: dict[str, Counter] = {}
    file_attr_counts: dict[str, Counter] = {}
    module_defined: dict[str, List[str]] = {}
    module_all_exports: dict[str, List[str]] = {}

    for layer in LAYER_ORDER:
        for path in sorted((SRC / layer).rglob("*.py")):
            obj_list, names_counter, attrs_counter, defined_names, all_exports = (
                parse_file(path)
            )
            objects.extend(obj_list)
            file_name_counts[str(path)] = names_counter
            file_attr_counts[str(path)] = attrs_counter
            module_defined[str(path)] = defined_names
            module_all_exports[str(path)] = all_exports
    objects.sort(key=lambda o: (LAYER_ORDER.index(o.layer), o.module, o.type, o.name))
    return (
        objects,
        file_name_counts,
        file_attr_counts,
        {"defined": module_defined, "exports": module_all_exports},
    )


def collect_usage_counts(
    file_name_counts: dict[str, Counter], file_attr_counts: dict[str, Counter]
) -> Tuple[Counter, Counter, Counter, Counter]:
    prod_name = Counter()
    prod_attr = Counter()
    test_name = Counter()
    test_attr = Counter()

    for path, counter in file_name_counts.items():
        if path.startswith(str(SRC)):
            prod_name.update(counter)
        elif path.startswith(str(TESTS)):
            test_name.update(counter)
    for path, counter in file_attr_counts.items():
        if path.startswith(str(SRC)):
            prod_attr.update(counter)
        elif path.startswith(str(TESTS)):
            test_attr.update(counter)
    return prod_name, prod_attr, test_name, test_attr


def classify_object(
    obj: ObjectRecord,
    prod_name: Counter,
    prod_attr: Counter,
    test_name: Counter,
    test_attr: Counter,
    file_name_counts: dict[str, Counter],
    file_attr_counts: dict[str, Counter],
) -> dict:
    prod_refs = prod_name.get(obj.name, 0) + prod_attr.get(obj.name, 0)
    test_refs = test_name.get(obj.name, 0) + test_attr.get(obj.name, 0)
    self_refs = file_name_counts.get(obj.file, Counter()).get(
        obj.name, 0
    ) + file_attr_counts.get(obj.file, Counter()).get(obj.name, 0)

    classification: str
    if prod_refs > 0 and test_refs > 0:
        classification = "ACTIVE"
    elif prod_refs > 0 and (prod_refs - self_refs) == 0 and test_refs == 0:
        classification = "SELF_ONLY"
    elif prod_refs > 0 and test_refs == 0:
        classification = "PRODUCTION_ONLY"
    elif prod_refs == 0 and test_refs > 0:
        classification = "TEST_ONLY"
    else:
        classification = "DEAD"

    exempt_reason: Optional[str] = None
    if classification == "DEAD":
        if obj.type == "class" and (
            obj.name.endswith("Port")
            or obj.name.endswith("Schema")
            or "Protocol" in (obj.base_classes or [])
        ):
            exempt_reason = "Protocol/Port/Schema exemption"
        if obj.type == "__all__":
            exempt_reason = "__all__ facade"

    return {
        "qualname": obj.qualname,
        "name": obj.name,
        "module": obj.module,
        "layer": obj.layer,
        "type": obj.type,
        "file": obj.file,
        "prod_refs": prod_refs,
        "test_refs": test_refs,
        "self_refs": self_refs,
        "classification": classification,
        "exempt_reason": exempt_reason,
    }


def detect_orphans(objects: List[ObjectRecord]) -> List[dict]:
    modules = {obj.module: obj.file for obj in objects if obj.type != "__all__"}
    incoming: dict[str, int] = defaultdict(int)

    for layer in LAYER_ORDER:
        for path in sorted((SRC / layer).rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            src_layer, src_module = path_to_module(path)
            for node in ast.walk(tree):
                target: Optional[str] = None
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("bioetl."):
                            target = alias.name
                            incoming[target] += 1
                elif isinstance(node, ast.ImportFrom):
                    if node.module is None:
                        continue
                    if node.module.startswith("bioetl"):
                        target = node.module
                        incoming[target] += 1
    orphans: List[dict] = []
    for module, file in modules.items():
        if incoming.get(module, 0) == 0 and not module.endswith("__init__"):
            loc = sum(1 for _ in Path(file).read_text(encoding="utf-8").splitlines())
            layer = module.split(".")[1] if "." in module else "unknown"
            defined = [obj.name for obj in objects if obj.module == module]
            orphans.append(
                {
                    "module": module,
                    "file": file,
                    "layer": layer,
                    "loc": loc,
                    "objects": defined,
                }
            )
    orphans.sort(key=lambda x: (LAYER_ORDER.index(x["layer"]), x["module"]))
    return orphans


def detect_duplicates(objects: List[ObjectRecord]) -> List[dict]:
    by_hash: dict[str, List[ObjectRecord]] = defaultdict(list)
    for obj in objects:
        if obj.body_hash:
            by_hash[obj.body_hash].append(obj)
    duplicates: List[dict] = []
    for h, group in by_hash.items():
        if len(group) < 2:
            continue
        loc = group[0].loc
        severity = "LOW"
        if loc >= 50:
            severity = "CRITICAL"
        elif loc >= 20:
            severity = "HIGH"
        elif loc >= 10:
            severity = "MEDIUM"
        entry = {
            "hash": h,
            "loc": loc,
            "severity": severity,
            "objects": [
                {
                    "qualname": g.qualname,
                    "module": g.module,
                    "layer": g.layer,
                    "type": g.type,
                    "file": g.file,
                    "loc": g.loc,
                }
                for g in sorted(
                    group, key=lambda x: (LAYER_ORDER.index(x.layer), x.module, x.name)
                )
            ],
        }
        duplicates.append(entry)
    duplicates.sort(key=lambda x: (-x["loc"], x["hash"]))
    return duplicates


def resolve_relative(module: str, level: int, name: Optional[str]) -> Optional[str]:
    parts = module.split(".")
    if level > len(parts) - 1:
        return None
    base = parts[: len(parts) - level]
    if name:
        base.append(name)
    return ".".join(base)


def build_dependency_map() -> dict:
    edges: set[Tuple[str, str]] = set()
    modules_set: set[str] = set()

    for layer in LAYER_ORDER:
        for path in sorted((SRC / layer).rglob("*.py")):
            layer_name, module = path_to_module(path)
            modules_set.add(module)
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                targets: List[str] = []
                if isinstance(node, ast.Import):
                    targets = [
                        alias.name
                        for alias in node.names
                        if alias.name.startswith("bioetl.")
                    ]
                elif isinstance(node, ast.ImportFrom):
                    if node.level and node.module:
                        resolved = resolve_relative(module, node.level, node.module)
                        if resolved and resolved.startswith("bioetl."):
                            targets.append(resolved)
                    elif node.module and node.module.startswith("bioetl."):
                        targets.append(node.module)
                for target in targets:
                    edges.add((module, target))

    fan_out: dict[str, int] = defaultdict(int)
    fan_in: dict[str, int] = defaultdict(int)
    for src, tgt in edges:
        fan_out[src] += 1
        fan_in[tgt] += 1

    graph = defaultdict(list)
    for src, tgt in edges:
        graph[src].append(tgt)

    index = 0
    indices: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    stack: List[str] = []
    on_stack: set[str] = set()
    sccs: List[List[str]] = []

    sys.setrecursionlimit(5000)

    def strongconnect(v: str) -> None:
        nonlocal index
        indices[v] = index
        lowlink[v] = index
        index += 1
        stack.append(v)
        on_stack.add(v)

        for w in graph.get(v, []):
            if w not in indices:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], indices[w])

        if lowlink[v] == indices[v]:
            scc = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                scc.append(w)
                if w == v:
                    break
            if len(scc) > 1:
                sccs.append(sorted(scc))

    for module in modules_set:
        if module not in indices:
            strongconnect(module)

    isolates = sorted(
        [
            m
            for m in modules_set
            if fan_in.get(m, 0) == 0
            and fan_out.get(m, 0) == 0
            and not m.endswith("__init__")
        ]
    )

    return {
        "edges": sorted(list(edges)),
        "fan_in": fan_in,
        "fan_out": fan_out,
        "cycles": sccs,
        "isolates": isolates,
    }


def render_report(
    objects: List[ObjectRecord],
    refs: List[dict],
    duplicates: List[dict],
    orphans: List[dict],
    depmap: dict,
) -> str:
    total_classes = sum(1 for o in objects if o.type == "class")
    total_functions = sum(1 for o in objects if o.type == "function")
    total_constants = sum(1 for o in objects if o.type == "constant")
    dead_objects = [
        r for r in refs if r["classification"] == "DEAD" and r["exempt_reason"] is None
    ]
    summary = [
        "| Метрика | Значение |",
        "|---------|----------|",
        f"| Всего классов | {total_classes} |",
        f"| Всего функций (module-level) | {total_functions} |",
        f"| Всего констант | {total_constants} |",
        f"| Мёртвых объектов (DEAD) | {len(dead_objects)} |",
        f"| Дублей (confirmed) | {len(duplicates)} |",
        f"| Дублей (suspected) | 0 |",
        "",
    ]

    def layer_table(layer: str) -> str:
        entries = [o for o in objects if o.layer == layer]
        lines = [
            "| Type | Name | Module | LOC | Details |",
            "|------|------|--------|-----|---------|",
        ]
        for o in entries:
            details: List[str] = []
            if o.type == "class":
                if o.base_classes:
                    details.append(f"bases={','.join(o.base_classes)}")
                if o.public_methods:
                    details.append(f"public={','.join(o.public_methods)}")
            if o.type == "function" and o.signature:
                details.append(o.signature)
            lines.append(
                f"| {o.type} | {o.name} | {o.module} | {o.loc} | {'; '.join(details)} |"
            )
        return "\n".join(lines) if len(lines) > 2 else "_no objects_"

    dead_section = [
        "| # | Object | Type | Layer | File |",
        "|---|--------|------|-------|------|",
    ]
    for idx, obj in enumerate(dead_objects, 1):
        dead_section.append(
            f"| {idx} | {obj['qualname']} | {obj['type']} | {obj['layer']} | {obj['file']} |"
        )
    if len(dead_section) == 2:
        dead_section.append("| – | – | – | – | – |")

    orphan_section = [
        "| # | File | LOC | Objects Defined |",
        "|---|------|-----|----------------|",
    ]
    for idx, entry in enumerate(orphans, 1):
        orphan_section.append(
            f"| {idx} | {entry['file']} | {entry['loc']} | {', '.join(entry['objects'])} |"
        )
    if len(orphan_section) == 2:
        orphan_section.append("| – | – | – | – |")

    dup_section = [
        "| # | Hash | LOC | Severity | Objects |",
        "|---|------|-----|----------|---------|",
    ]
    for idx, entry in enumerate(duplicates, 1):
        objs = "; ".join([o["qualname"] for o in entry["objects"]])
        dup_section.append(
            f"| {idx} | {entry['hash'][:12]} | {entry['loc']} | {entry['severity']} | {objs} |"
        )
    if len(dup_section) == 2:
        dup_section.append("| – | – | – | – | – |")

    fanout_top = sorted(depmap["fan_out"].items(), key=lambda x: -x[1])[:10]
    fanin_top = sorted(depmap["fan_in"].items(), key=lambda x: -x[1])[:10]
    fanout_lines = [
        "| Object | Dependencies Count |",
        "|--------|-------------------|",
    ] + [f"| {k} | {v} |" for k, v in fanout_top]
    fanin_lines = ["| Object | Dependents Count |", "|--------|-----------------|"] + [
        f"| {k} | {v} |" for k, v in fanin_top
    ]

    cycles_lines = ["| # | Cycle | Files Involved |", "|---|-------|----------------|"]
    for idx, cyc in enumerate(depmap["cycles"], 1):
        cycles_lines.append(f"| {idx} | {', '.join(cyc)} | – |")
    if len(cycles_lines) == 2:
        cycles_lines.append("| – | – | – |")

    report_parts = [
        "# Code Inventory Report — BioETL",
        f"Date: {TASK_ID}",
        "Scope: src/bioetl/ (all layers)",
        "",
        "## Executive Summary",
        *summary,
        "## 1. Реестр Объектов",
    ]

    for layer in LAYER_ORDER:
        report_parts.append(
            f"### 1.{LAYER_ORDER.index(layer) + 1} {layer.capitalize()} Layer"
        )
        report_parts.append(layer_table(layer))
        report_parts.append("")

    report_parts.extend(
        [
            "## 2. Dead Code",
            "### 2.1 DEAD объекты (0 ссылок)",
            "\n".join(dead_section),
            "",
            "### 2.4 Orphan-модули (файлы без imports)",
            "\n".join(orphan_section),
            "",
            "## 3. Duplicate Logic",
            "### 3.1 Confirmed Duplicates (идентичная логика)",
            "\n".join(dup_section),
            "",
            "## 4. Dependency Map",
            "### 4.1 Объекты с наибольшим fan-out (зависят от многих)",
            "\n".join(fanout_lines),
            "",
            "### 4.2 Объекты с наибольшим fan-in (от них зависят многие)",
            "\n".join(fanin_lines),
            "",
            "### 4.3 Циклические зависимости внутри слоя",
            "\n".join(cycles_lines),
            "",
            "## 5. Рекомендации",
            "- Заполнить рекомендации после детальной верификации.",
            "",
        ]
    )

    return "\n".join(report_parts)


def main() -> None:
    objects, file_name_counts, file_attr_counts, module_info = collect_objects()
    prod_name, prod_attr, test_name, test_attr = collect_usage_counts(
        file_name_counts, file_attr_counts
    )

    refs = [
        classify_object(
            obj,
            prod_name,
            prod_attr,
            test_name,
            test_attr,
            file_name_counts,
            file_attr_counts,
        )
        for obj in objects
    ]

    orphans = detect_orphans(objects)
    duplicates = detect_duplicates(objects)
    depmap = build_dependency_map()

    atomic_write(
        OUT_DIR / "objects.json",
        json.dumps([asdict(o) | {"qualname": o.qualname} for o in objects], indent=2),
    )
    atomic_write(
        OUT_DIR / "references.json",
        json.dumps({"objects": refs, "orphans": orphans}, indent=2),
    )
    atomic_write(OUT_DIR / "duplicates.json", json.dumps(duplicates, indent=2))
    atomic_write(OUT_DIR / "dependency-map.json", json.dumps(depmap, indent=2))

    report_md = render_report(objects, refs, duplicates, orphans, depmap)
    atomic_write(OUT_DIR / "inventory-report.md", report_md)


if __name__ == "__main__":
    main()
