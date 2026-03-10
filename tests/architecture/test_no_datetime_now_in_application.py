"""Architecture test: application layer must use ClockPort instead of datetime.now()."""

from __future__ import annotations

import ast
from pathlib import Path

APPLICATION_DIR = Path("src/bioetl/application")


class TestNoDatetimeNowInApplication:
    """Ensure application layer uses injected clocks for timestamp creation."""

    def test_no_datetime_now_in_application(self) -> None:
        if APPLICATION_DIR.exists():
            base = APPLICATION_DIR
        else:
            base = Path(__file__).parent.parent.parent / APPLICATION_DIR

        violations: list[str] = []
        for py_file in base.rglob("*.py"):
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)

            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"now", "utcnow"}
                ):
                    if (
                        isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "datetime"
                    ):
                        relative_path = py_file.relative_to(base)
                        violations.append(
                            f"{relative_path}:{node.lineno}: datetime.{node.func.attr}()"
                        )
                    elif (
                        isinstance(node.func.value, ast.Attribute)
                        and node.func.value.attr == "datetime"
                    ):
                        relative_path = py_file.relative_to(base)
                        violations.append(
                            f"{relative_path}:{node.lineno}: datetime.datetime.{node.func.attr}()"
                        )

        assert not violations, (
            "datetime.now()/utcnow() found in application layer:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\nUse ClockPort.now_utc() via constructor injection instead."
        )
