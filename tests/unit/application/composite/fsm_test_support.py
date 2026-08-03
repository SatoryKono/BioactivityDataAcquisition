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
"""Shared pytest fixtures for CompositePipelineRunner FSM suites."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.composite.runner_pkg import (
    CompositePipelineRunner,
    CompositeRuntimeConfig,
)
from tests.unit.application.composite import runner_test_support as support

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_logger() -> MagicMock:
    return support.create_mock_logger()


@pytest.fixture
def mock_lock() -> AsyncMock:
    return support.create_mock_lock(release_value=False)


@pytest.fixture
def mock_key_extractor() -> AsyncMock:
    return support.create_crossref_key_extractor()


@pytest.fixture
def mock_coordinator() -> AsyncMock:
    return support.create_successful_crossref_coordinator()


@pytest.fixture
def mock_merger() -> AsyncMock:
    return support.create_successful_crossref_merger()


@pytest.fixture
def mock_checkpoint_manager() -> AsyncMock:
    return support.create_tracking_checkpoint_manager()


@pytest.fixture
def mock_seed_runner_factory() -> object:
    return support.create_magic_seed_runner_factory()


@pytest.fixture
def mock_enricher_runner_factory() -> object:
    return support.create_magic_enricher_runner_factory()


@pytest.fixture
def sample_composite_config() -> MagicMock:
    return support.create_required_crossref_composite_config()


@pytest.fixture
def runner(
    sample_composite_config,
    mock_seed_runner_factory,
    mock_enricher_runner_factory,
    mock_key_extractor,
    mock_coordinator,
    mock_merger,
    mock_checkpoint_manager,
    mock_logger,
    mock_lock,
) -> CompositePipelineRunner:
    return support.create_runner(
        config=sample_composite_config,
        runtime=CompositeRuntimeConfig(resume=False, dry_run=False),
        logger=mock_logger,
        checkpoint_manager=mock_checkpoint_manager,
        seed_runner_factory=mock_seed_runner_factory,
        enricher_runner_factory=mock_enricher_runner_factory,
        key_extractor=mock_key_extractor,
        coordinator=mock_coordinator,
        merger=mock_merger,
        lock=mock_lock,
        run_id="00000000-0000-0000-0000-000000000123",
    )


def find_fsm_transition_calls(logger: MagicMock) -> list[object]:
    return [
        call
        for call in logger.info.call_args_list
        if call.args and "FSM state transition" in str(call.args[0])
    ]
