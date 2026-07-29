"""Shared typing helpers for justified Any boundaries (TYPE-002)."""

from __future__ import annotations

from typing import Any, cast

__all__ = ["as_mixin_host"]


def as_mixin_host(obj: object) -> Any:  # Any: mixin host surface (concrete self attrs/methods)
    """Widen a mixin ``self`` to access host attributes without per-callsite Any.

    Mixins intentionally leave host fields on the concrete class. Call sites should
    use ``as_mixin_host(self).attr`` instead of ``cast(Any, self).attr`` so TYPE-002
    justification stays centralized on this helper.
    """
    return cast(Any, obj)  # Any: mixin host surface (concrete self attrs/methods)
