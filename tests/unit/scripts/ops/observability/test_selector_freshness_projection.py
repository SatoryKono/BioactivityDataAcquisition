"""Exercise the shipped Infinity selector expression using the JSONata engine."""

from __future__ import annotations

import json
import os
import shutil
import subprocess

import pytest

from scripts.ops.observability.grafana._selected_run_panels import SELECTOR_ROWS

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("items", "expected"),
    [
        ([], [{"text": "НЕТ ЗАПУСКОВ", "value": "-"}]),
        (
            [{"text": "today [STALE catalog]", "value": "run-1"}],
            [{"text": "today", "value": "run-1"}],
        ),
        ([{"text": "today", "value": "run-1"}], [{"text": "today", "value": "run-1"}]),
        (
            [
                {"text": "old [STALE catalog]", "value": "r1", "extra": 7},
                {"text": "today", "value": "r2"},
            ],
            [
                {"text": "old", "value": "r1", "extra": 7},
                {"text": "today", "value": "r2"},
            ],
        ),
    ],
)
def test_catalog_annotation_does_not_rewrite_run_identity(items, expected):
    node = shutil.which("node")
    module = os.environ.get("JSONATA_MODULE")
    if not node or not module:
        pytest.skip("set JSONATA_MODULE to a jsonata package to execute the selector")
    source = (
        "const fs=require('fs'); const jsonata=require(process.env.JSONATA_MODULE); "
        "const data=JSON.parse(fs.readFileSync(0,'utf8')); "
        "jsonata(data.expression).evaluate(data.payload).then(result=>"
        "process.stdout.write(JSON.stringify(result))).catch(error=>{console.error(error);process.exit(1)});"
    )
    result = subprocess.run(
        [node, "-e", source],
        input=json.dumps({"expression": SELECTOR_ROWS, "payload": {"items": items}}),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == expected
