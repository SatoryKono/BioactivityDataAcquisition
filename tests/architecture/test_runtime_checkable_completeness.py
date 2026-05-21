"""Tests for comprehensive @runtime_checkable coverage on all ports.

Ensures that all public port protocols in domain/ports/ are decorated with
@runtime_checkable, enabling isinstance() boundary checks at composition time.

See: TYPE-004 in docs/00-project/ai/rules/bioetl-ai-rules.md
"""

from __future__ import annotations

import inspect

import pytest

from bioetl.domain import ports


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
EXPECTED_PORT_COUNT = 80


class TestAllPortsRuntimeCheckable:
    """Every port protocol MUST be @runtime_checkable (TYPE-004)."""

    def test_port_count_matches_live_baseline(self) -> None:
        """Sanity check: the facade currently exports 80 port protocols."""
        assert len(ALL_PORT_NAMES) == EXPECTED_PORT_COUNT, (
            f"Expected {EXPECTED_PORT_COUNT} ports, found {len(ALL_PORT_NAMES)}. "
            f"If you added/removed a port, update this test. "
            f"Current ports: {ALL_PORT_NAMES}"
        )

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
