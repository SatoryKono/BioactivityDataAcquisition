import re

filepath = "src/bioetl/composition/runtime_builders/evidence_location_registration.py"
with open(filepath, 'r') as f:
    content = f.read()

content = content.replace("import os", "")
content = content.replace("os.environ.get(_DASHBOARD_DATA_ROOT_ENV, \"\").strip()", "getattr(settings, 'dashboard_data_root', \"\")")
content = content.replace("env_value = os.environ.get(RUNTIME_SOURCE_ID_ENV, \"\").strip()", "env_value = getattr(settings, 'runtime_source_id', \"\")")

with open(filepath, 'w') as f:
    f.write(content)
