"""ChEMBL data source adapter.

Implements DataSourcePort for ChEMBL database.
See RULES.md Appendix A for rate limits and retry strategy.
"""

from __future__ import annotations

from bioetl.infrastructure.adapters.chembl import models as _chembl_models
from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter
from bioetl.infrastructure.adapters.chembl.models import (
    _CHEMBL_FACADE_MODEL_EXPORTS,
)

for _export_name in _CHEMBL_FACADE_MODEL_EXPORTS:
    globals()[_export_name] = getattr(_chembl_models, _export_name)

del _export_name

__all__ = ["ChemblAdapter", *_CHEMBL_FACADE_MODEL_EXPORTS]
