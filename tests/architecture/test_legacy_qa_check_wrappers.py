"""Architecture tests for legacy QA check wrappers."""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_check_architecture_wrapper_delegates_to_canonical() -> None:
    repo_root = _repo_root()
    wrapper_path = repo_root / "src" / "tools" / "scripts" / "check_architecture.py"

    assert wrapper_path.exists(), "src/tools/scripts/check_architecture.py must exist"
    content = wrapper_path.read_text(encoding="utf-8")
    assert "runpy.run_path" in content
    assert "scripts" in content
    assert "qa" in content
    assert "check_architecture.py" in content


def test_check_application_deps_wrapper_delegates_to_canonical() -> None:
    repo_root = _repo_root()
    wrapper_path = (
        repo_root / "src" / "tools" / "scripts" / "check_application_deps.py"
    )

    assert (
        wrapper_path.exists()
    ), "src/tools/scripts/check_application_deps.py must exist"
    content = wrapper_path.read_text(encoding="utf-8")
    assert "runpy.run_path" in content
    assert "scripts" in content
    assert "qa" in content
    assert "check_application_deps.py" in content


def test_check_constructor_args_wrapper_delegates_to_canonical() -> None:
    repo_root = _repo_root()
    wrapper_path = repo_root / "src" / "tools" / "scripts" / "check_constructor_args.py"

    assert (
        wrapper_path.exists()
    ), "src/tools/scripts/check_constructor_args.py must exist"
    content = wrapper_path.read_text(encoding="utf-8")
    assert "runpy.run_path" in content
    assert "scripts" in content
    assert "qa" in content
    assert "check_constructor_args.py" in content
