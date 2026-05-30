"""Architecture gate: all config and contract YAML surfaces must parse cleanly."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
YAML_SURFACES = (
    PROJECT_ROOT / "configs" / "contracts",
    PROJECT_ROOT / "configs" / "entities",
)


def _iter_yaml_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.yaml") if path.is_file())


@pytest.mark.architecture
@pytest.mark.parametrize(
    "yaml_path",
    [
        pytest.param(path, id=path.relative_to(PROJECT_ROOT).as_posix())
        for surface in YAML_SURFACES
        for path in _iter_yaml_files(surface)
    ],
)
def test_config_and_contract_yaml_files_parse(yaml_path: Path) -> None:
    """Every tracked entity/contract YAML file must load without syntax errors."""
    payload = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    assert payload is not None or yaml_path.stat().st_size == 0
