"""Bidirectional, command-scoped parity for the public Click reference (#12055).

Tables own their first-cell options; shell synopses/examples own the command
path they explicitly invoke. Prose and migration notes do not declare options.
Click-generated help is documented globally, not repeated in every table.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

import click
import pytest

pytestmark = pytest.mark.architecture

_OPTION = re.compile(r"(?<![\w-])--?[a-z][a-z0-9-]*")
_HEADING = re.compile(r"^#{3,4} `([a-z0-9-]+(?: [a-z0-9-]+)*)`")
CLI_DOC = Path(__file__).resolve().parents[2] / "docs/04-reference/cli.md"


def _public_commands(root: click.Command) -> dict[str, click.Command]:
    """Resolve eager/lazy children through Click, excluding metadata-hidden trees."""
    commands: dict[str, click.Command] = {}

    def visit(command: click.Command, path: str, parent: click.Context | None) -> None:
        """Traverse public descendants using the context of their owning group."""
        if command.hidden:
            return
        commands[path] = command
        context = click.Context(command, info_name=command.name, parent=parent)
        if isinstance(command, click.Group):
            for name in command.list_commands(context):
                child = command.get_command(context, name)
                assert child is not None, (
                    f"Unresolved public Click command: {path} {name}"
                )
                visit(child, f"{path} {name}".strip(), context)

    visit(root, "", None)
    return commands


def _shell_options(
    invocation: str, commands: dict[str, click.Command]
) -> dict[str, set[str]]:
    """Resolve shell paths and group-owned options without invoking callbacks."""
    parts = shlex.split(invocation)[1:]
    path = ""
    declarations: dict[str, set[str]] = {}
    while path in commands:
        command = commands[path]
        flags = declarations.setdefault(path, set())
        if not isinstance(command, click.Group):
            flags.update(_OPTION.findall(" ".join(parts)))
            break
        if not parts:
            break
        raw_token = parts.pop(0)
        token = raw_token.strip("[]")
        if raw_token.upper() == "[OPTIONS]" or token == "--":
            continue
        if token.startswith("<") or raw_token.upper() == "[COMMAND]":
            break
        if token.startswith("-"):
            name, separator, _ = token.partition("=")
            flags.add(name)
            option = next(
                (
                    param
                    for param in command.params
                    if isinstance(param, click.Option)
                    and name in (*param.opts, *param.secondary_opts)
                ),
                None,
            )
            if option is not None and not option.is_flag and not option.count:
                del parts[: max(0, option.nargs - bool(separator))]
            continue
        path = f"{path} {token}".strip()
    if path not in commands:
        declarations.setdefault(path, set())
    return declarations


def _documented_options(
    markdown: str, commands: dict[str, click.Command]
) -> dict[str, set[str]]:
    """Read headings/tables and validate shell paths against public Click metadata."""
    headings = {
        match.group(1)
        for line in markdown.splitlines()
        if (match := _HEADING.match(line))
    }
    documented = {path: set() for path in headings | {""}}
    section: str | None = None
    in_shell = False
    continued = ""
    for line in markdown.splitlines():
        if line.startswith("```"):
            in_shell = not in_shell and line.strip() in {"```bash", "```sh", "```shell"}
            continued = ""
            continue
        if in_shell:
            line = continued + line.strip()
            if line.endswith("\\"):
                continued = line[:-1] + " "
                continue
            continued = ""
            if not line.startswith("bioetl "):
                continue
            for path, flags in _shell_options(line, commands).items():
                if path not in commands:
                    documented.setdefault(path, set())
                elif path in documented:
                    documented[path].update(flags)
            continue
        if match := _HEADING.match(line):
            section = match.group(1)
        elif line.startswith("#"):
            section = None
        elif section is not None and line.startswith("|"):
            documented[section].update(_OPTION.findall(line.split("|", 2)[1]))
    return documented


def _parity_errors(root: click.Command, markdown: str) -> list[str]:
    """Report command and option differences independently for each command."""
    commands = _public_commands(root)
    documented = _documented_options(markdown, commands)
    errors = [
        f"undocumented command: {path}"
        for path in sorted(commands.keys() - documented.keys())
    ]
    errors += [
        f"unknown documented command: {path}"
        for path in sorted(documented.keys() - commands.keys())
    ]
    for path in sorted(commands.keys() & documented.keys()):
        command = commands[path]
        options = {
            flag
            for param in command.params
            if isinstance(param, click.Option) and not param.hidden
            for flag in (*param.opts, *param.secondary_opts)
        }
        help_option = command.get_help_option(click.Context(command))
        generated_help = set(help_option.opts) if help_option is not None else set()
        declared = documented[path] - (generated_help - options)
        missing = options - declared
        extra = declared - options
        if missing:
            errors.append(f"{path or '<root>'}: undocumented options {sorted(missing)}")
        if extra:
            errors.append(
                f"{path or '<root>'}: unknown documented options {sorted(extra)}"
            )
    return errors


def test_public_click_commands_and_options_match_reference() -> None:
    """Both set differences must be empty for every public command and group."""
    from bioetl.interfaces.cli.main import cli

    assert not (errors := _parity_errors(cli, CLI_DOC.read_text(encoding="utf-8"))), (
        "\n".join(errors)
    )


@pytest.fixture
def parity_cli() -> click.Group:
    """Build a small CLI with aliases and distinct command-owned options."""
    root = click.Group("bioetl")
    root.add_command(
        click.Command(
            "alpha",
            params=[
                click.Option(["--toggle/--no-toggle"]),
                click.Option(["--value", "-v"]),
            ],
        )
    )
    root.add_command(click.Command("beta", params=[click.Option(["--other"])]))
    return root


def test_parity_accepts_secondary_and_short_flags(parity_cli: click.Group) -> None:
    """Accept both boolean spellings and short aliases declared in the reference."""
    text = "### `alpha`\n| `--toggle / --no-toggle` | flag |\n| `--value`, `-v` | str |\n### `beta`\n```bash\nbioetl beta --other X\n```"
    assert _parity_errors(parity_cli, text) == []


@pytest.mark.parametrize("omitted", ["--toggle", "--no-toggle", "--value", "-v"])
def test_parity_detects_each_undocumented_alias(
    parity_cli: click.Group, omitted: str
) -> None:
    """Require every public alias rather than only the primary flag."""
    flags = [
        flag for flag in ("--toggle", "--no-toggle", "--value", "-v") if flag != omitted
    ]
    text = (
        f"### `alpha`\n| `{' '.join(flags)}` | flags |\n### `beta`\n| `--other` | str |"
    )
    assert _parity_errors(parity_cli, text) == [
        f"alpha: undocumented options {[omitted]}"
    ]


def test_parity_detects_stale_options_in_correct_command(
    parity_cli: click.Group,
) -> None:
    """Reject retired flags in the command where they are documented."""
    text = "### `alpha`\n| `--toggle --no-toggle --value -v --retired` | flags |\n### `beta`\n| `--other` | str |"
    assert _parity_errors(parity_cli, text) == [
        "alpha: unknown documented options ['--retired']"
    ]


def test_parity_does_not_borrow_options_from_another_section(
    parity_cli: click.Group,
) -> None:
    """Keep option ownership local to its documented command."""
    text = (
        "### `alpha`\n| `--toggle --no-toggle --value -v --other` | flags |\n### `beta`"
    )
    assert _parity_errors(parity_cli, text) == [
        "alpha: unknown documented options ['--other']",
        "beta: undocumented options ['--other']",
    ]


def test_parity_requires_optionless_commands_and_rejects_unknown_headings() -> None:
    """Validate command presence even when no options are declared."""
    root = click.Group("bioetl", commands={"actual": click.Command("actual")})
    assert _parity_errors(root, "### `invented`") == [
        "undocumented command: actual",
        "unknown documented command: invented",
    ]


def test_parity_uses_hidden_metadata_and_traverses_lazy_groups() -> None:
    """Resolve lazy public children while excluding hidden options and commands."""

    class LazyGroup(click.Group):
        def list_commands(self, ctx: click.Context) -> list[str]:
            """Expose the lazy child through the Click discovery interface."""
            return ["child"]

        def get_command(
            self, ctx: click.Context, cmd_name: str
        ) -> click.Command | None:
            """Resolve the child with one public option and one hidden option."""
            return click.Command(
                "child",
                params=[
                    click.Option(["--public"]),
                    click.Option(["--internal"], hidden=True),
                ],
            )

    root = click.Group(
        "bioetl",
        commands={
            "lazy": LazyGroup("lazy", params=[click.Option(["--group-option"])]),
            "private": click.Command("private", hidden=True),
        },
    )
    text = "### `lazy`\n| `--group-option` | str |\n#### `lazy child`\n| `--public` | str |"
    assert _parity_errors(root, text) == []
    assert _parity_errors(root, text.replace("--public", "--stale")) == [
        "lazy child: undocumented options ['--public']",
        "lazy child: unknown documented options ['--stale']",
    ]


def test_parity_ignores_migration_prose_and_description_column() -> None:
    """Exclude historical flags in prose and table descriptions from declarations."""
    root = click.Group(
        "bioetl",
        commands={"run": click.Command("run", params=[click.Option(["--new"])])},
    )
    text = "### `run`\nMigration: `--old` removed.\n| `--new` | Replaces `--old` |"
    assert _parity_errors(root, text) == []


def test_debug_reference_matches_supported_default() -> None:
    """Option-name parity must not mask the original unsupported-mode claim."""
    from bioetl.interfaces.cli.commands.debug import debug

    mode = next(param for param in debug.params if param.name == "mode")
    text = CLI_DOC.read_text(encoding="utf-8")
    section = text.split("### `debug`", 1)[1].split("### `diagnostics`", 1)[0]
    row = next(line for line in section.splitlines() if line.startswith("| `--mode`"))
    assert row.split("|")[3].strip(" `") == mode.default == "log"
    assert "CONFIG_ERROR" in row
    assert "не поддерживается" in section
    assert "all stages" not in section
    assert "CLI prompts" not in section


@pytest.mark.parametrize(
    "example", ["bioetl diagnostcs guide", "bioetl diagnostics guied"]
)
def test_parity_rejects_unknown_shell_command_paths(example: str) -> None:
    """Correct headings must not hide misspelled root or nested shell commands."""
    root = click.Group(
        "bioetl",
        commands={
            "diagnostics": click.Group(
                "diagnostics", commands={"guide": click.Command("guide")}
            )
        },
    )
    text = "### `diagnostics`\n#### `diagnostics guide`\n```bash\n" + example + "\n```"
    assert any(
        "unknown documented command:" in error for error in _parity_errors(root, text)
    )


@pytest.mark.parametrize("fence", ["bash", "sh", "shell"])
def test_parity_rejects_retired_option_on_shell_continuation(fence: str) -> None:
    """Continuation lines must not hide a removed flag after a valid command."""
    root = click.Group("bioetl", commands={"inspect": click.Command("inspect")})
    text = (
        f"### `inspect`\n```{fence}\nbioetl inspect \\\n    --silver-filter-only\n```"
    )
    assert _parity_errors(root, text) == [
        "inspect: unknown documented options ['--silver-filter-only']"
    ]


def test_parity_accepts_continued_command_path_and_options() -> None:
    """Join a split command path and retain each continued public option."""
    root = click.Group(
        "bioetl",
        commands={
            "group": click.Group(
                "group",
                commands={
                    "child": click.Command(
                        "child", params=[click.Option(["--value", "-v"])]
                    )
                },
            )
        },
    )
    text = "### `group`\n#### `group child`\n```bash\nbioetl group \\\n    child \\\n    --value X \\\n    -v Y\n```"
    assert _parity_errors(root, text) == []


def test_parity_keeps_leaf_arguments_and_generic_placeholder_out_of_paths() -> None:
    """Leaf positional arguments and an explicit generic synopsis are not commands."""
    root = click.Group("bioetl", commands={"show": click.Command("show")})
    text = (
        "### `show`\n```bash\nbioetl <command> [options]\nbioetl show some-record\n```"
    )
    assert _parity_errors(root, text) == []


@pytest.mark.parametrize("path", ["missing", "group typo"])
def test_parity_rejects_unknown_path_after_group_options(path: str) -> None:
    """Group flags and option values must not hide a later unknown command."""
    root = click.Group(
        "bioetl",
        params=[click.Option(["--verbose"], is_flag=True), click.Option(["--label"])],
        commands={"group": click.Group("group")},
    )
    text = (
        "| unused |\n### `group`\n```bash\nbioetl --verbose --label group "
        + path
        + "\n```"
    )
    assert any(
        "unknown documented command:" in error for error in _parity_errors(root, text)
    )


def test_parity_assigns_group_options_before_child_without_callbacks() -> None:
    """Consume metadata-declared values while retaining group option ownership."""

    def forbidden_callback(*_args: object, **_kwargs: object) -> None:
        """Fail if documentation inspection ever executes a Click callback."""
        pytest.fail("documentation parsing executed a callback")

    group = click.Group(
        "group",
        params=[
            click.Option(["--label"], callback=forbidden_callback),
            click.Option(["--toggle/--no-toggle"]),
        ],
        commands={"child": click.Command("child", callback=forbidden_callback)},
    )
    root = click.Group("bioetl", commands={"group": group})
    text = "### `group`\n#### `group child`\n```bash\nbioetl group --label child --toggle child\nbioetl group --label=child --no-toggle child\nbioetl group --label 'child label' --toggle child\n```"
    assert _parity_errors(root, text) == []
