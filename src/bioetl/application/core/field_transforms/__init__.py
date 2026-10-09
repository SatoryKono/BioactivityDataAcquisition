"""Canonical grouping for transform primitives and field-spec helpers."""

from __future__ import annotations

from bioetl.application.core import dict_transformers as _dict_transformers
from bioetl.application.core import entity_id as _entity_id
from bioetl.application.core import field_specs as _field_specs
from bioetl.application.core.wiring.lazy_export_hooks import (
    install_lazy_export_facade,
)

_FIELD_TRANSFORM_EXPORTS = {
    **{
        name: (_dict_transformers.__name__, name) for name in _dict_transformers.__all__
    },
    **{name: (_entity_id.__name__, name) for name in _entity_id.__all__},
    **{name: (_field_specs.__name__, name) for name in _field_specs.__all__},
}
install_lazy_export_facade(globals(), __name__, _FIELD_TRANSFORM_EXPORTS)
