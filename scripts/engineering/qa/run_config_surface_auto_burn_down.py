#!/usr/bin/env python3
"""Iterative config-surface burn-down: align one inconsistent parameter per phase."""

from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parents[3]
SCORECARD = ROOT / "configs/quality/debt_scorecard.yaml"
BASELINE = ROOT / "reports/quality/config-discrepancy-baseline.json"
EXCLUDED_CONFIGS: frozenset[str] = frozenset()

# Keys that must not be copied across configs (provider/entity-specific runtime).
DENY_KEY_PREFIXES: tuple[str, ...] = (
    "hash_policy",
    "pipeline.source",
    "pipeline.page_size_override",
    "pipeline.field_policy.therapeutic_flag",
    "filters.extraction_params",
    "filters.gold_filters.columns",
    "filters.gold_filters.list_contains",
    "filters.gold_filters.list_lengths",
    "filters.gold_filters.ranges.max_tani",
    "filters.gold_filters.ranges.standard_value",
    "filters.silver_filters.columns",
    "filters.silver_filters.ranges",
)

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.schema.generate_config_matrix import (  # noqa: E402
    _collect_family_configs,
)


def _yaml_rt() -> YAML:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False
    yaml.width = 120
    yaml.indent(mapping=2, sequence=4, offset=2)
    return yaml


def _config_path(config_name: str) -> Path:
    if config_name.startswith("entity/"):
        rel = config_name.removeprefix("entity/")
        return ROOT / "configs/entities" / f"{rel.replace('/', os.sep)}.yaml"
    if config_name.startswith("composite/"):
        stem = config_name.removeprefix("composite/")
        return ROOT / "configs/composites" / f"{stem}.yaml"
    raise ValueError(f"Unknown config name: {config_name}")


def _get_nested(data: Any, parts: list[str]) -> Any:
    cur = data
    for part in parts:
        if not isinstance(cur, dict) or part not in cur:
            raise KeyError(part)
        cur = cur[part]
    return cur


def _has_nested(data: Any, parts: list[str]) -> bool:
    try:
        _get_nested(data, parts)
        return True
    except KeyError:
        return False


def _ensure_set(data: dict[str, Any], parts: list[str], value: Any) -> bool:
    cur: Any = data
    for part in parts[:-1]:
        nxt = cur.get(part) if isinstance(cur, dict) else None
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    leaf = parts[-1]
    if isinstance(cur, dict) and leaf not in cur:
        cur[leaf] = copy.deepcopy(value)
        return True
    return False


def _should_skip_key(key: str) -> bool:
    if key.startswith("hash_policy"):
        return False
    return any(key == prefix or key.startswith(f"{prefix}.") for prefix in DENY_KEY_PREFIXES)


def _should_skip_config(config_name: str, key: str) -> bool:
    if key.startswith("hash_policy") and config_name.startswith("entity/"):
        return "/chembl/" not in config_name
    return False


def _partial_keys(family_configs: dict[str, dict[str, str]]) -> list[tuple[int, str]]:
    all_keys = sorted({key for values in family_configs.values() for key in values})
    if not family_configs:
        return []
    common = set.intersection(*(set(values.keys()) for values in family_configs.values()))
    partial = [key for key in all_keys if key not in common]
    ranked: list[tuple[int, str]] = []
    for key in partial:
        present = sum(1 for values in family_configs.values() if key in values)
        if present == 0:
            continue
        ranked.append((present, key))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return ranked


def _align_key(family_configs: dict[str, dict[str, str]], key: str, yaml: YAML) -> int:
    missing = [
        name
        for name in family_configs
        if key not in family_configs[name]
        and name not in EXCLUDED_CONFIGS
        and not _should_skip_config(name, key)
    ]
    if not missing:
        return 0

    reference_name = next(name for name in family_configs if key in family_configs[name])
    parts = key.split(".")
    ref_data = yaml.load(_config_path(reference_name))
    try:
        stub = _get_nested(ref_data, parts)
    except KeyError:
        return 0

    touched = 0
    for name in missing:
        path = _config_path(name)
        data = yaml.load(path)
        if not isinstance(data, dict):
            continue
        if _has_nested(data, parts):
            continue
        if not _ensure_set(data, parts, stub):
            continue
        _atomic_write(path, yaml, data)
        touched += 1
    return touched


