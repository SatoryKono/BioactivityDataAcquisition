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
import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.storage.support.checkpoint_writer import (
    FileCompositeCheckpointWriter,
)

pytestmark = pytest.mark.integration


def test_manifest_history_survives_successful_composite_cleanup(tmp_path: Path) -> None:
    from bioetl.application.composite.checkpoint.persistence_service import (
        CompositeCheckpointPersistenceParams,
        CompositeCheckpointPersistenceService,
    )
    from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
    from bioetl.domain.composite.state import CompositePipelineState
    from bioetl.infrastructure.control_plane._file_artifact_lifecycle_refs import (
        _append_checkpoint_candidates,
    )

    root = tmp_path / "checkpoints" / "composite"
    writer = FileCompositeCheckpointWriter(root)
    service = CompositeCheckpointPersistenceService(
        CompositeCheckpointPersistenceParams(
            composite_name="composite_publication",
            checkpoint_filename="resume.json",
            glob_pattern="*.json",
            storage=writer,
            logger=MagicMock(),
        )
    )
    state = CompositeCheckpointState(
        composite_name="composite_publication", run_id="run-1", manifest_id="manifest-1"
    )
    service.save(state)
    first_index = json.loads(writer.read(".history/by_manifest/manifest-1.json"))
    first_content = writer.read(first_index["history_path"])
    completed = replace(state, state=CompositePipelineState.COMPLETED)
    service.save(completed)
    service.delete()

    assert not writer.exists("resume.json")
    assert writer.read(first_index["history_path"]) == first_content
    index = json.loads(writer.read(".history/by_manifest/manifest-1.json"))
    assert json.loads(writer.read(index["history_path"])) == completed.to_dict()
    assert first_index["history_path"] != index["history_path"]
    candidates, issues = [], []
    _append_checkpoint_candidates(
        candidates,
        issues,
        tmp_path / "control",
        SimpleNamespace(
            pipeline_name=state.composite_name,
            run_id=state.run_id,
            manifest_id=state.manifest_id,
        ),
    )
    assert issues == []
    paths = {path for _, path in candidates}
    assert root / index["history_path"] in paths
    assert root / ".history/by_manifest/manifest-1.json" in paths


def test_history_failure_does_not_publish_resume_checkpoint(tmp_path: Path) -> None:
    from bioetl.application.composite.checkpoint.persistence_service import (
        CompositeCheckpointPersistenceParams,
        CompositeCheckpointPersistenceService,
    )
    from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
    from bioetl.domain.exceptions import CheckpointConflictError

    storage = MagicMock()
    storage.write_atomic.side_effect = OSError("history disk full")
    service = CompositeCheckpointPersistenceService(
        CompositeCheckpointPersistenceParams(
            composite_name="composite_publication",
            checkpoint_filename="resume.json",
            glob_pattern="*.json",
            storage=storage,
            logger=MagicMock(),
        )
    )
    with pytest.raises(CheckpointConflictError, match="history disk full"):
        service.save(
            CompositeCheckpointState(
                composite_name="composite_publication",
                run_id="run-1",
                manifest_id="manifest-1",
            )
        )
    assert all(
        call.args[0] != "resume.json" for call in storage.write_atomic.call_args_list
    )


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
