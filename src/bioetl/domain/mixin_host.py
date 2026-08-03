"""Mixin host typing helper (TYPE-002 justified Any boundary)."""

from __future__ import annotations

from typing import Any, cast

__all__ = ["as_mixin_host"]


def as_mixin_host(obj: object) -> Any:  # Any: mixin host
    """Widen a mixin ``self`` for host attribute access without per-callsite Any.

    Call sites use ``as_mixin_host(self).attr`` instead of ``cast(Any, self).attr``
    so TYPE-002 justification stays centralized here.
    """
    return cast(Any, obj)  # Any: mixin host
