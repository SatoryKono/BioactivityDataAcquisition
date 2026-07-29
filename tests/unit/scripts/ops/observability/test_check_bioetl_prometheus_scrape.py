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
"""Unit tests for BioETL Prometheus scrape smoke check."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from scripts.ops.observability import check_bioetl_prometheus_scrape as mod

pytestmark = pytest.mark.unit


def test_main_ok_when_bioetl_target_up() -> None:
    payload = {
        "status": "success",
        "data": {
            "activeTargets": [
                {
                    "labels": {"job": "bioetl"},
                    "health": "up",
                    "scrapeUrl": "http://bioetl:8000/metrics",
                    "lastError": "",
                }
            ]
        },
    }

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(payload).encode()

    with patch.object(mod.urllib.request, "urlopen", return_value=_Resp()):
        assert mod.main(["--json"]) == mod.EXIT_OK


def test_main_errors_when_target_down() -> None:
    payload = {
        "status": "success",
        "data": {
            "activeTargets": [
                {
                    "labels": {"job": "bioetl"},
                    "health": "down",
                    "scrapeUrl": "http://bioetl:8000/metrics",
                    "lastError": "connection refused",
                }
            ]
        },
    }

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(payload).encode()

    with patch.object(mod.urllib.request, "urlopen", return_value=_Resp()):
        assert mod.main(["--json"]) == mod.EXIT_TARGET_DOWN
