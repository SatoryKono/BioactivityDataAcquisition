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
"""Behavior coverage for the typed composition-root registry."""

import pytest

from bioetl.composition import entrypoints

pytestmark = pytest.mark.unit


def test_register_replaces_factory_for_the_same_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(entrypoints, "_REGISTRY", {})

    class Port:
        pass

    first = object()
    second = object()
    entrypoints.register(Port, lambda: first)
    entrypoints.register(Port, lambda: second)

    assert entrypoints.resolve(Port) is second


def test_registered_ports_returns_factory_without_invoking_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(entrypoints, "_REGISTRY", {})

    class Port:
        pass

    calls = 0

    def factory() -> object:
        nonlocal calls
        calls += 1
        return object()

    entrypoints.register(Port, factory)

    assert entrypoints.registered_ports() == {Port: factory}
    assert calls == 0
