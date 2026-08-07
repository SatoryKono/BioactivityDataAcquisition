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
"""Tests for comprehensive @runtime_checkable coverage on all ports.

Ensures that all public port protocols in domain/ports/ are decorated with
@runtime_checkable, enabling isinstance() boundary checks at composition time.

See: TYPE-004 in docs/00-project/ai/rules/bioetl-ai-rules.md
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from bioetl.domain import ports


pytestmark = pytest.mark.architecture


def _discover_all_port_classes() -> list[str]:
    """Discover all Protocol classes ending with 'Port' in domain.ports."""
    return sorted(
        name
        for name in dir(ports)
        if name.endswith("Port")
        and not name.startswith("_")
        and inspect.isclass(getattr(ports, name))
    )


ALL_PORT_NAMES = _discover_all_port_classes()
EXPECTED_PORT_COUNT = 84
EXPECTED_PROTOCOL_CLASS_COUNT = 85
RULES_PATH = Path("docs/00-project/RULES.md")


class TestAllPortsRuntimeCheckable:
    """Every port protocol MUST be @runtime_checkable (TYPE-004)."""

    def test_port_count_matches_live_baseline(self) -> None:
        """Sanity check: the facade currently exports 84 ``*Port`` protocols."""
        assert len(ALL_PORT_NAMES) == EXPECTED_PORT_COUNT, (
            f"Expected {EXPECTED_PORT_COUNT} ports, found {len(ALL_PORT_NAMES)}. "
            f"If you added/removed a port, update this test. "
            f"Current ports: {ALL_PORT_NAMES}"
        )

    def test_runtime_checkable_count_is_reflected_in_rules_doc(self) -> None:
        """RULES.md must not publish stale runtime-checkable port counts."""
        rules_text = RULES_PATH.read_text(encoding="utf-8")

        assert (
            f"**{EXPECTED_PROTOCOL_CLASS_COUNT}** `port_protocol_classes`" in rules_text
        )
        assert "Все 68 порт" not in rules_text

    @pytest.mark.parametrize("port_name", ALL_PORT_NAMES)
    def test_port_is_runtime_checkable(self, port_name: str) -> None:
        """Each port MUST be @runtime_checkable for isinstance() checks."""
        port_class = getattr(ports, port_name)

        class _Dummy:
            pass

        try:
            isinstance(_Dummy(), port_class)
            is_checkable = True
        except TypeError:
            is_checkable = False

        assert is_checkable, (
            f"{port_name} MUST be decorated with @runtime_checkable. "
            f"Add `@runtime_checkable` before `class {port_name}(Protocol):`."
        )
