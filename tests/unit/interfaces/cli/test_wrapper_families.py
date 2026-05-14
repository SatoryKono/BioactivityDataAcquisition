"""Shared boundary-test families for thin CLI package wrappers.

New package-level convenience seams should land here by default instead of
spawning dedicated one-off suites.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from bioetl.interfaces.cli.registry_helpers import build_cli_registry


def _no_args(_module: ModuleType) -> tuple[tuple[object, ...], dict[str, object]]:
    """Build an empty invocation for zero-argument wrappers."""
    return (), {}


def _pipeline_runner_args(
    _module: ModuleType,
) -> tuple[tuple[object, ...], dict[str, object]]:
    """Build representative args for create_pipeline_runner."""
    return ("chembl_activity", MagicMock()), {}


def _registry_kwarg(
    _module: ModuleType,
) -> tuple[tuple[object, ...], dict[str, object]]:
    """Build a representative registry kwarg for registration wrappers."""
    return (), {"registry": MagicMock()}


PACKAGE_WRAPPER_CASES: tuple[
    tuple[
        str,
        str,
        str,
        Callable[[ModuleType], tuple[tuple[object, ...], dict[str, object]]],
        object,
        object,
    ],
    ...,
] = (
    (
        "bioetl.interfaces.cli",
        "create_pipeline_runner",
        "bioetl.composition.execution_api.create_pipeline_runner",
        _pipeline_runner_args,
        object(),
        "identity",
    ),
    (
        "bioetl.interfaces.cli.registry_helpers",
        "create_registry",
        "bioetl.composition.registry_api.create_registry",
        _no_args,
        object(),
        "identity",
    ),
    (
        "bioetl.interfaces.cli.registry_helpers",
        "register_all_pipelines",
        "bioetl.composition.registry_api.register_all_pipelines",
        _registry_kwarg,
        None,
        None,
    ),
)


@pytest.mark.unit
@pytest.mark.parametrize(
    (
        "module_name",
        "wrapper_name",
        "patch_target",
        "call_factory",
        "patched_return_value",
        "expected_result",
    ),
    PACKAGE_WRAPPER_CASES,
    ids=("cli-create-runner", "registry-create", "registry-register"),
)
def test_cli_package_wrappers_delegate_to_public_composition_facades(
    module_name: str,
    wrapper_name: str,
    patch_target: str,
    call_factory: Callable[[ModuleType], tuple[tuple[object, ...], dict[str, object]]],
    patched_return_value: object,
    expected_result: object,
) -> None:
    """Thin package wrappers should remain lazy delegates to public facades."""
    module = importlib.import_module(module_name)
    args, kwargs = call_factory(module)

    with patch(patch_target, return_value=patched_return_value) as mock_impl:
        result = getattr(module, wrapper_name)(*args, **kwargs)

    if expected_result == "identity":
        assert result is patched_return_value
    else:
        assert result is expected_result
    mock_impl.assert_called_once_with(*args, **kwargs)


@pytest.mark.unit
def test_build_cli_registry_uses_local_patch_points() -> None:
    """Registry builder should keep using module-level collaborator seams."""
    registry = MagicMock()

    with (
        patch(
            "bioetl.interfaces.cli.registry_helpers.create_registry",
            return_value=registry,
        ) as mock_create_registry,
        patch(
            "bioetl.interfaces.cli.registry_helpers.register_all_pipelines",
        ) as mock_register_all_pipelines,
    ):
        result = build_cli_registry()

    assert result is registry
    mock_create_registry.assert_called_once_with()
    mock_register_all_pipelines.assert_called_once_with(registry=registry)
