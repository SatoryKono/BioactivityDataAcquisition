import pytest
from pathlib import Path
from bioetl.infrastructure.observability import metric_inventory_discovery
from bioetl.infrastructure.observability import metric_inventory_scan

pytestmark = pytest.mark.unit


def test_directory_walk_normal(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("def f(): pass", encoding="utf-8")
    (tmp_path / "b.txt").write_text("text", encoding="utf-8")
    paths = metric_inventory_discovery._iter_text_files(tmp_path)
    assert len(paths) == 1
    assert paths[0].name == "a.py"


def test_directory_glob_normal(tmp_path: Path) -> None:
    (tmp_path / "src" / "bioetl" / "infrastructure" / "observability").mkdir(
        parents=True
    )
    (
        tmp_path
        / "src"
        / "bioetl"
        / "infrastructure"
        / "observability"
        / "_metrics_defs_a.py"
    ).write_text('metric = "bioetl_lifecycle_probe"\n', encoding="utf-8")
    result = metric_inventory_scan._scan_registered_metric_names(tmp_path)
    assert result == {"bioetl_lifecycle_probe"}
