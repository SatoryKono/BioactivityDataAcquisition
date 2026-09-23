"""Ratchet and unit coverage for AUD-002 mapping IO extract (#10526)."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.graph.sync_pkg import _core
from memory.graph.sync_pkg import mapping_io

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
MOD = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "mapping_io.py"
_CORE_LOC_BEFORE = 15140


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_mapping_io_owns_helpers_and_shrinks_core() -> None:
    core_text = CORE.read_text(encoding="utf-8")
    mod_text = MOD.read_text(encoding="utf-8")
    assert "def _read_yaml(" not in core_text
    assert "def _memory_mapping_path(" not in core_text
    assert "def _read_yaml(" in mod_text
    assert _core._read_yaml is mapping_io._read_yaml
    assert _loc(CORE) < _CORE_LOC_BEFORE
    assert _loc(MOD) < 500


def test_yaml_json_and_mapping_path(tmp_path: Path) -> None:
    yaml_path = tmp_path / "m.yaml"
    yaml_path.write_text("file_structure:\n  promoted_hubs: [src]\n", encoding="utf-8")
    payload = mapping_io._read_yaml(yaml_path)
    assert mapping_io._mapping_section(payload, "file_structure")["promoted_hubs"] == [
        "src"
    ]
    json_path = tmp_path / "m.json"
    json_path.write_text('{"a": 1}\n', encoding="utf-8")
    assert mapping_io._read_json(json_path) == {"a": 1}
    assert mapping_io._mapping_dict_or_empty([]) == {}
    preferred = tmp_path / mapping_io.DEFAULT_MEMORY_MAPPING_PATH
    preferred.parent.mkdir(parents=True)
    preferred.write_text("x: 1\n", encoding="utf-8")
    assert mapping_io._memory_mapping_path(tmp_path) == preferred
    assert mapping_io._load_memory_mapping(tmp_path) == {"x": 1}
