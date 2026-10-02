# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for the composition-assembled shared run-report store.

ARCH-008 (#11859): `create_run_report_store()` must assemble once and share
the instance by reference instead of constructing a new adapter per request.
"""

from __future__ import annotations

import pytest

from bioetl.composition import observability_runtime
from bioetl.composition.observability_runtime import create_run_report_store

pytestmark = pytest.mark.unit


def test_create_run_report_store_assembles_once() -> None:
    first = create_run_report_store()
    second = create_run_report_store()

    assert first is second


def test_shared_run_report_store_exposes_port_surface() -> None:
    store = create_run_report_store()

    for method in (
        "mkdir",
        "write_text",
        "read_text",
        "read_identity_text",
        "is_file",
        "is_dir",
        "iterdir",
        "mtime",
        "remove_tree",
    ):
        assert callable(getattr(store, method)), f"missing port method: {method}"


def test_shared_store_singleton_survives_module_reload_reference() -> None:
    assert observability_runtime._shared_run_report_store is create_run_report_store()
