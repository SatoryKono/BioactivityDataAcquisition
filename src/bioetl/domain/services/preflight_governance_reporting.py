"""Report-building helpers for preflight governance outputs."""

from __future__ import annotations

from bioetl.domain.types import JsonDict
from bioetl.domain.types.validation_result import CompositeValidationReport


def build_validation_summary(report: CompositeValidationReport) -> JsonDict:
    """Build the validation summary section for governance reports."""
    runtime_guard_result = report.runtime_guard_result
    return {
        "total_issues": len(report.get_all_issues()),
        "total_blockers": len(report.get_all_blockers()),
        "total_warnings": len(report.get_all_warnings()),
        "total_infos": len(report.get_all_infos()),
        "layers": {
            "structural": {
                "issues": len(report.structural_result.issues),
                "blockers": len(report.structural_result.get_blockers()),
            },
            "deep_preflight": {
                "issues": len(report.deep_preflight_result.issues),
                "blockers": len(report.deep_preflight_result.get_blockers()),
            },
            "runtime_guard": {
                "issues": len(runtime_guard_result.issues)
                if runtime_guard_result
                else 0,
                "blockers": (
                    len(runtime_guard_result.get_blockers())
                    if runtime_guard_result
                    else 0
                ),
            },
        },
    }


__all__ = ["build_validation_summary"]
