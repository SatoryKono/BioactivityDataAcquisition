"""Merge targeted gap coverage class nodes into the main coverage.xml."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(".").resolve()
MAIN = ROOT / "reports/coverage/coverage.xml"
GAP = ROOT / "reports/coverage/coverage-gap-targeted.xml"
INVENTORY = ROOT / "reports/quality/module-coverage-inventory.json"


def _normalize(filename: str) -> str:
    norm = filename.replace("\\", "/")
    if norm.startswith("src/"):
        norm = norm[len("src/") :]
    if norm.startswith("bioetl/"):
        norm = norm[len("bioetl/") :]
    return norm


def main() -> None:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    # Prefer previous unmeasured list; fall back to currently uncovered paths.
    targets = {
        str(row["path"]).replace("\\", "/").removeprefix("src/bioetl/")
        for row in inventory["summary"].get("unmeasured_modules", [])
    }
    if not targets:
        targets = {
            str(row["path"]).replace("\\", "/").removeprefix("src/bioetl/")
            for row in inventory["modules"]
            if row.get("coverage_status") == "uncovered"
        }
    print("targets", len(targets))

    gap_root = ET.parse(GAP).getroot()
    gap_by_rel: dict[str, ET.Element] = {}
    for class_node in gap_root.iter("class"):
        filename = class_node.get("filename")
        if not filename:
            continue
        rel = _normalize(filename)
        if rel in targets or f"src/bioetl/{rel}" in {
            str(row.get("path", "")).replace("\\", "/")
            for row in inventory["modules"]
            if row.get("coverage_status") in {"uncovered", "unmeasured"}
        }:
            gap_by_rel[rel] = class_node
    # Also index any gap class whose rel is under targets
    for class_node in gap_root.iter("class"):
        filename = class_node.get("filename")
        if not filename:
            continue
        rel = _normalize(filename)
        if rel in targets:
            gap_by_rel[rel] = class_node
    print("gap_matches", len(gap_by_rel), sorted(gap_by_rel)[:5])

    main_tree = ET.parse(MAIN)
    main_root = main_tree.getroot()
    packages = {p.get("name"): p for p in main_root.iter("package")}
    existing_classes = {
        _normalize(c.get("filename") or ""): c for c in main_root.iter("class")
    }

    updated = 0
    added = 0
    for rel, gap_class in sorted(gap_by_rel.items()):
        # Count hits in gap class
        executable = sum(1 for _ in gap_class.iter("line"))
        covered = sum(
            1 for line in gap_class.iter("line") if int(line.attrib.get("hits", "0")) > 0
        )
        if covered == 0:
            print("skip_zero_cover", rel, executable)
            continue

        if rel in existing_classes:
            old = existing_classes[rel]
            parent = None
            # replace in parent classes element
            for package in main_root.iter("package"):
                classes_el = package.find("classes")
                if classes_el is None:
                    continue
                for child in list(classes_el):
                    if child is old or _normalize(child.get("filename") or "") == rel:
                        classes_el.remove(child)
                        new_class = ET.fromstring(
                            ET.tostring(gap_class, encoding="unicode")
                        )
                        new_class.set("filename", rel)
                        classes_el.append(new_class)
                        updated += 1
                        print("updated", rel, f"{covered}/{executable}")
                        parent = package
                        break
                if parent is not None:
                    break
            continue

        # add new
        parts = Path(rel).parts
        pkg_name = "." if len(parts) == 1 else ".".join(parts[:-1])
        parent = packages.get(pkg_name)
        if parent is None:
            packages_el = main_root.find("packages")
            if packages_el is None:
                packages_el = ET.SubElement(main_root, "packages")
            parent = ET.SubElement(
                packages_el,
                "package",
                {
                    "name": pkg_name,
                    "line-rate": gap_class.get("line-rate", "0"),
                    "branch-rate": gap_class.get("branch-rate", "0"),
                    "complexity": "0",
                },
            )
            ET.SubElement(parent, "classes")
            packages[pkg_name] = parent
        classes_el = parent.find("classes")
        if classes_el is None:
            classes_el = ET.SubElement(parent, "classes")
        new_class = ET.fromstring(ET.tostring(gap_class, encoding="unicode"))
        new_class.set("filename", rel)
        classes_el.append(new_class)
        added += 1
        print("added", rel, f"{covered}/{executable}")

    main_tree.write(MAIN, encoding="utf-8", xml_declaration=True)
    print("done updated", updated, "added", added)


if __name__ == "__main__":
    main()
