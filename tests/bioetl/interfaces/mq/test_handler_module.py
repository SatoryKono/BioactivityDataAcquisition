import importlib


def test_mq_handler_module_importable():
    module = importlib.import_module("bioetl.interfaces.mq.handler")
    assert isinstance(module.__doc__, str)
