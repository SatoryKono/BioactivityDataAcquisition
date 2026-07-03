"""Fixture wiring for integration storage metadata tests.

Pytest no longer allows ``pytest_plugins`` in nested ``conftest.py`` files.
Import the shared fixture module directly so its fixtures remain available only
to this subtree without registering a suite-wide plugin from a non-top-level
conftest.
"""

from tests.helpers.metadata_fixtures import *  # noqa: F401,F403
