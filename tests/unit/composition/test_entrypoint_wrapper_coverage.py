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
"""Delegation coverage for retained composition entrypoint wrappers."""

import pytest

from bioetl.composition import entrypoints, observability_api

pytestmark = pytest.mark.unit


def test_start_metrics_server_forwards_all_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = object()
    observed: dict[str, object] = {}

    def implementation(**kwargs: object) -> bool:
        observed.update(kwargs)
        return True

    monkeypatch.setattr(observability_api, "start_metrics_server", implementation)

    assert entrypoints.start_metrics_server(
        9100,
        "127.0.0.1",
        fail_fast=True,
        retry_count=5,
        retry_delay=0.25,
        logger=logger,
    )
    assert observed == {
        "port": 9100,
        "addr": "127.0.0.1",
        "fail_fast": True,
        "retry_count": 5,
        "retry_delay": 0.25,
        "logger": logger,
    }


def test_load_pipeline_config_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    """The wrapper delegates to composite_api.load_pipeline_config."""
    # Mock the actual implementation that gets imported inside the function
    sentinel = object()
    monkeypatch.setattr(
        "bioetl.composition.composite_catalog.load_pipeline_config",
        lambda name: sentinel,
    )

    assert entrypoints.load_pipeline_config("chembl_activity") is sentinel
