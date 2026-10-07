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
"""Filesystem seam for repository env documents."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.config.repository_source_environment import (
    read_repository_env_text,
)

pytestmark = pytest.mark.unit


def test_read_repository_env_text_returns_none_when_the_file_is_absent(
    tmp_path: Path,
) -> None:
    assert read_repository_env_text(tmp_path / "missing.env") is None


def test_read_repository_env_text_reads_the_explicit_file(tmp_path: Path) -> None:
    document = tmp_path / "repository.env"
    document.write_text("EXAMPLE_KEY=value\n", encoding="utf-8")

    assert read_repository_env_text(document) == "EXAMPLE_KEY=value\n"
