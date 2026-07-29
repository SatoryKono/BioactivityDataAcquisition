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
"""Guardrails for retired application-core constructor kwargs."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SURFACES = (
    ROOT / "src/bioetl/application/core/runner.py",
    ROOT / "src/bioetl/application/core/_runner_dependency_support.py",
    ROOT / "src/bioetl/application/core/batch_writer.py",
    ROOT / "src/bioetl/application/core/postrun/service.py",
    ROOT / "src/bioetl/application/core/postrun/_service_collaborators.py",
)


@pytest.mark.architecture
def test_application_core_constructors_do_not_accept_unbounded_legacy_kwargs() -> None:
    """Runner, writer, and postrun seams must use typed dependency inputs."""
    offenders = {
        path.relative_to(ROOT).as_posix(): needle
        for path in SURFACES
        for needle in ("**legacy_kwargs", "legacy_kwargs", "resolve_legacy_")
        if needle in path.read_text(encoding="utf-8")
    }

    assert offenders == {}
