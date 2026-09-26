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
"""Regression guards for runtime/admin time seam normalization."""

from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


@pytest.mark.architecture
def test_targeted_runtime_admin_paths_do_not_reintroduce_wall_clock_fallbacks() -> None:
    assert "current_utc_time(" not in _read(
        "src/bioetl/application/services/execution/pipeline_run_context_service.py"
    )
    assert "current_utc_time(" not in _read(
        "src/bioetl/application/services/control_plane/manifest/service.py"
    )
    assert "current_utc_time(" not in _read(
        "src/bioetl/application/core/preflight/health_aggregator.py"
    )
    assert "current_utc_time(" not in _read(
        "src/bioetl/application/core/postrun/metadata_write_service.py"
    )
    assert "current_utc_time(" not in _read(
        "src/bioetl/application/composite/checkpoint/_anchor_context.py"
    )
    assert "current_utc_time(" not in _read(
        "src/bioetl/application/composite/checkpoint/_state_support.py"
    )
    assert "current_utc_time(" not in _read(
        "src/bioetl/application/composite/checkpoint/_checkpoint_runtime.py"
    )
    assert "default_factory=current_utc_time" not in _read(
        "src/bioetl/application/services/execution/pipeline_runner_models.py"
    )


@pytest.mark.architecture
def test_context_module_no_longer_uses_wall_clock_defaults_for_runtime_contexts() -> (
    None
):
    contents = _read("src/bioetl/domain/context.py")
    time_contents = _read("src/bioetl/domain/context_time.py")

    assert (
        "started_at: datetime = field(default_factory=current_utc_time)" not in contents
    )
    assert "started_at or current_utc_time()" not in contents
    assert "def current_utc_time(" not in contents
    assert "datetime.now(" not in contents
    assert "resolve_context_started_at(" in contents
    assert "clock.now()" in time_contents


@pytest.mark.architecture
def test_effective_config_domain_artifact_uses_deterministic_timestamp_defaults() -> (
    None
):
    contents = _read("src/bioetl/domain/control_plane/effective_config_artifact.py")

    assert "default_factory=_current_utc_time" not in contents
    assert "from bioetl.domain.context import current_utc_time" not in contents
    assert "datetime.now(" not in contents
