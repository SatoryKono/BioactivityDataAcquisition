"""Architecture tests for legacy schema compatibility wrappers."""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_config_matrix_generator_wrapper_delegates_to_canonical() -> None:
    repo_root = _repo_root()
    wrapper_path = (
        repo_root / "src" / "tools" / "scripts" / "config_matrix_generator.py"
    )

    assert wrapper_path.exists(), (
        "src/tools/scripts/config_matrix_generator.py must exist"
    )
    content = wrapper_path.read_text(encoding="utf-8")
    assert "runpy.run_path" in content
    assert "scripts" in content
    assert "schema" in content
    assert "generate_config_matrix.py" in content


def test_validate_unified_configs_wrapper_delegates_to_canonical() -> None:
    repo_root = _repo_root()
    wrapper_path = (
        repo_root / "src" / "tools" / "scripts" / "validate_unified_configs.py"
    )

    assert wrapper_path.exists(), (
        "src/tools/scripts/validate_unified_configs.py must exist"
    )
    content = wrapper_path.read_text(encoding="utf-8")
    assert "runpy.run_path" in content
    assert "scripts" in content
    assert "schema" in content
    assert "validate_unified_configs.py" in content
