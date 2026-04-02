"""Compatibility support seam for run-all execution helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.run_all.execution import (
        run_all_pipelines_async as run_all_pipelines_async,
    )
    from bioetl.interfaces.cli.commands.domains.run_all.execution import (
        RunAllBatchExecutionRequest as RunAllBatchExecutionRequest,
    )
    from bioetl.interfaces.cli.commands.domains.run_all.execution import (
        run_batch_with_policy as run_batch_with_policy,
    )
    from bioetl.interfaces.cli.commands.domains.run_all.execution import (
        RunAllPolicyRequest as RunAllPolicyRequest,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.run_all.execution")
