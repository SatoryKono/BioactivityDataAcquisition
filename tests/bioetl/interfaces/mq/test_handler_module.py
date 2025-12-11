import importlib

import pytest


def test_mq_handler_module_importable():
    """Test that MQ handler module can be imported if it exists."""
    try:
        module = importlib.import_module("bioetl.interfaces.mq.handler")
        assert isinstance(module.__doc__, str)
    except ModuleNotFoundError:
        pytest.skip("MQ handler module not implemented yet")
