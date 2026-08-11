"""Unit tests for the Zed environment doctor (stdlib-only helper)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DEV_SCRIPTS = ROOT / "scripts" / "engineering" / "dev"

pytestmark = [pytest.mark.unit]


@pytest.fixture(scope="module")
def doctor_module():
    if str(DEV_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(DEV_SCRIPTS))
    from scripts.engineering.dev import zed_env_doctor

    return zed_env_doctor


def test_format_report_healthy(doctor_module) -> None:
    text = doctor_module.format_report([])
    assert "ok" in text
    assert "ModuleNotFoundError" not in text


def test_check_modules_missing(doctor_module) -> None:
    findings = doctor_module.check_modules(["no_such_package_for_zed_doctor_xyz"])
    assert findings[0].code == "missing_module"
    assert "setup_env_windows.ps1" in findings[0].recovery


def test_check_interpreter_missing_venv(doctor_module, tmp_path: Path) -> None:
    findings = doctor_module.check_interpreter(repo_root=tmp_path)
    assert findings[0].code == "missing_venv"


def test_ensure_ready_exits_without_traceback(
    doctor_module, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        doctor_module,
        "diagnose",
        lambda **_kwargs: [
            doctor_module.Finding(
                code="missing_module",
                message="Required package is not importable: import-linter (importlinter)",
                recovery=r".\scripts\engineering\dev\setup_env_windows.ps1",
            )
        ],
    )
    with pytest.raises(SystemExit) as excinfo:
        doctor_module.ensure_ready(modules=("importlinter",))
    assert excinfo.value.code == 2


def test_tracked_zed_keymap_has_unique_reachable_bindings() -> None:
    """Strict JSON parsing rejects shadowed key chords in the tracked keymap."""

    def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    payload = json.loads(
        (ROOT / ".zed" / "keymap.json").read_text(encoding="utf-8"),
        object_pairs_hook=_unique_object,
    )
    bindings = payload["bindings"]

    assert bindings["ctrl-d"] == "editor::SelectNextOccurrence"
    assert bindings["ctrl-alt-d"] == "editor::DuplicateLine"
