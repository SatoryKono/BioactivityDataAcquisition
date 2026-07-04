#!/usr/bin/env python3
"""Remove erroneous auto burn-down stubs copied across entity configs."""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parents[3]
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


def _clean_pipeline(pipeline: dict[str, Any], provider: str, entity: str) -> bool:
    changed = False

    if entity != "molecule":
        field_policy = pipeline.get("field_policy")
        if isinstance(field_policy, dict) and "therapeutic_flag" in field_policy:
            if entity == "molecule":
                pass
            elif len(field_policy) == 1:
                pipeline["field_policy"] = {}
                changed = True
            else:
                del field_policy["therapeutic_flag"]
                changed = True

    keep_source = provider == "uniprot" and entity in {"idmapping", "protein"}
    if not keep_source and "source" in pipeline:
        del pipeline["source"]
        changed = True
    elif keep_source and isinstance(pipeline.get("source"), dict):
        source = pipeline["source"]
        for key in ("api_key", "email"):
            if key in source:
                del source[key]
                changed = True

    keep_page_size = provider == "chembl" and entity == "publication"
    if not keep_page_size and "page_size_override" in pipeline:
        del pipeline["page_size_override"]
        changed = True

    return changed


def main() -> None:
    yaml = _yaml_rt()
    touched = 0
    for path in sorted(ENTITIES.glob("*/*.yaml")):
        data = yaml.load(path)
        if not isinstance(data, dict):
            continue
        pipeline = data.get("pipeline")
        if not isinstance(pipeline, dict):
            continue
        provider = str(data.get("provider") or pipeline.get("provider") or "")
        entity = str(data.get("entity") or pipeline.get("entity_type") or path.stem)
        if _clean_pipeline(pipeline, provider, entity):
            _atomic_write(path, yaml, data)
            touched += 1
            print(f"cleaned {path.relative_to(ROOT)}")
    print(f"touched={touched}")


if __name__ == "__main__":
    main()
