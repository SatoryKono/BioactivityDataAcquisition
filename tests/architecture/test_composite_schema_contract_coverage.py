"""Architecture test: composite configs must have schema and Gold contract coverage."""

from __future__ import annotations

from pathlib import Path

from bioetl.composition.bootstrap.runtime.composite import (
    COMPOSITE_GOLD_SCHEMA_REGISTRY,
)
from bioetl.domain.contracts.gold import composite as composite_contracts


def _expected_contract_name(stem: str) -> str:
    return f"Composite{stem.capitalize()}GoldSchema"


def test_each_composite_pipeline_has_schema_and_contract() -> None:
    """Every composite pipeline config must define matching schema and contract."""
    config_dir = Path("configs/pipelines/composite")
    schema_dir = Path("configs/schemas/composite")

    config_stems = sorted(path.stem for path in config_dir.glob("*.yaml"))
    assert config_stems, "No composite pipeline configs found"

    missing_schemas: list[str] = []
    missing_contracts: list[str] = []
    missing_registry_links: list[str] = []

    for stem in config_stems:
        schema_path = schema_dir / f"{stem}.yaml"
        if not schema_path.exists():
            missing_schemas.append(str(schema_path))

        contract_name = _expected_contract_name(stem)
        if not hasattr(composite_contracts, contract_name):
            missing_contracts.append(contract_name)

        if stem not in COMPOSITE_GOLD_SCHEMA_REGISTRY:
            missing_registry_links.append(stem)

    assert not missing_schemas, "Missing composite schema YAML files:\n" + "\n".join(
        f"  - {path}" for path in missing_schemas
    )
    assert not missing_contracts, (
        "Missing composite Gold contract classes:\n"
        + "\n".join(f"  - {name}" for name in missing_contracts)
    )
    assert not missing_registry_links, (
        "Missing composite contract registry links in runner bootstrap:\n"
        + "\n".join(f"  - {stem}" for stem in missing_registry_links)
    )
