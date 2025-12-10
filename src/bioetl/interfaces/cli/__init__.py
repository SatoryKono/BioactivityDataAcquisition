"""CLI interface for BioETL.

This module provides a Typer-based command line interface for pipeline operations.

Available commands:
    - list-pipelines: Show all available pipelines
    - validate-config: Validate a pipeline configuration file
    - run: Execute a pipeline with specified configuration
    - smoke-run: Quick test run with limited data

Example usage:
    # As a module
    from bioetl.interfaces.cli import app
    app()

    # From command line
    $ bioetl list-pipelines
    $ bioetl run activity_chembl --profile development
    $ bioetl smoke-run activity_chembl
"""

from bioetl.interfaces.cli.app import app

__all__ = ["app"]
