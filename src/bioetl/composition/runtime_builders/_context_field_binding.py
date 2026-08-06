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
    """Return a new context with updates applied (copy-returning contract).

    Never mutates the input context in place. Dataclass hosts use
    ``dataclasses.replace``; other hosts with ``__dict__`` are shallow-copied
    via their constructor/type when possible.
    """
    if not updates:
        return context
    if is_dataclass(context) and not isinstance(context, type):
        # Validate keys against dataclass fields before replace.
        field_names = {
            field.name for field in context.__dataclass_fields__.values()
        }
        unknown = sorted(set(updates) - field_names)
        if unknown:
            raise TypeError(
                f"{unsupported_message}: unknown context fields: {', '.join(unknown)}"
            )
        return cast("ContextT", replace(cast("DataclassInstance", context), **updates))
    if hasattr(context, "__dict__") and not isinstance(context, type):
        # Shallow copy via type(context)(**payload) to avoid mutating the input.
        payload = {
            key: value
            for key, value in vars(context).items()
            if not key.startswith("_")
        }
        payload.update(updates)
        try:
            return type(context)(**payload)
        except TypeError:
            # Fallback: new instance + setattr for hosts that reject **kwargs.
            try:
                clone = object.__new__(type(context))
            except TypeError as exc:
                raise TypeError(unsupported_message) from exc
            for key, value in payload.items():
                try:
                    object.__setattr__(clone, key, value)
                except (AttributeError, TypeError) as exc:
                    raise TypeError(unsupported_message) from exc
            return clone
    raise TypeError(unsupported_message)
