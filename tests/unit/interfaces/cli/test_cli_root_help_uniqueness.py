# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Root CLI help must list each command name exactly once."""

from __future__ import annotations

from collections.abc import Mapping
from importlib import import_module

import click
import pytest
from click.testing import CliRunner

from bioetl.interfaces.cli import cli
from bioetl.interfaces.cli.registry_helpers import format_command_help_rows

cli_main = import_module("bioetl.interfaces.cli.main")


pytestmark = pytest.mark.unit

_EAGER_ROOT_COMMANDS = ("dq", "debug", "lock")


def _command_rows_from_help(output: str) -> list[str]:
    lines = output.replace("\r\n", "\n").split("\n")
    in_commands = False
    names: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("Commands:"):
            in_commands = True
            continue
        if in_commands:
            if not stripped:
                if names:
                    break
                continue
            if stripped.startswith("Options:") or stripped.startswith("Usage:"):
                break
            names.append(stripped.split()[0])
    return names


def test_root_help_lists_each_command_once() -> None:
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0, result.output
    names = _command_rows_from_help(result.output)
    assert names, "root --help must render a Commands section"
    assert len(names) == len(set(names)), f"duplicate command rows: {names}"
    for command_name in _EAGER_ROOT_COMMANDS:
        assert names.count(command_name) == 1


def test_list_commands_is_unique_and_eager_first() -> None:
    names = cli.list_commands(click.Context(cli))

    assert names[:3] == list(_EAGER_ROOT_COMMANDS)
    assert len(names) == len(set(names))
    assert set(_EAGER_ROOT_COMMANDS).isdisjoint(cli_main._LAZY_COMMAND_SPECS)


@pytest.mark.parametrize("command_name", _EAGER_ROOT_COMMANDS)
def test_eager_root_commands_resolve_help(command_name: str) -> None:
    result = CliRunner().invoke(cli, [command_name, "--help"])

    assert result.exit_code == 0, result.output
    assert "Usage:" in result.output


def test_format_command_help_rows_deduplicates_overlapping_names() -> None:
    captured: list[list[tuple[str, str]]] = []

    class _Formatter:
        def section(self, name: str):
            del name

            class _Section:
                def __enter__(self) -> None:
                    return None

                def __exit__(self, *args: object) -> None:
                    del args

            return _Section()

        def write_dl(self, rows: list[tuple[str, str]]) -> None:
            captured.append(list(rows))

    eager: Mapping[str, tuple[object, str]] = {
        "dq": (object(), "eager dq"),
        "debug": (object(), "eager debug"),
    }
    lazy = {
        "dq": ("mod", "dq", "lazy dq"),
        "lock": ("mod", "lock", "lazy lock"),
        "run": ("mod", "run", "lazy run"),
    }

    format_command_help_rows(
        formatter=_Formatter(),  # type: ignore[arg-type]
        eager_commands=eager,
        lazy_commands=lazy,
    )

    assert captured == [
        [
            ("dq", "eager dq"),
            ("debug", "eager debug"),
            ("lock", "lazy lock"),
            ("run", "lazy run"),
        ]
    ]
