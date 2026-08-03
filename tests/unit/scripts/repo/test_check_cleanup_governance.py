# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for broad cleanup instruction governance."""

from __future__ import annotations

import pytest

from pathlib import Path

import yaml

from scripts.engineering.repo import check_cleanup_governance as module


pytestmark = pytest.mark.unit


def _write_config(tmp_path: Path, allowed_patterns: list[str] | None = None) -> None:
    config_path = tmp_path / module.CONFIG_PATH
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "allowed_broad_cleanup_examples": [
                    {
                        "path": "docs/allowed.md",
                        "reason": "disallowed example",
                        "patterns": allowed_patterns or ["rm -rf data/"],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_collect_broad_cleanup_violations_flags_unallowed_instruction(
    tmp_path: Path,
) -> None:
    (tmp_path / ".git").mkdir()
    _write_config(tmp_path)
    docs_path = tmp_path / "docs" / "guide.md"
    docs_path.parent.mkdir()
    docs_path.write_text("Run `rm -rf data/` to reset everything.\n", encoding="utf-8")

    violations = module.collect_broad_cleanup_violations(tmp_path)

    assert [(item.path, item.line_number) for item in violations] == [
        ("docs/guide.md", 1)
    ]


def test_collect_broad_cleanup_violations_allows_registered_disallowed_example(
    tmp_path: Path,
) -> None:
    (tmp_path / ".git").mkdir()
    _write_config(tmp_path, ["git clean -fdx"])
    docs_path = tmp_path / "docs" / "allowed.md"
    docs_path.parent.mkdir()
    docs_path.write_text("Disallowed: `git clean -fdx`.\n", encoding="utf-8")

    assert module.collect_broad_cleanup_violations(tmp_path) == []
