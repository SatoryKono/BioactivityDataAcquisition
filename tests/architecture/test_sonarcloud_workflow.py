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
"""Repository contract checks for the retired SonarCloud integration."""

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture


def test_sonarcloud_workflow_is_not_shipped() -> None:
    assert not Path(".github/workflows/sonarcloud.yml").exists()


def test_sonarcloud_root_config_is_not_shipped() -> None:
    assert not Path("sonar-project.properties").exists()
