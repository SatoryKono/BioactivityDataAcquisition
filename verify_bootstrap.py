
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path.cwd() / "src"))

from bioetl.bootstrap import bootstrap_pipeline
from bioetl.infrastructure.factories.pipelines.chembl_activity import ChEMBLActivityPipelineFactory

print("Imports successful")
