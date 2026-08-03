# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Fixture wiring for integration storage metadata tests.

Pytest no longer allows ``pytest_plugins`` in nested ``conftest.py`` files.
Import the shared fixture module directly so its fixtures remain available only
to this subtree without registering a suite-wide plugin from a non-top-level
conftest.
"""

from tests.helpers.metadata_fixtures import *  # noqa: F403
