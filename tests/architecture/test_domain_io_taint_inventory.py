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
"""Architecture gates for semantic Domain I/O taint inventory."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.engineering.qa.report_domain_io_taint_inventory import (
    build_payload,
    scan_domain_source,
)

ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "reports" / "quality" / "domain-io-taint-inventory.json"

pytestmark = pytest.mark.architecture


@pytest.mark.generated_artifact
def test_domain_io_taint_inventory_artifact_matches_generator() -> None:
    """Committed Domain I/O taint evidence must match the current source tree."""
    expected = build_payload(ROOT)
    actual = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))

    assert actual == expected


@pytest.mark.generated_artifact
def test_domain_io_taint_inventory_has_no_unreviewed_violations() -> None:
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))

    assert payload["violation_count"] == 0
    assert payload["violations"] == []


@pytest.mark.generated_artifact
def test_domain_io_taint_inventory_records_explicit_schema_boundary_exceptions() -> (
    None
):
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    exception_kinds = {
        exception["kind"] for exception in payload.get("allowed_exceptions", [])
    }

    assert {"import:pandera", "import:pandas"} <= exception_kinds


def test_domain_io_taint_inventory_forbids_import_graph_bypass() -> None:
    """#11788 (ARCH-002): domain must load modules through the import graph only."""
    payload = build_payload(ROOT)
    banned_kind_fragments = (
        "spec_from_file_location",
        "module_from_spec",
        "exec_module",
    )
    findings = [*payload["violations"], *payload["allowed_exceptions"]]
    offenders = [
        (finding["path"], finding["kind"])
        for finding in findings
        if finding["kind"] == "import:socket"
        or any(fragment in finding["kind"] for fragment in banned_kind_fragments)
    ]

    assert offenders == []


_SYNTHETIC_DOMAIN = "src/bioetl/domain/_synthetic.py"
_SYNTHETIC_SCHEMA = "src/bioetl/domain/schemas/_synthetic.py"


def _violation_kinds(
    source: str, *, relative_path: str = _SYNTHETIC_DOMAIN
) -> list[str]:
    violations, _allowed = scan_domain_source(source, relative_path=relative_path)
    return [finding.kind for finding in violations]


@pytest.mark.parametrize(
    ("source", "kind"),
    [
        (
            "from urllib.request import urlopen\n"
            "def load(url: str) -> object:\n"
            "    return urlopen(url)\n",
            "call:urllib.request.urlopen",
        ),
        (
            "import urllib.request\n"
            "def load(url: str) -> object:\n"
            "    return urllib.request.urlopen(url)\n",
            "call:urllib.request.urlopen",
        ),
        (
            "import urllib.request as ur\n"
            "def load(url: str) -> object:\n"
            "    return ur.urlopen(url)\n",
            "call:urllib.request.urlopen",
        ),
        (
            "from urllib.request import urlopen as fetch\n"
            "def load(url: str) -> object:\n"
            "    return fetch(url)\n",
            "call:urllib.request.urlopen",
        ),
    ],
    ids=[
        "direct-urlopen",
        "qualified-urlopen",
        "module-alias-urlopen",
        "name-alias-urlopen",
    ],
)
def test_domain_io_scanner_detects_urlopen_operations(source: str, kind: str) -> None:
    """#12463: direct, qualified, and aliased urlopen are I/O operations."""
    assert kind in _violation_kinds(source)


