"""Compatibility support seam for run-all helper utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.run_all.support import (
        BatchRunResult as BatchRunResult,
    )
    from bioetl.interfaces.cli.commands.domains.run_all.support import (
        RunAllExecutionPlan as RunAllExecutionPlan,
    )
    from bioetl.interfaces.cli.commands.domains.run_all.support import (
        create_run_all_options as create_run_all_options,
    )
    from bioetl.interfaces.cli.commands.domains.run_all.support import (
        determine_batch_exit_code as determine_batch_exit_code,
    )
    from bioetl.interfaces.cli.commands.domains.run_all.support import (
        echo_batch_summary as echo_batch_summary,
    )
    from bioetl.interfaces.cli.commands.domains.run_all.support import (
        filter_pipelines_by_provider as filter_pipelines_by_provider,
    )
    from bioetl.interfaces.cli.commands.domains.run_all.support import (
        get_available_providers as get_available_providers,
    )
    from bioetl.interfaces.cli.commands.domains.run_all.support import (
        handle_destructive_confirmation as handle_destructive_confirmation,
    )
    from bioetl.interfaces.cli.commands.domains.run_all.support import (
        record_pipeline_failure as record_pipeline_failure,
    )
    from bioetl.interfaces.cli.commands.domains.run_all.support import (
        record_pipeline_result as record_pipeline_result,
    )
    from bioetl.interfaces.cli.commands.domains.run_all.support import (
        resolve_run_all_execution_plan as resolve_run_all_execution_plan,
    )
    from bioetl.interfaces.cli.commands.domains.run_all.support import (
        resolve_run_all_registry as resolve_run_all_registry,
    )
    from bioetl.interfaces.cli.commands.domains.run_all.support import (
        should_prompt_for_destructive_run as should_prompt_for_destructive_run,
    )
    from bioetl.interfaces.cli.commands.domains.run_all.support import (
        validate_provider as validate_provider,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.run_all.support")
