# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
from __future__ import annotations

import os
from pathlib import Path

import pytest

from bioetl.composition.registry_api import create_registry, get_default_registry
from bioetl.composition.factories.pipeline.registry import (
    create_pipeline_registration_state,
    is_registered,
    register_all_pipelines,
    reset_registration,
)
from bioetl.composition.factories.pipeline.registry_core import (
    create_registry as create_core_registry,
)


pytestmark = pytest.mark.unit


@pytest.fixture(scope="session")
def session_registered_pipeline_names() -> frozenset[str]:
    """Register pipelines once per session for completeness/list hotspots (#8329)."""
    registry = get_default_registry()
    register_all_pipelines(registry=registry)
    return frozenset(registry.list_pipelines())


class _DummyPipelineFactory:
    silver_schema = None
    pandera_silver_schema = None

    def __init__(self, pipeline_name: str, *, gold_schema: object | None) -> None:
        self.pipeline_name = pipeline_name
        self.gold_schema = gold_schema

    def create_with_services(self, request: object) -> object:
        raise NotImplementedError

    def create_runner(self, request: object) -> object:
        raise NotImplementedError


@pytest.fixture(autouse=True)
def ensure_registration():
    """Ensure pipeline factories are registered before tests."""
    register_all_pipelines(registry=get_default_registry())


def _pipeline_config_name(path: Path, *, config_dir: Path) -> str | None:
    relative_path = path.relative_to(config_dir)
    parts = relative_path.parts
    if len(parts) < 2:
        return None
    provider = parts[0]
    if provider.startswith("_"):
        return None
    if provider == "composite":
        # Composite pipelines are bootstrapped from configs/composites/*.yaml
        # rather than the registry-backed configs/entities/{provider}/{entity}.yaml
        # convention that this test verifies.
        return None
    entity = os.path.splitext(parts[1])[0]
    return f"{provider}_{entity}"


def _iter_pipeline_config_names(config_dir: Path) -> list[str]:
    found_configs: list[str] = []
    for root, _, files in os.walk(config_dir):
        for file in files:
            if not (file.endswith(".yaml") or file.endswith(".yml")):
                continue
            pipeline_name = _pipeline_config_name(
                Path(root) / file, config_dir=config_dir
            )
            if pipeline_name is not None:
                found_configs.append(pipeline_name)
    return found_configs


def test_registry_completeness(session_registered_pipeline_names: frozenset[str]):
    """
    Verify that every unified entity pipeline configuration file in configs/entities
    has a corresponding entry in the PipelineRegistry.
    """
    config_dir = Path("configs/entities")
    if not config_dir.exists():
        pytest.skip("Config directory not found")

    # Pipelines that have configs but are not yet fully integrated
    # These are new providers in development that will be registered later
    pipelines_in_development: set[str] = set()  # All pipelines are now fully integrated

    found_configs = _iter_pipeline_config_names(config_dir)

    # Session-scoped registration amortizes factory import cost (#8329).
    registered_pipelines = session_registered_pipeline_names

    # Check for missing handlers (excluding pipelines in development)
    missing_handlers = [
        name
        for name in found_configs
        if name not in registered_pipelines and name not in pipelines_in_development
    ]

    assert not missing_handlers, (
        f"The following pipelines have configs but no registered factory: {missing_handlers}"
    )


def test_registry_contains_expected_pipelines(
    session_registered_pipeline_names: frozenset[str],
):
    """Sanity check that key pipelines are present."""
    expected = [
        "chembl_activity",
        "pubchem_compound",
        "uniprot_protein",
        "pubmed_publication",
    ]
    registered = session_registered_pipeline_names

    for pipe in expected:
        assert pipe in registered, f"Expected pipeline {pipe} not found in registry"


def test_register_all_pipelines_is_idempotent():
    """Test that calling register_all_pipelines multiple times is safe."""
    registry = get_default_registry()

    # First call already made in fixture
    assert is_registered()

    # Get current count
    initial_count = len(registry.list_pipelines())

    # Call again - should be no-op
    register_all_pipelines(registry=registry)

    # Count should remain the same
    assert len(registry.list_pipelines()) == initial_count


def test_registry_empty_raises_runtime_error(isolated_registry):
    """Test that accessing empty registry raises RuntimeError."""
    # Use the isolated_registry fixture which is empty
    with pytest.raises(RuntimeError, match="PipelineRegistry is empty"):
        isolated_registry.get("any_pipeline")


def test_isolated_registry_is_independent(isolated_registry):
    """Test that isolated registries are independent of each other."""
    registry1 = isolated_registry
    registry2 = create_registry()

    # Both should be empty initially
    assert len(registry1.list_pipelines()) == 0
    assert len(registry2.list_pipelines()) == 0

    # Register to one
    register_all_pipelines(registry=registry1)

    # First registry should be populated
    assert len(registry1.list_pipelines()) > 0

    # Second registry should still be empty
    assert len(registry2.list_pipelines()) == 0


def test_multiple_registries_in_same_process():
    """Test that we can create 2 registries in one process."""
    registry1 = create_registry()
    registry2 = create_registry()

    register_all_pipelines(registry=registry1)
    register_all_pipelines(registry=registry2)

    # Both should have the same pipelines
    assert registry1.list_pipelines() == registry2.list_pipelines()

    # But they should be different instances
    assert registry1 is not registry2
    assert registry1._registry is not registry2._registry


def test_reset_registration_clears_default_registry_state():
    """reset_registration should clear the default registry and registration flag."""
    try:
        registry = get_default_registry()
        register_all_pipelines(registry=registry)
        assert is_registered()
        assert len(registry.list_pipelines()) > 0

        reset_registration(registry=registry)

        assert not is_registered()
        assert registry.list_pipelines() == []
    finally:
        register_all_pipelines(registry=get_default_registry())


def test_explicit_registration_state_tracks_registration_independently():
    """Explicit registration state should avoid coupling tests to module globals."""
    registration_state = create_pipeline_registration_state()
    registry = create_registry()

    assert not is_registered(registration_state=registration_state)

    register_all_pipelines(
        registry=registry,
        registration_state=registration_state,
    )

    assert is_registered(registration_state=registration_state)


def test_register_all_pipelines_rejects_missing_explicit_registry() -> None:
    with pytest.raises(ValueError, match="explicit registry"):
        register_all_pipelines()


def test_reset_registration_rejects_missing_explicit_registry() -> None:
    with pytest.raises(ValueError, match="explicit registry"):
        reset_registration()


def test_core_registry_contract_edges_are_explicit():
    """Core registry should expose deterministic validation and lookup behavior."""
    registry = create_core_registry()
    factory = _DummyPipelineFactory("demo", gold_schema=object())

    assert registry.contains("demo") is False
    registry.register("demo", factory)

    assert registry.contains("demo") is True
    assert registry.list_keys() == ["demo"]
    assert registry.get("demo").factory is factory

    with pytest.raises(ValueError, match="Unknown pipeline name"):
        registry.get("missing")
    with pytest.raises(ValueError, match="Pipeline already registered"):
        registry.register("demo", factory)
    with pytest.raises(ValueError, match="does not match"):
        registry.register("other", factory)
    with pytest.raises(ValueError, match="must have gold_schema"):
        registry.register(
            "missing_gold",
            _DummyPipelineFactory("missing_gold", gold_schema=None),
        )
