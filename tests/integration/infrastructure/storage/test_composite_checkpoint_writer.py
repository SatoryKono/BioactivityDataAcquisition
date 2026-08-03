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
"""Integration tests for FileCompositeCheckpointWriter."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.storage.support.checkpoint_writer import (
    FileCompositeCheckpointWriter,
)

pytestmark = pytest.mark.integration


def test_write_atomic_persists_content(tmp_path: Path) -> None:
    """Successful atomic writes should leave only the final checkpoint file."""
    writer = FileCompositeCheckpointWriter(tmp_path)

    writer.write_atomic("state.json", '{"status": "ok"}')

    assert (tmp_path / "state.json").read_text() == '{"status": "ok"}'
    assert not (tmp_path / "state.tmp").exists()


def test_write_atomic_cleans_temp_and_propagates_keyboard_interrupt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cleanup temp files while preserving cancellation semantics."""
    writer = FileCompositeCheckpointWriter(tmp_path)
    path_cls = type(tmp_path)

    def _raise_keyboard_interrupt(self: Path, target: Path) -> Path:
        del self, target
        raise KeyboardInterrupt()

    monkeypatch.setattr(path_cls, "replace", _raise_keyboard_interrupt)

    with pytest.raises(KeyboardInterrupt):
        writer.write_atomic("state.json", '{"status": "interrupted"}')

    assert not (tmp_path / "state.json").exists()
    assert not (tmp_path / "state.tmp").exists()
