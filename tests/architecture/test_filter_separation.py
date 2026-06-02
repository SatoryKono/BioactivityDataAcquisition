"""Architecture tests for nominal separation of Silver/Gold filter configs."""

from __future__ import annotations

import pytest

from bioetl.domain.filtering import (
    BaseFilterConfig,
    GoldFilterConfig,
    SilverFilterConfig,
)


pytestmark = pytest.mark.architecture


def test_silver_and_gold_are_not_subclasses_of_each_other() -> None:
    assert issubclass(SilverFilterConfig, GoldFilterConfig) is False
    assert issubclass(GoldFilterConfig, SilverFilterConfig) is False


def test_silver_and_gold_inherit_base_filter_config() -> None:
    assert issubclass(SilverFilterConfig, BaseFilterConfig)
    assert issubclass(GoldFilterConfig, BaseFilterConfig)


def test_instances_are_nominally_separated() -> None:
    silver = SilverFilterConfig(required_fields=("id",))
    gold = GoldFilterConfig(required_fields=("id",))

    assert isinstance(silver, GoldFilterConfig) is False
    assert isinstance(gold, SilverFilterConfig) is False
