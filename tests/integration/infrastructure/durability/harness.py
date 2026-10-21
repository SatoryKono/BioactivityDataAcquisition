"""Child-process barrier used by the durability construction smoke."""

from __future__ import annotations

from collections.abc import Callable

from tests.integration.infrastructure.durability._child_runner import run_child


class DurabilityHarness:
    """Run a picklable probe outside the parent pytest process."""

    def run_isolated(
        self,
        target: Callable[..., None],
        args: tuple[object, ...],
        *,
        timeout_s: float = 30.0,
    ) -> int:
        """Return the child exit code, or raise when the child overruns."""
        return run_child(target, args, timeout_s=timeout_s)
