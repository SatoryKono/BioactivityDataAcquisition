#!/usr/bin/env python3
"""Generate supplemental Mermaid class diagrams for package families.

The canonical curated class diagrams remain the primary narrative layer.
This generator adds AST-derived package-family supplements for src/bioetl/**
families that contain more than three top-level classes and are not already
covered by the curated family set.
"""

from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

try:
    from scripts.diagrams.core.diagram_paths import DIAGRAM_ROOT, REPO_ROOT
except ImportError:  # pragma: no cover - direct script execution
    from scripts.diagrams.core.diagram_paths import DIAGRAM_ROOT, REPO_ROOT


SRC_ROOT = REPO_ROOT / "src" / "bioetl"
CLASS_DIAGRAM_DIR = DIAGRAM_ROOT / "class-diagrams"
GENERATED_PREFIX = "90-pkg-"
MIN_FAMILY_CLASSES = 4
MAX_SLICE_NODES = 30

# Curated high-level families already covered by the handcrafted class diagrams.
CURATED_FAMILY_PATHS = frozenset(
    {
        "application/composite",
        "application/core",
        "application/pipelines/pubmed/extractors",
        "application/services",
        "composition/factories/pipeline",
        "domain/config",
        "domain/entities",
        "domain/exceptions",
        "domain/ports",
        "domain/services",
        "domain/types",
        "domain/value_objects",
        "infrastructure/adapters",
        "infrastructure/observability",
        "infrastructure/storage",
    }
)


@dataclass(frozen=True)
class ClassInfo:
    family: str
    module_stem: str
    module_name: str
    class_name: str
    base_names: tuple[str, ...]


@dataclass(frozen=True)
class FamilySlice:
    family: str
    part_index: int
    part_total: int
    module_names: tuple[str, ...]
    classes: tuple[ClassInfo, ...]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate AST-derived supplemental Mermaid class diagrams for "
            "package families with more than three top-level classes."
        )
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit with non-zero status if generated files would change.",
    )
    return parser.parse_args(argv)


def _extract_base_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return _extract_base_name(node.value)
    if isinstance(node, ast.Call):
        return _extract_base_name(node.func)
    return None


