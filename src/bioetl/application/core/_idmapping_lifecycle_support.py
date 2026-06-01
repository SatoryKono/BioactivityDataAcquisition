"""Backward-compatible re-export for `bioetl.application.core.idmapping_lifecycle_support`."""

from __future__ import annotations

from bioetl.application.core import idmapping_lifecycle_support as _public

close_data_source = _public.close_data_source
enter_data_source = _public.enter_data_source
health_check = _public.health_check

__all__ = ['close_data_source', 'enter_data_source', 'health_check']
