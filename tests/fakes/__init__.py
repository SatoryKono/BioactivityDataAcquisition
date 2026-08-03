"""Fake implementations for testing.

Provides in-memory implementations of domain ports for integration tests.
"""

from tests.fakes.checkpoint_fake import InMemoryCheckpoint
from tests.fakes.quarantine_fake import InMemoryQuarantine
from tests.fakes.storage_fake import InMemoryStorage

__all__ = [
    "InMemoryCheckpoint",
    "InMemoryQuarantine",
    "InMemoryStorage",
]
