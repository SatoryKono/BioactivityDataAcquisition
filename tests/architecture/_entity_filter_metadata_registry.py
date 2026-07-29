# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Helpers for the shared entity filter metadata registry."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "configs" / "quality" / "entity_filter_metadata_registry.yaml"


def load_shared_filter_metadata(config_path: str) -> dict[str, Any]:
    """Load the shared filters.metadata payload for one entity config path."""
    payload = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), REGISTRY_PATH

    profiles = payload.get("profiles", {})
    assert isinstance(profiles, dict), REGISTRY_PATH

    for profile in profiles.values():
        if not isinstance(profile, dict):
            continue
        applies_to = profile.get("applies_to", [])
        if config_path not in applies_to:
            continue
        filter_metadata = profile.get("filter_metadata", {})
        assert isinstance(filter_metadata, dict), REGISTRY_PATH
        return deepcopy(filter_metadata)

    raise AssertionError(
        f"{config_path} is not registered in {REGISTRY_PATH.relative_to(ROOT).as_posix()}"
    )
