"""Program done-criteria policy helpers for debt scorecard decomposition checks."""

from __future__ import annotations

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.quality._primitives import (
    _parse_quarter_label,
    _validate_non_negative_int,
)


def _validate_program_done_criteria_section(
    raw: JsonDict,  # Any: YAML values are heterogeneous
    errors: list[str],
) -> None:
    """Validate long-horizon program done criteria section."""
    section = raw.get("program_done_criteria")
    if not isinstance(section, dict):
        errors.append("program_done_criteria: required mapping")
        return

    _validate_non_negative_int(
        section.get("max_total_exemptions"),
        field_name="program_done_criteria.max_total_exemptions",
        errors=errors,
    )

    min_score = section.get("min_integral_score")
    if not isinstance(min_score, (int, float)):
        errors.append("program_done_criteria.min_integral_score: expected number")
    elif not (0 <= float(min_score) <= 100):
        errors.append(
            "program_done_criteria.min_integral_score: must be between 0 and 100"
        )

    _validate_non_negative_int(
        section.get("max_expired_entries"),
        field_name="program_done_criteria.max_expired_entries",
        errors=errors,
    )

    deadline_quarter = section.get("deadline_quarter")
    if (
        not isinstance(deadline_quarter, str)
        or _parse_quarter_label(deadline_quarter) is None
    ):
        errors.append(
            "program_done_criteria.deadline_quarter: expected 'YYYY-QN' format"
        )


__all__ = ["_validate_program_done_criteria_section"]
