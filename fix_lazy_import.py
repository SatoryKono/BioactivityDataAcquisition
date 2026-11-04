import re

filepath = "scripts/engineering/quality/architecture_quality_scoring.py"
with open(filepath, 'r') as f:
    content = f.read()

content = content.replace("raise ValueError(\"lazy_import_observed_count must be 0 when max_count is 0\")", 'raise ValueError("lazy_import_observed_count must be 0 when cap is 0")')
with open(filepath, 'w') as f:
    f.write(content)