@pytest.mark.parametrize(
    ("source", "kind"),
    [
        (
            "from pathlib import Path\n"
            "def read(name: str) -> str:\n"
            "    return Path(name).read_text()\n",
            "attribute_call:read_text",
        ),
        (
            "from pathlib import Path\n"
            "def write(name: str) -> None:\n"
            "    Path(name).write_text('x')\n",
            "attribute_call:write_text",
        ),
        (
            "from pathlib import Path as P\n"
            "def open_it(name: str) -> object:\n"
            "    return P(name).open()\n",
            "attribute_call:open",
        ),
        (
            "from pathlib import Path\n"
            "def read(name: str) -> str:\n"
            "    path = Path(name)\n"
            "    return path.read_text()\n",
            "attribute_call:read_text",
        ),
        (
            "from pathlib import Path\n"
            "def read(name: str) -> str:\n"
            "    return (Path(name) / 'child').read_text()\n",
            "attribute_call:read_text",
        ),
        (
            "import os\ndef delete(name: str) -> None:\n    os.remove(name)\n",
            "call:os.remove",
        ),
        (
            "from os import remove as rm\n"
            "def delete(name: str) -> None:\n"
            "    rm(name)\n",
            "call:os.remove",
        ),
        (
            "def read(name: str) -> str:\n"
            "    with open(name, encoding='utf-8') as handle:\n"
            "        return handle.read()\n",
            "call:open",
        ),
    ],
    ids=[
        "path-read-text",
        "path-write-text",
        "path-open-alias",
        "path-assigned-read-text",
        "path-join-read-text",
        "os-remove",
        "os-remove-alias",
        "builtin-open",
    ],
)
def test_domain_io_scanner_keeps_path_and_os_operation_control(
    source: str,
    kind: str,
) -> None:
    kinds = _violation_kinds(source)
    assert kind in kinds
    assert "import:os" not in kinds
    assert "import:pathlib" not in kinds


@pytest.mark.parametrize(
    "source",
    [
        "from pathlib import PurePath\n"
        "def suffix(name: str) -> str:\n"
        "    return PurePath(name).suffix\n",
        "from pathlib import Path\n"
        "def join(name: str) -> Path:\n"
        "    return Path(name) / 'child'\n",
        "from urllib.parse import urlparse\n"
        "def host(url: str) -> str:\n"
        "    parsed = urlparse(url)\n"
        "    return parsed.hostname or ''\n",
        "import urllib.parse\n"
        "def host(url: str) -> str:\n"
        "    return urllib.parse.urlsplit(url).hostname or ''\n",
        "import os\ndef value() -> str:\n    return 'ok'\n",
        "class Catalog:\n"
        "    def resolve(self, code: str) -> str:\n"
        "        return code\n"
        "    def open(self) -> str:\n"
        "        return 'ok'\n"
        "def urlopen(url: str) -> str:\n"
        "    return url\n"
        "def use(catalog: Catalog) -> str:\n"
        "    return catalog.resolve('x') + catalog.open() + urlopen('local')\n",
    ],
    ids=[
        "purepath-suffix",
        "path-arithmetic",
        "urlparse",
        "urlsplit",
        "import-os-without-call",
        "unrelated-same-names",
    ],
)
def test_domain_io_scanner_allows_pure_and_unrelated_calls(source: str) -> None:
    assert _violation_kinds(source) == []


def test_domain_io_scanner_keeps_pandas_and_socket_import_zones() -> None:
    pandas_source = "import pandas as pd\n"
    pandas_kinds = _violation_kinds(pandas_source)
    assert pandas_kinds == ["import:pandas"]

    violations, allowed = scan_domain_source(
        pandas_source,
        relative_path=_SYNTHETIC_SCHEMA,
    )
    assert violations == ()
    assert [finding.kind for finding in allowed] == ["import:pandas"]

    socket_source = "import socket\n"
    assert _violation_kinds(socket_source) == ["import:socket"]


def test_domain_io_scanner_detects_importlib_file_loader_calls() -> None:
    source = (
        "import importlib.util\n"
        "def load(path: str) -> object:\n"
        "    return importlib.util.spec_from_file_location('m', path)\n"
    )
    assert "call:importlib.util.spec_from_file_location" in _violation_kinds(source)

    unrelated = (
        "def spec_from_file_location(name: str, path: str) -> tuple[str, str]:\n"
        "    return name, path\n"
        "def use(path: str) -> tuple[str, str]:\n"
        "    return spec_from_file_location('m', path)\n"
    )
    assert _violation_kinds(unrelated) == []
