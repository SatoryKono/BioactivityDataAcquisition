"""Quality governance utilities for technical-debt gates."""

from __future__ import annotations

from bioetl.infrastructure.quality.architecture_debt_reduction import (
    build_architecture_debt_execution_plan,
    find_latest_architecture_debt_tasks_file,
    load_architecture_debt_tasks,
)
from bioetl.infrastructure.quality.architecture_debt_task_generation import (
    generate_architecture_debt_tasks_payload,
)
from bioetl.infrastructure.quality.architecture_quality_scorecard import (
    build_architecture_quality_scorecard,
    write_architecture_quality_scorecard,
)
from bioetl.infrastructure.quality.debt_scorecard import (
    build_exemption_inventory,
    compute_integral_debt_score,
    evaluate_debt_scorecard,
    load_debt_scorecard,
    split_growth_violations_by_severity,
    validate_debt_scorecard,
    validate_scorecard_registry_sync,
)
from bioetl.infrastructure.quality.exemptions_registry import (
    EXEMPTION_REGISTRIES_ALLOW_EMPTY,
    REQUIRED_EXEMPTION_REGISTRIES,
    build_module_path_key,
    get_registry_values,
    load_exemptions_registry,
    resolve_registry_value,
    validate_exemption_key_normalization,
    validate_exemption_target_references,
    validate_exemptions_registry,
)

__all__ = [
    "EXEMPTION_REGISTRIES_ALLOW_EMPTY",
    "REQUIRED_EXEMPTION_REGISTRIES",
    "build_architecture_debt_execution_plan",
    "build_architecture_quality_scorecard",
    "build_exemption_inventory",
    "build_module_path_key",
    "compute_integral_debt_score",
    "evaluate_debt_scorecard",
    "find_latest_architecture_debt_tasks_file",
    "generate_architecture_debt_tasks_payload",
    "get_registry_values",
    "load_architecture_debt_tasks",
    "load_debt_scorecard",
    "load_exemptions_registry",
    "resolve_registry_value",
    "split_growth_violations_by_severity",
    "validate_debt_scorecard",
    "validate_exemption_key_normalization",
    "validate_exemption_target_references",
    "validate_exemptions_registry",
    "validate_scorecard_registry_sync",
    "write_architecture_quality_scorecard",
]
