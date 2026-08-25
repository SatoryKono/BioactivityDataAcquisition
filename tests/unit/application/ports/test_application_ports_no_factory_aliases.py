"""Guard ADR-058 application ports against *Factory / *Like alias regression (#9641)."""

from __future__ import annotations

import pytest

from bioetl.application import ports as application_ports
from bioetl.application.ports import dq, metrics, pipeline, storage

pytestmark = pytest.mark.unit

_FORBIDDEN_ALIASES = (
    (dq, "DQReportServiceFactory"),
    (metrics, "WorkflowMetricsFactory"),
    (metrics, "MetricsFactory"),
    (pipeline, "ContractPolicyLoader"),
    (storage, "StorageContextLike"),
    (storage, "CompositeMergeStorage"),
)


@pytest.mark.parametrize(("module", "alias"), _FORBIDDEN_ALIASES)
def test_application_port_modules_do_not_export_pre_protocol_aliases(
    module: object,
    alias: str,
) -> None:
    assert alias not in vars(module)
    assert alias not in getattr(application_ports, "__all__", ())
