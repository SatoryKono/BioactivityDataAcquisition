"""Unit tests for config path lint filesystem safeguards."""

from __future__ import annotations

import pytest

from scripts.schema import lint_config_paths

pytestmark = pytest.mark.unit


class _BrokenStatPath:
    def is_file(self) -> bool:
        raise OSError(22, "Invalid argument")


def test_lint_config_paths_safe_is_file_returns_false_on_oserror() -> None:
    assert lint_config_paths._safe_is_file(_BrokenStatPath()) is False  # type: ignore[arg-type]


def test_safe_is_file_returns_true_for_regular_file(tmp_path) -> None:  # type: ignore[no-untyped-def]
    target = tmp_path / "config.md"
    target.write_text("ok", encoding="utf-8")

    assert lint_config_paths._safe_is_file(target) is True
