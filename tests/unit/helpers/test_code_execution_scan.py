"""Regression coverage for the security execution-call scan."""

import pytest

from tests.helpers.code_execution_scan import execution_calls


@pytest.mark.parametrize(
    "source",
    [
        "eval(payload)",
        "exec(payload)",
        "builtins.eval(payload)",
        "builtins.exec(payload)",
        "untrusted.list.eval(payload)",
        "pl.col('field').list.eval(payload)",
        "from builtins import eval as evaluate\nevaluate(payload)",
        "compile(payload, 'input', 'exec')",
        "compile(payload, filename='input', mode='exec')",
    ],
)
def test_detects_python_execution(source: str) -> None:
    assert execution_calls(source)


@pytest.mark.parametrize(
    "source",
    [
        "import polars as pl\npl.col('field').list.eval(pl.element().struct.field('display'))",
        "# eval(payload)\nmessage = 'exec(payload)'",
        "compile(pattern, flags)",
        "compile(payload, 'input', 'eval')",
    ],
)
def test_ignores_non_execution_expressions(source: str) -> None:
    assert execution_calls(source) == ()
