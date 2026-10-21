"""Fixtures for durability construction smoke."""

from __future__ import annotations

import pytest

from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.time.system_clock import SystemClock
from bioetl.infrastructure.validation import ContractAwareSilverValidator
from tests.integration.infrastructure.durability.builders import DurabilityCollaborators


@pytest.fixture
def test_logger() -> NoOpLogger:
    return NoOpLogger()


@pytest.fixture
def noop_metrics() -> NoOpMetrics:
    return NoOpMetrics()


@pytest.fixture
def system_clock() -> SystemClock:
    return SystemClock()


@pytest.fixture
def silver_validator() -> ContractAwareSilverValidator:
    return ContractAwareSilverValidator(schema=None)


@pytest.fixture
def durability_collaborators(
    test_logger: NoOpLogger,
    noop_metrics: NoOpMetrics,
    system_clock: SystemClock,
    silver_validator: ContractAwareSilverValidator,
) -> DurabilityCollaborators:
    return DurabilityCollaborators(
        logger=test_logger,
        metrics=noop_metrics,
        clock=system_clock,
        silver_validator=silver_validator,
    )
