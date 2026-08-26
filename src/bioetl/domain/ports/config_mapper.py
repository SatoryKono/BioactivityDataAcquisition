"""YAML-to-domain config mapper contract.

``DomainConfigMapper`` is a compatibility alias of the canonical
``DomainConfigMapperPort`` Protocol (one mapper ``*Port`` surface). The target
is decorated with ``@runtime_checkable`` in its canonical module.
"""

from __future__ import annotations

from bioetl.domain.ports.config.config_loader_port import DomainConfigMapperPort

DomainConfigMapper = DomainConfigMapperPort

__all__ = ["DomainConfigMapper"]
