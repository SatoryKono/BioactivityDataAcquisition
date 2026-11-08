"""Attach cached Bronze inputs to an existing runner context."""

from dataclasses import is_dataclass, replace

from bioetl.domain.context import CachedBronzeContext


def bind_cached_bronze_context[T](
    ctx: T,
    cached_bronze: CachedBronzeContext,
) -> T:
    """Attach cached Bronze inputs while preserving the concrete context type."""
    current = getattr(ctx, "cached_bronze", None)
    if current == cached_bronze:
        return ctx
    if is_dataclass(ctx):
        if isinstance(ctx, type):
            raise TypeError("cached_bronze binding requires a dataclass instance")
        return replace(ctx, cached_bronze=cached_bronze)
    try:
        object.__setattr__(ctx, "cached_bronze", cached_bronze)
        return ctx
    except (AttributeError, TypeError):
        pass
    try:
        setattr(ctx, "cached_bronze", cached_bronze)  # noqa: B010 - generic dynamic host
        return ctx
    except (AttributeError, TypeError) as exc:
        raise TypeError(
            "PipelineRunContext does not support cached_bronze binding; "
            "use a dataclass or mutable context host"
        ) from exc
