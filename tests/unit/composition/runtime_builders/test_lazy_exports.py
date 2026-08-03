# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for runtime builder package-level lazy exports."""

from __future__ import annotations

import pytest

from bioetl.composition import runtime_builders
from bioetl.composition.runtime_builders import _run_manifest_data_roots
from bioetl.composition.runtime_builders import runner_builder

pytestmark = pytest.mark.unit


def test_build_pipeline_runner_lazy_export_delegates(monkeypatch) -> None:
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fake_build_pipeline_runner(*args: object, **kwargs: object) -> str:
        calls.append((args, kwargs))
        return "runner"

    monkeypatch.setattr(
        runner_builder,
        "build_pipeline_runner",
        fake_build_pipeline_runner,
    )

    assert (
        runtime_builders.build_pipeline_runner("ctx", registry="registry") == "runner"
    )
    assert calls == [(("ctx",), {"registry": "registry"})]


def test_control_plane_root_lazy_export_delegates(monkeypatch) -> None:
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fake_control_plane_root(*args: object, **kwargs: object) -> str:
        calls.append((args, kwargs))
        return "root"

    monkeypatch.setattr(
        _run_manifest_data_roots,
        "control_plane_root",
        fake_control_plane_root,
    )

    assert runtime_builders.control_plane_root("settings", "store") == "root"
    assert calls == [(("settings", "store"), {})]
