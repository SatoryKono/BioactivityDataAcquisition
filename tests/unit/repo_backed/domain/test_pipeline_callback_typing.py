"""Public callback protocols accept the domain context without casts."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.repo_backed, pytest.mark.subprocess_backed]


def test_pipeline_callback_consumer_types(tmp_path: Path) -> None:
    """Strict mypy accepts domain and contravariant object callbacks."""
    consumer = tmp_path / "consumer.py"
    consumer.write_text(
        """from bioetl.domain.context import PipelineContext
from bioetl.domain.ports.pipeline_callbacks import GoldFilterCallback, GoldTransformCallback, TransformCallback
from bioetl.domain.types import JsonDict

def domain_filter(context: PipelineContext, record: JsonDict) -> bool:
    return True

def domain_gold_transform(context: PipelineContext, record: JsonDict) -> JsonDict:
    return record

async def domain_transform(context: PipelineContext, record: JsonDict, index: int) -> object | None:
    return record

def broad_filter(context: object, record: JsonDict) -> bool:
    return True

filter_callback: GoldFilterCallback = domain_filter
gold_transform_callback: GoldTransformCallback = domain_gold_transform
transform_callback: TransformCallback = domain_transform
broad_filter_callback: GoldFilterCallback = broad_filter
""",
        encoding="utf-8",
    )
    root = Path(__file__).resolve().parents[4]
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "mypy",
            "--strict",
            "--no-incremental",
            "--follow-imports=silent",
            "--cache-dir",
            str(tmp_path / "cache"),
            str(consumer),
        ],
        cwd=root,
        env={**os.environ, "MYPYPATH": str(root / "src")},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_callback_module_does_not_import_context_at_runtime() -> None:
    """Importing callbacks alone must not pull in the context module."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import bioetl.domain.ports.pipeline_callbacks; "
            "assert 'bioetl.domain.context' not in sys.modules",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
