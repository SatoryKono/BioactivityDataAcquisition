"""Repository contract checks for the retired SonarCloud integration."""

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture


def test_sonarcloud_workflow_is_not_shipped() -> None:
    assert not Path(".github/workflows/sonarcloud.yml").exists()


def test_sonarcloud_root_config_is_not_shipped() -> None:
    assert not Path("sonar-project.properties").exists()
