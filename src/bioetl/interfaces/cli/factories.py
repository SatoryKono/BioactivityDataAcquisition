"""Default factories for CLI commands."""

from bioetl.interfaces.cli.contracts import CLICommandABC


def default_cli_command() -> CLICommandABC:
    """Stub factory for CLICommandABC until concrete commands are wired."""

    raise NotImplementedError("CLICommandABC default command is not configured")


__all__ = ["default_cli_command"]

