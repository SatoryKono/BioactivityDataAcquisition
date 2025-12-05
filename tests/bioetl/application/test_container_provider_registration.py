from __future__ import annotations

import sys
import types

from bioetl.domain.provider_registry import (
    get_provider,
    list_providers,
    reset_provider_registry,
    restore_provider_registry,
)
from bioetl.domain.providers import ProviderId


def _stub_tqdm_module() -> types.ModuleType:
    module = types.ModuleType("tqdm")
    module.tqdm = lambda *args, **kwargs: None
    return module


def test_register_providers_registers_chembl() -> None:
    snapshot = list_providers()
    try:
        reset_provider_registry()
        sys.modules.setdefault("tqdm", _stub_tqdm_module())

        from bioetl.application.container import PipelineContainer

        container = object.__new__(PipelineContainer)

        container._register_providers()

        provider = get_provider(ProviderId.CHEMBL)
        assert provider.id == ProviderId.CHEMBL
        assert ProviderId.CHEMBL in {definition.id for definition in list_providers()}
    finally:
        restore_provider_registry(snapshot)
        sys.modules.pop("tqdm", None)
