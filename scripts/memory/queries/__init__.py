"""Memory query operations."""

try:
    from scripts.memory.queries.query import main
    __all__ = ["main"]
except ImportError:
    __all__ = []
