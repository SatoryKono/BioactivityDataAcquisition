"""Regression tests for compatibility option registration in ``tests.conftest``."""

import pytest

from tests.conftest import pytest_addoption


class _Parser:
    def __init__(self, *, vcr_error: ValueError | None = None) -> None:
        self.vcr_error = vcr_error
        self.options: list[str] = []

    def addoption(self, name: str, **kwargs: object) -> None:
        if name == "--vcr-record" and self.vcr_error is not None:
            raise self.vcr_error
        self.options.append(name)


def test_pytest_addoption_ignores_existing_vcr_record_option() -> None:
    duplicate_error = ValueError("option names {'--vcr-record'} already added")
    parser = _Parser(vcr_error=duplicate_error)

    pytest_addoption(parser)

    assert "--vcr-record" not in parser.options


def test_pytest_addoption_reraises_unexpected_value_error() -> None:
    parser = _Parser(vcr_error=ValueError("invalid option configuration"))

    with pytest.raises(ValueError, match="invalid option configuration"):
        pytest_addoption(parser)
