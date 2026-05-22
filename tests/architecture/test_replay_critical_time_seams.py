"""Architecture test for replay-critical application/composition time seams.

REQ-ARCH-031: Single source of truth for timestamps.
Replay-critical runtime and checkpoint paths must receive time explicitly via
ClockPort or injected timestamp parameters rather than reading wall-clock time
internally.
"""

from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGETS: tuple[Path, ...] = (
    Path("src/bioetl/domain/transformations"),
    Path("src/bioetl/application/runtime_timestamps.py"),
    Path("src/bioetl/application/composite/checkpoint"),
    Path("src/bioetl/application/services/control_plane"),
    Path("src/bioetl/application/services/control_plane/run_manifest_service.py"),
    Path("src/bioetl/composition/_pipeline_execution.py"),
)


def _iter_python_files(target: Path) -> list[Path]:
    resolved = REPO_ROOT / target
    if resolved.is_dir():
        return sorted(resolved.rglob("*.py"))
    return [resolved]


def _relative_path(py_file: Path) -> str:
    return py_file.relative_to(REPO_ROOT).as_posix()


def _datetime_now_calls(py_file: Path) -> list[str]:
    source = py_file.read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in {"now", "utcnow"}:
            continue
        if isinstance(node.func.value, ast.Name) and node.func.value.id == "datetime":
            calls.append(
                f"{_relative_path(py_file)}:{node.lineno}: datetime.{node.func.attr}()"
            )
        elif (
            isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == "datetime"
        ):
            calls.append(
                f"{_relative_path(py_file)}:{node.lineno}: datetime.datetime.{node.func.attr}()"
            )
    return calls


def _current_utc_time_refs(py_file: Path) -> list[str]:
    if "src/bioetl/application/composite/checkpoint/" not in py_file.as_posix():
        return []
    source = py_file.read_text(encoding="utf-8")
    tree = ast.parse(source)
    refs: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "bioetl.domain.context":
            for alias in node.names:
                if alias.name == "current_utc_time":
                    refs.append(
                        f"{_relative_path(py_file)}:{node.lineno}: imports current_utc_time"
                    )
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "current_utc_time"
        ):
            refs.append(
                f"{_relative_path(py_file)}:{node.lineno}: current_utc_time()"
            )
    return refs


def test_replay_critical_time_seams_do_not_read_wall_clock_directly() -> None:
    """Replay-critical helpers must not create implicit current timestamps."""
    violations: list[str] = []
    for target in TARGETS:
        for py_file in _iter_python_files(target):
            violations.extend(_datetime_now_calls(py_file))
            violations.extend(_current_utc_time_refs(py_file))

    assert not violations, (
        "Wall-clock reads found in replay-critical runtime paths:\n"
        + "\n".join(f"  - {item}" for item in violations)
        + "\n\nInject ClockPort or explicit timestamps into runtime/checkpoint/control-plane seams."
    )
