"""Infrastructure-level enum file loading with direct I/O operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

__all__ = ["load_chembl_enums_from_file"]


def load_chembl_enums_from_file(
    yaml_path: Path | None = None,
) -> dict[str, Any]:  # Any: Dynamic YAML content structure
    """Load ChEMBL enum configurations from YAML file.

    This is an infrastructure-level function that performs direct file I/O.

    Args:
        yaml_path: Path to YAML file. If None, uses default path.

    Returns:
        Dictionary containing all enum configurations
    """
    if yaml_path is None:
        yaml_path = Path("configs/enums/chembl.yaml")

    with yaml_path.open() as f:
        return yaml.safe_load(f)
