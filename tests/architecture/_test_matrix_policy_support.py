"""Shared helpers for test-matrix governance architecture suites."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = ROOT / "tests"
MATRIX_PATH = ROOT / "configs" / "quality" / "test_matrix.yaml"
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
ENTITY_CONFIGS_DIR = ROOT / "configs" / "entities"
YamlMap = dict[str, Any]


def load_matrix() -> YamlMap:
    """Load the test matrix configuration."""
    with MATRIX_PATH.open(encoding="utf-8") as handle:
        return cast(YamlMap, yaml.safe_load(handle))


def iter_entity_configs() -> list[tuple[str, str, Path]]:
    """Return active entity config tuples as (provider, entity, path)."""
    configs: list[tuple[str, str, Path]] = []
    for config_path in sorted(ENTITY_CONFIGS_DIR.glob("*/*.yaml")):
        configs.append((config_path.parent.name, config_path.stem, config_path))
    return configs


def ownership_paths(matrix: YamlMap, entity_key: str) -> list[Path]:
    """Resolve owned test paths for a provider.entity key."""
    raw_paths = matrix.get("entity_test_ownership", {}).get(entity_key, [])
    if isinstance(raw_paths, str):
        raw_paths = [raw_paths]
    return [ROOT / path for path in raw_paths]


def forbidden_test_dir(forbidden_path: str) -> Path:
    """Map a forbidden layer path to the corresponding test directory."""
    parts = forbidden_path.split("/")
    if len(parts) >= 2:
        return TESTS_DIR / "unit" / parts[0] / parts[1]
    return TESTS_DIR / "unit" / parts[0]


def contains_forbidden_hypothesis_usage(content: str) -> bool:
    """Return whether a file contains non-exempt Hypothesis usage."""
    if "@given(" not in content and "from hypothesis" not in content:
        return False
    return "# hypothesis: boundary-exception" not in content


def required_provider_names(matrix: YamlMap, field: str) -> list[str]:
    """Return providers whose matrix policy requires the given field."""
    return [
        provider
        for provider, config in matrix["providers"].items()
        if config.get(field) == "MUST"
    ]


def must_unit_layers(matrix: YamlMap) -> list[str]:
    """Return layer names that must keep unit tests."""
    return [
        layer
        for layer, config in matrix["layers"].items()
        if config.get("unit") == "MUST"
    ]


def provider_suite_index(provider_suites: Any) -> dict[str, set[str]]:
    """Index provider regression suite ownership by provider name."""
    suite_index: dict[str, set[str]] = {}
    for suite_name, suite_config in provider_suites.items():
        for provider in suite_config.get("providers", {}):
            suite_index.setdefault(provider, set()).add(suite_name)
    return suite_index


def lane_paths(lane: YamlMap) -> list[Path]:
    """Resolve canonical lane test paths."""
    return [ROOT / str(path) for path in lane.get("paths", [])]


def lane_runner(lane: YamlMap) -> Path:
    """Resolve the configured lane runner path."""
    return ROOT / str(lane.get("runner"))


def represented_golden_master_entities() -> dict[str, set[str]]:
    """Return the provider/entity set represented by golden-master pipelines."""
    from tests.architecture.test_config_golden_master import PIPELINES

    represented: dict[str, set[str]] = {}
    for provider, entity, config_path in iter_entity_configs():
        lines = config_path.read_text(encoding="utf-8").splitlines()
        pipeline_name = next(
            line.split(":", 1)[1].strip() for line in lines if "pipeline_name:" in line
        )
        if pipeline_name in PIPELINES:
            represented.setdefault(provider, set()).add(entity)
    return represented
