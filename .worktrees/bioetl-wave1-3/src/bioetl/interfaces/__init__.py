"""User interfaces for BioETL.

This package contains user-facing interfaces for the BioETL system.
Currently provides CLI and observability interfaces.

Components:
    cli: Command-line interface (Click-based).
    observability: User-facing observability utilities.

The interfaces layer sits at the outermost ring of the hexagonal
architecture and depends on all other layers per RULES.md.
"""
