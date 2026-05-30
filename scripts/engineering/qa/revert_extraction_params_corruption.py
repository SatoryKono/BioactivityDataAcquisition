#!/usr/bin/env python3
"""Strip entity-specific extraction_params keys copied by auto burn-down."""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bioetl.infrastructure.config.config_ci_contract import EXTRACTION_PARAM_ALLOWLIST

ENTITIES = ROOT / "configs" / "entities"


def _yaml_rt() -> YAML:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False
    yaml.width = 120
    return yaml


def _atomic_write(path: Path, yaml: YAML, data: dict[str, Any]) -> None:
    buffer = io.StringIO()
    yaml.dump(data, buffer)
    payload = buffer.getvalue()
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_text(payload, encoding="utf-8")
    try:
        os.replace(tmp, path)
    except OSError:
        path.write_text(payload, encoding="utf-8")
        tmp.unlink(missing_ok=True)


def _clean_extraction_params(data: dict[str, Any], rel_key: str) -> bool:
    filters = data.get("filters")
    if not isinstance(filters, dict):
        return False
    extraction = filters.get("extraction_params")
    if not isinstance(extraction, dict):
        return False

    allowed = EXTRACTION_PARAM_ALLOWLIST.get(rel_key, frozenset())
    changed = False
    for key in list(extraction.keys()):
        if key not in allowed:
            del extraction[key]
            changed = True
    if not extraction and "extraction_params" in filters:
        filters["extraction_params"] = {}
    return changed


def main() -> None:
    yaml = _yaml_rt()
    touched = 0
    for path in sorted(ENTITIES.glob("*/*.yaml")):
        rel_key = f"{path.parent.name}/{path.stem}"
        data = yaml.load(path)
        if not isinstance(data, dict):
            continue
        if _clean_extraction_params(data, rel_key):
            _atomic_write(path, yaml, data)
            touched += 1
            print(f"cleaned extraction_params {rel_key}")
    print(f"touched={touched}")


if __name__ == "__main__":
    main()
