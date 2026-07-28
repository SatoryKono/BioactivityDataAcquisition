"""ARCH-CR-04: provenance blank rejection and fallback readiness blockers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.application.services.control_plane.manifest.execution_identity_support import (
    fallback_code_provenance_state,
)
from bioetl.application.services.control_plane.manifest.validation_provenance import (
    _validate_executable_code_provenance,
)


def _spec(**launch: object) -> SimpleNamespace:
    return SimpleNamespace(launch_context=dict(launch))


def _prov(**fields: object) -> SimpleNamespace:
    return SimpleNamespace(
        git_commit=fields.get("git_commit"),
        dependency_lock_hash=fields.get("dependency_lock_hash"),
        source_revision_state=fields.get("source_revision_state", "clean"),
        resolved_config_hash=fields.get("resolved_config_hash", "r" * 64),
        effective_config_hash=fields.get("effective_config_hash", "e" * 64),
    )


def test_validate_executable_code_provenance_rejects_whitespace_git_commit() -> None:
    with pytest.raises(RuntimeError, match="git_commit"):
        _validate_executable_code_provenance(
            _spec(),  # type: ignore[arg-type]
            _prov(git_commit="   ", dependency_lock_hash="lock"),  # type: ignore[arg-type]
        )


def test_validate_executable_code_provenance_rejects_whitespace_lock_hash() -> None:
    with pytest.raises(RuntimeError, match="dependency_lock_hash"):
        _validate_executable_code_provenance(
            _spec(),  # type: ignore[arg-type]
            _prov(git_commit="abc", dependency_lock_hash=" \t "),  # type: ignore[arg-type]
        )


def test_fallback_code_provenance_requires_nonblank_lock_for_ready() -> None:
    state = fallback_code_provenance_state(
        _prov(  # type: ignore[arg-type]
            git_commit="abc123",
            dependency_lock_hash="  ",
            source_revision_state="clean",
        )
    )
    assert state["strict_code_provenance_ready"] is False
    assert "dependency_lock_hash_missing" in state["strict_code_provenance_blockers"]
    assert state["dependency_lock_state"] == "missing"


def test_fallback_code_provenance_ready_when_commit_lock_clean() -> None:
    state = fallback_code_provenance_state(
        _prov(  # type: ignore[arg-type]
            git_commit="abc123",
            dependency_lock_hash="lockhash",
            source_revision_state="clean",
        )
    )
    assert state["strict_code_provenance_ready"] is True
    assert state["strict_code_provenance_blockers"] == []
    assert state["dependency_lock_state"] == "present"
