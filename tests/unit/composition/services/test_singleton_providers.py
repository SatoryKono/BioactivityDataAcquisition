from __future__ import annotations

import pytest

from bioetl.composition import _services


@pytest.mark.unit
def test_metrics_service_provider_returns_correct_type_and_does_not_reuse_instance() -> None:
    first_instance = _services.get_metrics_service()
    second_instance = _services.get_metrics_service()

    # The service instances are bound via the dependency injector per request
    # and are not inherently cached as singletons within the module itself, hence
    # the second instance is a distinct object
    assert first_instance.__class__.__name__ == "MetricsService"
    assert first_instance is not second_instance


@pytest.mark.unit
def test_checkpoint_service_provider_returns_correct_type_and_does_not_reuse_instance() -> None:
    first_instance = _services.get_checkpoint_service()
    second_instance = _services.get_checkpoint_service()

    assert first_instance.__class__.__name__ == "CheckpointService"
    assert first_instance is not second_instance


@pytest.mark.unit
def test_audit_service_provider_returns_correct_type_and_does_not_reuse_instance() -> None:
    first_instance = _services.get_audit_service()
    second_instance = _services.get_audit_service()

    assert first_instance.__class__.__name__ == "AuditInspectionService"
    assert first_instance is not second_instance
