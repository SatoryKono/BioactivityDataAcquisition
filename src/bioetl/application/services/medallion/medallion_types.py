"""Value objects for Medallion lifecycle operations.

Extracted from medallion_lifecycle.py to reduce file size and coupling.
"""

from __future__ import annotations

__all__ = ["ClearResult", "PrepareResult", "VacuumResult"]


from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.medallion import MedallionPolicy


@dataclass(frozen=True, slots=True)
class ClearResult:
    """Result of clear operation.

    Attributes:
        silver_cleared: Number of Silver records cleared.
        gold_cleared: Number of Gold records cleared.
        dry_run: Whether this was a dry run (no actual deletion).
    """

    silver_cleared: int
    gold_cleared: int
    dry_run: bool

    @property
    def total_cleared(self) -> int:
        """Get total records cleared.

        Returns:
            Sum of silver and gold cleared records.
        """
        return self.silver_cleared + self.gold_cleared


@dataclass(frozen=True, slots=True)
class VacuumResult:
    """Result of VACUUM operation.

    Attributes:
        silver_files_removed: Number of files removed from Silver table.
        gold_files_removed: Number of files removed from Gold table.
        skipped: Whether VACUUM was skipped.
    """

    silver_files_removed: int
    gold_files_removed: int
    skipped: bool


@dataclass(frozen=True, slots=True)
class PrepareResult:
    """Result of prepare_for_run operation.

    Combines clear result with policy used for transparency.

    Attributes:
        clear_result: Result of clear operation.
        policy: MedallionPolicy used for the operation.
    """

    clear_result: ClearResult
    policy: MedallionPolicy
