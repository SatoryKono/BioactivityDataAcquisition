"""Public serialization facade for ``CompositeConfig``."""

from __future__ import annotations

from .config_composite_decoder import composite_from_dict
from .config_composite_encoder import composite_to_dict

__all__ = ["composite_from_dict", "composite_to_dict"]
