# harness.py
from tests.integration.infrastructure.durability._child_runner import run_child

class DurabilityHarness:
    def __init__(self):
        pass

    def run_isolated(self, target, args):
        return run_child(target, args)
