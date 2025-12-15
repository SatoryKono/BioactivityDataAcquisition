"""ChEMBL data source adapter.

Implements DataSourcePort for ChEMBL database.
See RULES.md Appendix A for rate limits and retry strategy.
"""

from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter

__all__ = ["ChemblAdapter"]