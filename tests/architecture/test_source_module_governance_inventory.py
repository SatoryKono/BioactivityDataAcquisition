"""Architecture tests for oversized source module governance."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "quality" / "debt_scorecard.yaml"


YamlMap = dict[str, object]


def _load_yaml(path: Path) -> YamlMap:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return cast(YamlMap, payload)


@pytest.mark.architecture
def test_oversized_source_module_inventory_tracks_current_top_modules() -> None:
    """Largest source modules must be tracked and split-on-touch guarded."""
    payload = _load_yaml(CONFIG_PATH)
    inventory = cast(YamlMap, payload["oversized_source_module_inventory"])
    entries = cast(list[YamlMap], inventory["top_modules"])
    max_lines = int(inventory["max_tracked_lines"])

    assert inventory["split_on_touch"] is True
    assert inventory["linked_issue"] == "#4679"
    for entry in entries:
        path = ROOT / cast(str, entry["path"])
        assert path.exists()
        actual_lines = len(path.read_text(encoding="utf-8").splitlines())
        assert actual_lines == int(entry["lines"])
        assert actual_lines <= max_lines
        assert cast(str, entry["owner"]).strip()
        assert cast(str, entry["target_split"]).strip()
