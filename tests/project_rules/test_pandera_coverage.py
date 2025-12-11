from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.domain.schemas.registry import SchemaRegistry, register_schemas


def _expected_entities(configs_root: Path) -> set[str]:
    base = configs_root / "pipelines"
    entities: set[str] = set()
    for provider_dir in base.glob("*"):
        if not provider_dir.is_dir():
            continue
        for config_file in provider_dir.glob("*.yaml"):
            entities.add(config_file.stem)
    return entities


def test_pandera_schemas_registered(configs_root: Path) -> None:
    registry = SchemaRegistry()
    register_schemas(registry)

    expected_entities = _expected_entities(configs_root)
    missing: list[str] = []

    for entity in sorted(expected_entities):
        for name in (entity, f"{entity}_input", f"{entity}_output"):
            try:
                registry.get_schema(name)
                registry.get_schema_columns(name)
            except Exception as exc:  # noqa: BLE001
                missing.append(f"{name}: {exc}")

    if missing:
        pytest.fail("Не найдены схемы Pandera:\n" + "\n".join(missing))
