"""Owner-test reachability for ADR-058 lazy domain port owner modules (#9641).

These submodules are loaded through ``bioetl.domain.ports`` string keys.
Direct imports keep them out of the untriaged zero-import set without
raising the classified zero-import budget.
"""

from __future__ import annotations

from typing import Protocol

import pytest

from bioetl.domain.ports import config_mapper as config_mapper_mod
from bioetl.domain.ports import entity_type as entity_type_mod
from bioetl.domain.ports import pipeline_callbacks as pipeline_callbacks_mod
from bioetl.domain.ports import source_config as source_config_mod
from bioetl.domain.ports.config_mapper import DomainConfigMapper
from bioetl.domain.ports.entity_type import EntityTypeExtractor
from bioetl.domain.ports.pipeline_callbacks import (
    GoldFilterCallback,
    GoldTransformCallback,
    TransformCallback,
)
from bioetl.domain.ports.source_config import PaginationConfigLike, SourceConfigLike

pytestmark = pytest.mark.unit

_OWNER_MODULES = (
    config_mapper_mod,
    entity_type_mod,
    pipeline_callbacks_mod,
    source_config_mod,
)
_OWNER_PROTOCOLS = (
    DomainConfigMapper,
    EntityTypeExtractor,
    GoldFilterCallback,
    GoldTransformCallback,
    PaginationConfigLike,
    SourceConfigLike,
    TransformCallback,
)


@pytest.mark.parametrize("module", _OWNER_MODULES)
def test_adr_058_owner_modules_are_importable(module: object) -> None:
    assert getattr(module, "__name__", "").startswith("bioetl.domain.ports.")


@pytest.mark.parametrize("protocol", _OWNER_PROTOCOLS)
def test_adr_058_owner_protocols_are_runtime_checkable(protocol: type[object]) -> None:
    assert issubclass(protocol, Protocol)
    assert getattr(protocol, "_is_runtime_protocol", False) is True
    isinstance(object(), protocol)
