import sys
sys.path.insert(0, "src")
from bioetl.infrastructure.config._base import Settings
import json

schema = Settings.model_json_schema()
# Let's inspect PipelineSettings properties
pipeline_schema = schema['$defs']['PipelineSettings']
print("Pipeline settings keys:", pipeline_schema['properties'].keys())

control_plane_schema = schema['$defs']['ControlPlaneSettings']
print("Control plane keys:", control_plane_schema['properties'].keys())
