"""W153 contract: the join receives computed rows, not a function.

The BioETL pipeline join was not executed. Integration stays NOT_RUN.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

INTEGRATION_STATUS = "NOT_RUN"
INTEGRATION_REASON = (
    "интеграционный join контура BioETL не выполнялся; "
    "приёмка интеграции не засчитывается"
)


def join_w153(
    table: Sequence[Mapping[str, str]],
) -> tuple[Mapping[str, str], ...]:
    """Return the computed table. A callable is rejected."""
    if callable(table):
        message = "W153 join requires computed rows, not a function"
        raise TypeError(message)
    return tuple(table)
