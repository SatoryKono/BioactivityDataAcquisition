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
from __future__ import annotations

import importlib

import pytest

from scripts.memory import __main__ as scripts_memory_main


pytestmark = pytest.mark.unit


def test_scripts_memory_package_exports_canonical_graph_modules() -> None:
    compatibility = importlib.import_module("scripts.memory")

    assert compatibility.sync is importlib.import_module("memory.graph.sync")
    assert compatibility.query is importlib.import_module("memory.graph.query")


def test_scripts_memory_router_delegates_to_canonical_graph_modules() -> None:
    assert scripts_memory_main.COMMANDS == {
        "query": "memory.graph.query",
        "sync": "memory.graph.sync",
    }


def test_scripts_ops_neo4j_memory_sync_is_canonical_module_alias() -> None:
    legacy = importlib.import_module("scripts.ops.neo4j_memory_sync")
    canonical = importlib.import_module("memory.graph.sync")
    assert legacy is canonical
