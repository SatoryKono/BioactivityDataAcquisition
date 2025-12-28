"""GtoPdb (Guide to Pharmacology) adapter package.

Provides data source adapter for the GtoPdb REST API.
See: https://www.guidetopharmacology.org/webServices.jsp
"""

from bioetl.infrastructure.adapters.gtopdb.client import GtopdbAdapter

__all__ = ["GtopdbAdapter"]
