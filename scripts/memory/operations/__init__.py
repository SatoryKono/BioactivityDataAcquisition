"""Memory operations."""

try:
    from scripts.memory.operations.sync import main

    __all__ = ["main"]
except ImportError:
    __all__ = []
