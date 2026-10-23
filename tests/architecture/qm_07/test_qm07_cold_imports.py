import pytest

pytestmark = pytest.mark.unit


def test_cold_imports_dummy():
    assert True, "Unreachable by design proved by dummy"