def _atomic_write(path: Path, yaml: YAML, data: dict[str, Any]) -> None:
    import io

    buffer = io.StringIO()
    yaml.dump(data, buffer)
    payload = buffer.getvalue()
    payload = re.sub(
        r"(soft_fail_threshold: [^\n]+)\s+(hard_fail_threshold:)",
        r"\1\n        \2",
        payload,
    )
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_text(payload, encoding="utf-8")
    try:
        os.replace(tmp, path)
    except OSError:
        path.write_text(payload, encoding="utf-8")
        tmp.unlink(missing_ok=True)


def _regenerate() -> None:
    subprocess.check_call(
        [sys.executable, "-m", "scripts.schema", "generate-config-matrix", "--update"],
        cwd=ROOT,
    )


def _load_baseline() -> dict[str, Any]:
    return json.loads(BASELINE.read_text(encoding="utf-8"))


def _update_scorecard() -> None:
    payload = _load_baseline()
    metrics = payload["metrics"]
    families = payload["families"]
    text = SCORECARD.read_text(encoding="utf-8")

    def _replace_metric(block: str, name: str, value: int) -> str:
        return re.sub(
            rf"({re.escape(name)}:\s*\n\s+current_count:\s*)\d+(\s*\n\s+max_count:\s*)\d+",
            rf"\g<1>{value}\g<2>{value}",
            block,
            count=1,
        )

    for name in ("config_count", "unique_parameter_count", "inconsistent_parameter_count"):
        value = int(metrics[name])
        text = _replace_metric(text, name, value)

    for family_name in ("entity_effective", "composite_runtime"):
        family_metrics = families[family_name]
        pattern = rf"({family_name}:.*?metrics:)(.*?)(?=\n    [a-z_]+:|^registry_groups:)"
        match = re.search(pattern, text, re.S | re.M)
        if not match:
            continue
        block = match.group(0)
        updated = block
        for name in ("config_count", "unique_parameter_count", "inconsistent_parameter_count"):
            value = int(family_metrics[name])
            updated = _replace_metric(updated, name, value)
        text = text.replace(block, updated, 1)

    SCORECARD.write_text(text, encoding="utf-8")


def run(max_phases: int = 200_000) -> None:
    yaml = _yaml_rt()
    start = _load_baseline()["families"]
    start_entity = int(start["entity_effective"]["inconsistent_parameter_count"])
    start_composite = int(start["composite_runtime"]["inconsistent_parameter_count"])

    for phase in range(1, max_phases + 1):
        families = _collect_family_configs()
        touched = 0
        selected: tuple[str, str] | None = None

        for family_name in ("composite_runtime",):
            ranked = _partial_keys(families[family_name])
            for _present, key in ranked:
                if _should_skip_key(key):
                    continue
                count = _align_key(families[family_name], key, yaml)
                if count:
                    touched = count
                    selected = (family_name, key)
                    break
            if touched:
                break

        if not touched or selected is None:
            print(f"STOP phase={phase}: no alignable inconsistent keys remain")
            break

        _regenerate()
        payload = _load_baseline()
        entity = int(payload["families"]["entity_effective"]["inconsistent_parameter_count"])
        composite = int(payload["families"]["composite_runtime"]["inconsistent_parameter_count"])
        print(
            f"Phase {phase:06d} {selected[0]} {selected[1]}: "
            f"touched={touched} entity={entity} composite={composite}"
        )

    _update_scorecard()
    payload = _load_baseline()
    entity = int(payload["families"]["entity_effective"]["inconsistent_parameter_count"])
    composite = int(payload["families"]["composite_runtime"]["inconsistent_parameter_count"])
    print(
        f"FINAL entity={entity} composite={composite} "
        f"(delta entity={start_entity - entity}, composite={start_composite - composite})"
    )


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 200_000
    run(limit)
