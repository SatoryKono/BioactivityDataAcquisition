"""Optional-stage failures keep their warning through CLI presentation."""

from types import SimpleNamespace

import pytest
from bioetl.interfaces.cli.exit_codes import ExitCode

from bioetl.interfaces.cli.commands.domains.composite.execution import (
    build_run_composite_result,
)
from bioetl.interfaces.cli.commands.domains.composite.support import (
    exit_with_composite_result,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "success,warnings,code,message",
    [
        (True, False, 0, "completed successfully"),
        (True, True, 0, "completed with warnings"),
        (False, False, ExitCode.PIPELINE_ERROR, "failed"),
    ],
)
def test_composite_result_preserves_warning_without_changing_optional_exit_code(
    success, warnings, code, message, capsys
):
    result = SimpleNamespace(
        is_success=success,
        had_warnings=warnings,
        failed_enrichers=["semanticscholar_publication"]
        if warnings or not success
        else [],
    )
    mapped = build_run_composite_result(result)
    with pytest.raises(SystemExit) as stopped:
        exit_with_composite_result(*mapped)
    assert stopped.value.code == code
    captured = capsys.readouterr()
    text = captured.out + captured.err
    assert message in text
    if warnings:
        assert "semanticscholar_publication" in text
        assert "completed successfully" not in text
