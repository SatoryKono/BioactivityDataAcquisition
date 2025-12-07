from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

BASELINE_PATH = Path(__file__).parent / "class_inventory_baseline.json"


def _count_classes(root: Path) -> int:
    total = 0
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        code = path.read_text(encoding="utf-8")
        tree = ast.parse(code)
        total += sum(isinstance(node, ast.ClassDef) for node in ast.walk(tree))
    return total


def test_class_inventory_zero_sum(bioetl_root: Path) -> None:
    if not BASELINE_PATH.exists():
        pytest.fail(
            f"Базлайн {BASELINE_PATH} отсутствует. "
            "Сгенерируйте class_inventory_baseline.json перед запуском."
        )

    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    expected_total = baseline.get("total_classes")
    if expected_total is None:
        pytest.fail("В базлайне нет ключа total_classes.")

    current_total = _count_classes(bioetl_root)

    assert current_total == expected_total, (
        f"Изменилось число классов: было {expected_total}, стало {current_total}"
    )
