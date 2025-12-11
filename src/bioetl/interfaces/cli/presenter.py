"""Presentation utilities for CLI output."""

from __future__ import annotations

from typing import Iterable

from rich.console import Console

from bioetl.application.use_cases import RunPipelineResponse


class CliPresenter:
    """Formats and renders CLI messages."""

    def __init__(self, console: Console) -> None:
        self._console = console

    def show_available_pipelines(self, names: Iterable[str]) -> None:
        """Display a list of available pipelines."""
        self._console.print("[bold]Available Pipelines:[/bold]")
        for name in names:
            self._console.print(f"  - {name}")

    def show_start_info(self, pipeline_name: str, limit: int | None, dry_run: bool) -> None:
        """Show pipeline start details."""
        self._console.print(f"[bold]Starting pipeline:[/bold] {pipeline_name}")
        if limit:
            self._console.print(f"[dim]Limit:[/dim] {limit} records")
        if dry_run:
            self._console.print("[dim]Mode:[/dim] dry-run")

    def present_result(self, response: RunPipelineResponse) -> None:
        """Render pipeline execution result."""
        if response.success:
            self._console.print("[green]✓ Pipeline finished successfully[/green]")
            self._console.print(f"  Rows: {response.row_count}")
            if response.output_path:
                self._console.print(f"  Output: {response.output_path}")
            return

        self._console.print("[red]✗ Pipeline failed[/red]")
        for error in response.errors:
            self._console.print(f"  [red]Error:[/red] {error}")

    def show_error(self, message: str) -> None:
        """Render an error message."""
        self._console.print(f"[red]Error:[/red] {message}")

    def show_interrupt(self) -> None:
        """Notify user about interruption."""
        self._console.print("\n[yellow]Interrupted by user[/yellow]")

    def show_config_valid(self) -> None:
        """Display successful config validation message."""
        self._console.print("[green]✓[/green] Config is valid")


__all__ = ["CliPresenter"]
