import re

with open("docs/04-reference/environment-variables.md") as f:
    docs_content = f.read()

docs_vars = set(re.findall(r'`(BIOETL_[A-Za-z0-9_]+)`', docs_content))
docs_vars = {v.replace("BIOETL_OBSERVABILITY__", "BIOETL_OBSERVABILITY_") for v in docs_vars}

with open("src/bioetl/infrastructure/config/_base.py") as f:
    base_content = f.read()

with open("src/bioetl/infrastructure/config/_observability_settings.py") as f:
    obs_content = f.read()

# basic fields
code_vars_base = set(re.findall(r'([a-z0-9_]+):', base_content))
code_vars_obs = set(re.findall(r'([a-z0-9_]+):', obs_content))

code_vars = {"BIOETL_" + v.upper() for v in code_vars_base}
code_vars.update({"BIOETL_OBSERVABILITY_" + v.upper() for v in code_vars_obs})

# Validation aliases
aliases = set(re.findall(r'validation_alias="([^"]+)"', base_content + obs_content))
code_vars.update(aliases)

print("In docs, not in code:")
for v in docs_vars - code_vars:
    print(v)

print("\nIn code, not in docs:")
for v in code_vars - docs_vars:
    print(v)
