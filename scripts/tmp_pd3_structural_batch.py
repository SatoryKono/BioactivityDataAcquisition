#!/usr/bin/env python3
"""Structural PD3 batch: schemas Config inline, constants rename, targeted cleanups."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "bioetl"


def strip_file_level_rule(text: str, rule: str) -> str:
    target = f"{rule}=false"
    out: list[str] = []
    for line in text.splitlines(True):
        if line.lstrip().startswith("# pyright:") and target in line:
            # remove whole line if only this rule (possibly with comment)
            body = line.split("pyright:", 1)[1]
            parts = [p.strip() for p in re.split(r"[, ]+", body) if p.strip()]
            parts = [p for p in parts if target not in p and rule not in p]
            # drop trailing rationale-only next lines handled elsewhere
            if not parts or all(not p.startswith("report") for p in parts):
                continue
            continue  # drop multi-rule line entirely if mixed — safer re-add only needed? skip
        out.append(line)
    return "".join(out)


def process_schema_config(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if "class Config" not in text:
        return False
    if "reportIncompatibleVariableOverride=false" not in text:
        return False
    original = text
    # Add inline ignore on class Config lines missing it
    text2 = re.sub(
        r"(?m)^(?P<indent>[ \t]*)class Config\b(?P<rest>[^:\n]*):",
        lambda m: (
            m.group(0)
            if "pyright: ignore" in m.group(0)
            else f"{m.group('indent')}class Config{m.group('rest')}:  # pyright: ignore[reportIncompatibleVariableOverride]"
        ),
        text,
    )
    # Remove file-level override directive lines
    lines = []
    for line in text2.splitlines(True):
        if (
            line.lstrip().startswith("# pyright:")
            and "reportIncompatibleVariableOverride=false" in line
        ):
            # if only this rule, drop; if multiple, strip this rule
            body = line.split("pyright:", 1)[1]
            others = [
                p.strip()
                for p in re.split(r"[, ]+", body)
                if p.strip()
                and "reportIncompatibleVariableOverride" not in p
                and p.strip().startswith("report")
            ]
            if others:
                lines.append(f"# pyright: {', '.join(others)}\n")
            continue
        if line.startswith("# Pandera/ETL nested Config"):
            continue
        if line.startswith("# MRO/override residual"):
            continue
        lines.append(line)
    text2 = "".join(lines)
    if text2 != original:
        path.write_text(text2, encoding="utf-8")
        return True
    return False


def process_available_constants(path: Path) -> bool:
    """Rename SCREAMING AVAILABLE probes that are reassigned to module-level non-const style."""
    text = path.read_text(encoding="utf-8")
    if "reportConstantRedefinition=false" not in text:
        return False
    original = text
    # Common patterns: OTLP_AVAILABLE, _ORJSON_AVAILABLE, _PSUTIL_AVAILABLE
    replacements = {
        "OTLP_AVAILABLE": "otlp_available",
        "_ORJSON_AVAILABLE": "_orjson_available",
        "_PSUTIL_AVAILABLE": "_psutil_available",
        "ORJSON_AVAILABLE": "orjson_available",
        "PSUTIL_AVAILABLE": "psutil_available",
    }
    for old, new in replacements.items():
        if old in text:
            text = text.replace(old, new)
    # strip constant redefinition directives
    lines = []
    for line in text.splitlines(True):
        if (
            line.lstrip().startswith("# pyright:")
            and "reportConstantRedefinition=false" in line
        ):
            body = line.split("pyright:", 1)[1]
            others = [
                p.strip()
                for p in re.split(r"[, ]+", body)
                if p.strip()
                and "reportConstantRedefinition" not in p
                and p.strip().startswith("report")
            ]
            if others:
                lines.append(f"# pyright: {', '.join(others)}\n")
            continue
        if "Optional dependency probe" in line:
            continue
        lines.append(line)
    text = "".join(lines)
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    schema_changed = 0
    for path in (SRC / "domain" / "schemas").rglob("*.py"):
        if process_schema_config(path):
            schema_changed += 1
            print("schema", path.relative_to(SRC))
    for path in (SRC / "domain" / "contracts").rglob("*.py"):
        if process_schema_config(path):
            schema_changed += 1
            print("contract", path.relative_to(SRC))

    const_changed = 0
    for rel in [
        "infrastructure/observability/tracing.py",
        "infrastructure/system/memory_monitor.py",
        "domain/normalization/profiles/chembl_policy_registry.py",
        "domain/serialization.py",
        "domain/normalization/json.py",
        "infrastructure/serialization/encoders.py",
        "composition/_workflow_services.py",
        "application/services/run_reports/writer.py",
        "domain/mapping/publication_controlled_vocabulary.py",
    ]:
        path = SRC / rel
        if path.is_file() and process_available_constants(path):
            const_changed += 1
            print("const", rel)

    print(f"schema_changed={schema_changed} const_changed={const_changed}")


if __name__ == "__main__":
    main()
