"""YAML-to-domain config mapper contract.

``DomainConfigMapper`` is a compatibility alias of the canonical
``DomainConfigMapperPort`` (one mapper ``*Port`` surface).
"""

from __future__ import annotations

from bioetl.domain.ports.config.config_loader_port import DomainConfigMapperPort

DomainConfigMapper = DomainConfigMapperPort

__all__ = ["DomainConfigMapper"]