def collect_family_classes() -> dict[str, list[ClassInfo]]:
    classes_by_family: dict[str, list[ClassInfo]] = defaultdict(list)
    for path in sorted(SRC_ROOT.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError:
            continue

        family = path.parent.relative_to(SRC_ROOT).as_posix()
        module_stem = path.stem
        module_name = (
            path.relative_to(SRC_ROOT).with_suffix("").as_posix().replace("/", ".")
        )

        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            base_names = tuple(
                base_name
                for base in node.bases
                if (base_name := _extract_base_name(base)) is not None
            )
            classes_by_family[family].append(
                ClassInfo(
                    family=family,
                    module_stem=module_stem,
                    module_name=module_name,
                    class_name=node.name,
                    base_names=base_names,
                )
            )
    return {
        family: infos
        for family, infos in classes_by_family.items()
        if len(infos) >= MIN_FAMILY_CLASSES and family not in CURATED_FAMILY_PATHS
    }


def _sanitize_token(raw: str) -> str:
    chars = [ch if ch.isalnum() else "_" for ch in raw]
    token = "".join(chars).strip("_")
    return token or "family"


def _sanitize_file_stem(raw: str) -> str:
    chars = [ch if ch.isalnum() else "-" for ch in raw]
    stem = "".join(chars).strip("-")
    while "--" in stem:
        stem = stem.replace("--", "-")
    return stem or "family"


def build_family_slices(
    classes_by_family: dict[str, list[ClassInfo]],
) -> list[FamilySlice]:
    slices: list[FamilySlice] = []
    for family in sorted(classes_by_family):
        classes = classes_by_family[family]
        classes_by_module: dict[str, list[ClassInfo]] = defaultdict(list)
        for info in classes:
            classes_by_module[info.module_stem].append(info)

        ordered_modules = sorted(
            classes_by_module.items(),
            key=lambda item: (-len(item[1]), item[0]),
        )

        current_modules: list[str] = []
        current_classes: list[ClassInfo] = []
        family_slices: list[tuple[tuple[str, ...], tuple[ClassInfo, ...]]] = []

        for module_name, module_classes in ordered_modules:
            if (
                current_classes
                and len(current_classes) + len(module_classes) > MAX_SLICE_NODES
            ):
                family_slices.append((tuple(current_modules), tuple(current_classes)))
                current_modules = []
                current_classes = []
            current_modules.append(module_name)
            current_classes.extend(
                sorted(module_classes, key=lambda item: item.class_name)
            )

        if current_classes:
            family_slices.append((tuple(current_modules), tuple(current_classes)))

        total_parts = len(family_slices)
        for index, (module_names, family_classes) in enumerate(family_slices, start=1):
            slices.append(
                FamilySlice(
                    family=family,
                    part_index=index,
                    part_total=total_parts,
                    module_names=module_names,
                    classes=family_classes,
                )
            )
    return slices


def _slice_file_name(slice_: FamilySlice) -> str:
    stem = f"{GENERATED_PREFIX}{_sanitize_file_stem(slice_.family)}"
    if slice_.part_total > 1:
        stem = f"{stem}-part{slice_.part_index}"
    return f"{stem}.mmd"


def _slice_title(slice_: FamilySlice) -> str:
    if slice_.part_total == 1:
        return f"Package Family: {slice_.family}"
    return (
        f"Package Family: {slice_.family} "
        f"(Part {slice_.part_index}/{slice_.part_total})"
    )


def _slice_covers(slice_: FamilySlice) -> str:
    module_list = ", ".join(slice_.module_names[:6])
    if slice_.part_total == 1:
        return (
            f"AST-derived supplemental package-family inventory for src/bioetl/"
            f"{slice_.family}; modules: {module_list}."
        )
    return (
        f"AST-derived supplemental package-family inventory slice for src/bioetl/"
        f"{slice_.family}; part {slice_.part_index}/{slice_.part_total}; "
        f"modules: {module_list}."
    )


def _slice_reference(slice_: FamilySlice) -> str:
    if slice_.part_total == 1:
        return (
            "Generated supplemental package-family diagram. "
            "Curated class-summary remains narrative-only."
        )
    return (
        "Generated supplemental package-family slice used to keep node density "
        f"within the class-diagram readability budget (<= {MAX_SLICE_NODES})."
    )


def _class_id(info: ClassInfo, duplicate_names: set[str]) -> str:
    if info.class_name not in duplicate_names:
        return info.class_name
    return _sanitize_token(f"{info.module_stem}_{info.class_name}")


def build_diagram_text(slice_: FamilySlice) -> str:
    duplicate_names = {
        name
        for name, count in defaultdict(
            int,
            {
                info.class_name: sum(
                    1 for item in slice_.classes if item.class_name == info.class_name
                )
                for info in slice_.classes
            },
        ).items()
        if count > 1
    }
    class_ids = {
        (info.module_name, info.class_name): _class_id(info, duplicate_names)
        for info in slice_.classes
    }
    known_names = {info.class_name for info in slice_.classes}

    lines = [
        f"%% Title: {_slice_title(slice_)}",
        f"%% Covers: {_slice_covers(slice_)}",
        "%% Components: top-level classes grouped by source module.",
        "%% @version 1.0.0",
        "%% @type    classDiagram",
        f"%% @date    {date.today().isoformat()}",
        "%% @level   Package Family / Inventory Slice",
        f"%% @nodes   {len(slice_.classes)}",
        f"%% @reference {_slice_reference(slice_)}",
        "classDiagram",
        "",
    ]

    for module_name in slice_.module_names:
        namespace_name = _sanitize_token(module_name)
        lines.append(f"    namespace {namespace_name} {{")
        module_classes = [
            info for info in slice_.classes if info.module_stem == module_name
        ]
        for info in module_classes:
            lines.append(
                f"        class {class_ids[(info.module_name, info.class_name)]}"
            )
        lines.append("    }")
        lines.append("")

    relationships: list[str] = []
    for info in slice_.classes:
        child_id = class_ids[(info.module_name, info.class_name)]
        for base_name in info.base_names:
            if base_name not in known_names:
                continue
            candidates = [
                item for item in slice_.classes if item.class_name == base_name
            ]
            if len(candidates) != 1:
                continue
            base_info = candidates[0]
            parent_id = class_ids[(base_info.module_name, base_info.class_name)]
            relationships.append(f"    {parent_id} <|-- {child_id}")

    if relationships:
        lines.extend(sorted(set(relationships)))
        lines.append("")

    return "\n".join(lines) + "\n"


def build_expected_outputs(slices: Iterable[FamilySlice]) -> dict[Path, str]:
    return {
        CLASS_DIAGRAM_DIR / _slice_file_name(slice_): build_diagram_text(slice_)
        for slice_ in slices
    }


def write_outputs(expected_outputs: dict[Path, str]) -> tuple[int, int]:
    removed = 0
    written = 0
    for stale_file in sorted(CLASS_DIAGRAM_DIR.glob(f"{GENERATED_PREFIX}*.mmd")):
        if stale_file not in expected_outputs:
            stale_file.unlink()
            removed += 1

    for path, content in expected_outputs.items():
        if path.exists() and path.read_text(encoding="utf-8") == content:
            continue
        path.write_text(content, encoding="utf-8")
        written += 1

    return written, removed


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    classes_by_family = collect_family_classes()
    slices = build_family_slices(classes_by_family)
    expected_outputs = build_expected_outputs(slices)

    stale_files = {
        path
        for path in CLASS_DIAGRAM_DIR.glob(f"{GENERATED_PREFIX}*.mmd")
        if path not in expected_outputs
    }
    changed_files = {
        path
        for path, content in expected_outputs.items()
        if not path.exists() or path.read_text(encoding="utf-8") != content
    }

    if args.check:
        if changed_files or stale_files:
            print("[ERROR] Supplemental package-family class diagrams are stale.")
            print(
                f"[INFO] Families: {len(classes_by_family)} | "
                f"Slices: {len(slices)} | "
                f"Changed files: {len(changed_files)} | "
                f"Stale files: {len(stale_files)}"
            )
            return 1
        print(
            f"[OK] Supplemental package-family class diagrams are current "
            f"({len(classes_by_family)} families / {len(slices)} slices)."
        )
        return 0

    written, removed = write_outputs(expected_outputs)
    print(
        f"[OK] Generated supplemental package-family class diagrams: "
        f"{len(classes_by_family)} families / {len(slices)} slices"
    )
    print(f"[INFO] Files written: {written}")
    print(f"[INFO] Stale files removed: {removed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
