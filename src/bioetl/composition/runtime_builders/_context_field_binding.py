"""Shared context field binding for runtime assembly."""

from __future__ import annotations

from dataclasses import is_dataclass, replace
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

def bind_context_fields[ContextT](
    context: ContextT,
    *,
    updates: dict[str, object],
    unsupported_message: str,
) -> ContextT:
    """Return a dataclass copy or update a mutable context in place."""
    if is_dataclass(context) and not isinstance(context, type):
        return cast(
            "ContextT",
            replace(cast("DataclassInstance", context), **updates),
        )
    if hasattr(context, "__dict__"):
        for field_name, value in updates.items():
            setattr(context, field_name, value)
        return context
    raise TypeError(unsupported_message)
