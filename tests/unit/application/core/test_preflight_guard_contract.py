"""Malformed optional capabilities fail before any runtime work is attempted."""

import pytest

from bioetl.application.core._quarantine_manager_support import (
    QuarantineManagerSupportMixin,
)
from bioetl.application.core.preflight.health_aggregator_runtime import (
    _supports_raise_on_unhealthy,
)

pytestmark = pytest.mark.unit


def test_opaque_callable_does_not_advertise_unhealthy_keyword_support():
    class OpaqueProbe:
        __signature__ = "unavailable plugin signature"

        def __call__(self):
            return None

    assert _supports_raise_on_unhealthy(OpaqueProbe()) is False


@pytest.mark.parametrize("stage", ["bronze", "invalid", ""])
def test_quarantine_rejects_unknown_stage_before_resolving_runtime_ports(stage):
    with pytest.raises(ValueError, match="Unsupported quarantine stage"):
        QuarantineManagerSupportMixin()._quarantine_runtime_ports(stage)


def test_gold_rejects_generic_write_mode_with_configuration_diagnostic():
    from bioetl.application.core.preflight.medallion_validator_runtime import validate_single_write_mode
    from bioetl.domain.medallion import Layer, WriteModePolicy

    errors = validate_single_write_mode(write_mode_policy=WriteModePolicy(), layer=Layer.GOLD, mode_value="append", field="gold.write_mode", rule="medallion")
    assert len(errors) == 1
    assert errors[0].field == "gold.write_mode"
    assert errors[0].expected == "supported layer for generic modes"
