"""Cold imports from a source checkout and an unrelated working directory.

Source and sdist expose the declared tooling closure; installed wheel smoke
uses a separate environment without either source path.
"""

import json
import csv
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.architecture
@pytest.mark.unit
def test_cold_imports(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    quality_root = repo_root / "scripts/engineering/quality"
    manifest = repo_root / "reports/quality/quality-move-qm01/file_move_plan.csv"
    with manifest.open(encoding="utf-8", newline="") as handle:
        paths = [row["target_path"] for row in csv.DictReader(handle)]
    assert len(paths) == len(set(paths)) == 30
    assert set(paths) == {
        path.relative_to(repo_root).as_posix() for path in quality_root.glob("*.py")
    }
    modules = [
        path.removesuffix(".py").replace("/", ".").removesuffix(".__init__")
        for path in paths
    ]

    for module in modules:
        # -I ignores inherited PYTHONPATH and cwd. Each module gets a fresh process.
        code = (
            "import importlib, json, sys; "
            f"sys.path[:0] = {list(map(str, (repo_root / 'src', repo_root)))!r}; "
            f"module = importlib.import_module({module!r}); "
            "print(json.dumps(module.__file__))"
        )
        result = subprocess.run(
            [sys.executable, "-I", "-c", code],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, f"Failed to import {module}: {result.stderr}"
        expected = quality_root / (
            "__init__.py"
            if module.endswith(".quality")
            else module.rsplit(".", 1)[1] + ".py"
        )
        assert Path(json.loads(result.stdout)).resolve() == expected.resolve(), (
            f"Unexpected origin for {module}: {result.stdout}"
        )
