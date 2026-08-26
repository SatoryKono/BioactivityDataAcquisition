"""YAML-to-domain config mapper contract."""

from __future__ import annotations

from bioetl.domain.ports.config.config_loader_port import DomainConfigMapperPort

DomainConfigMapper = DomainConfigMapperPort

__all__ = ["DomainConfigMapper"]
