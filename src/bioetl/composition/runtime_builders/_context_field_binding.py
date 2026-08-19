"""Shared context field binding for runtime assembly."""

from __future__ import annotations

from dataclasses import fields, is_dataclass, replace
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
        return _replace_dataclass_context(
            context,
            updates=updates,
            unsupported_message=unsupported_message,
        )
    if hasattr(context, "__dict__") and not isinstance(context, type):
        return _copy_object_context(
            context,
            updates=updates,
            unsupported_message=unsupported_message,
        )
    raise TypeError(unsupported_message)


def _replace_dataclass_context[ContextT](
    context: ContextT,
    *,
    updates: dict[str, object],
    unsupported_message: str,
) -> ContextT:
    """Validate dataclass fields and return a replaced context."""
    dataclass_context = cast("DataclassInstance", context)
    field_names = {field.name for field in fields(dataclass_context)}
    unknown = sorted(set(updates) - field_names)
    if unknown:
        raise TypeError(
            f"{unsupported_message}: unknown context fields: {', '.join(unknown)}"
        )
    return cast("ContextT", replace(dataclass_context, **updates))


def _copy_object_context[ContextT](
    context: ContextT,
    *,
    updates: dict[str, object],
    unsupported_message: str,
) -> ContextT:
    """Shallow-copy a non-dataclass context without mutating its input."""
    payload = {
        key: value for key, value in vars(context).items() if not key.startswith("_")
    }
    payload.update(updates)
    try:
        return type(context)(**payload)
    except TypeError:
        return _copy_object_context_without_constructor(
            context,
            payload=payload,
            unsupported_message=unsupported_message,
        )


def _copy_object_context_without_constructor[ContextT](
    context: ContextT,
    *,
    payload: dict[str, object],
    unsupported_message: str,
) -> ContextT:
    """Clone one context whose constructor rejects keyword payloads."""
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
