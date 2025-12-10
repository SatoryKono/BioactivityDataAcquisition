
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from unittest.mock import MagicMock
sys.modules.setdefault("tqdm", MagicMock())

from bioetl.interfaces.container_factory import create_config_loader
from bioetl.infrastructure.config.loader import get_schema_contract_provider, set_schema_contract_provider
from bioetl.interfaces.simple_container import SimplePipelineContainer

def test_debug_provider():
    print(f"Initial provider: {get_schema_contract_provider()}")
    
    container = SimplePipelineContainer()
    print(f"Container created. Bootstrapped: {container.is_bootstrapped}")
    
    container.bootstrap()
    print(f"Container bootstrapped. Bootstrapped: {container.is_bootstrapped}")
    print(f"Provider in container: {container._schema_contract_provider}")
    print(f"Global provider: {get_schema_contract_provider()}")
    
    config_loader = create_config_loader()
    print(f"Config loader created. Global provider: {get_schema_contract_provider()}")

if __name__ == "__main__":
    test_debug_provider()
