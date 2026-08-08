"""Public serialization facade for ``CompositeConfig``."""

from __future__ import annotations

from bioetl.domain.composite.config_composite_decoder import composite_from_dict
from bioetl.domain.composite.config_composite_encoder import composite_to_dict

__all__ = ["composite_from_dict", "composite_to_dict"]
