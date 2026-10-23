import sys
import json
import re

sys.path.insert(0, "src")
from bioetl.infrastructure.config._base import Settings

def get_code_vars(schema, prefix="BIOETL_"):
    vars = []
    for key, prop in schema.get("properties", {}).items():
        if "$ref" in prop:
            ref_name = prop["$ref"].split("/")[-1]
            ref_schema = Settings.model_json_schema().get("$defs", {}).get(ref_name, {})
            vars.extend(get_code_vars(ref_schema, prefix + key.upper() + "__"))
        elif "allOf" in prop:
            ref_name = prop["allOf"][0]["$ref"].split("/")[-1]
            ref_schema = Settings.model_json_schema().get("$defs", {}).get(ref_name, {})
            vars.extend(get_code_vars(ref_schema, prefix + key.upper() + "__"))
        else:
            if "validation_alias" in prop:
                vars.append(prop["validation_alias"])
            elif "validationAlias" in prop:
                 vars.append(prop["validationAlias"])
            else:
                 alias = prop.get("alias", key)
                 if alias.startswith("BIOETL_"):
                     vars.append(alias)
                 else:
                     vars.append(prefix + key.upper())
    return set(vars)

schema = Settings.model_json_schema()
code_vars = get_code_vars(schema)
# Also add WSL related and pytest related that might not be in config
code_vars.update({"BIOETL_WSL_VENV_DIR", "BIOETL_PYTEST_WINDOWS_XDIST_WORKERS"})

with open("docs/04-reference/environment-variables.md") as f:
    docs_content = f.read()

docs_vars = set(re.findall(r'`(BIOETL_[A-Za-z0-9_]+)`', docs_content))
docs_vars.update(set(re.findall(r'\*(BIOETL_[A-Za-z0-9_]+)\*', docs_content)))
docs_vars.update(set(re.findall(r'\b(BIOETL_[A-Za-z0-9_]+)\b', docs_content)))

# Filter docs_vars to only those that start with BIOETL_
docs_vars = {v for v in docs_vars if v.startswith("BIOETL_")}

# The docs_vars might include things like BIOETL_{PROVIDER}_{KEY}, let's remove it
docs_vars = {v for v in docs_vars if "{" not in v}

print("Variables in DOCS but not in CODE schema (may be unused/outdated or managed elsewhere):")
for v in sorted(list(docs_vars - code_vars)):
    print(v)

print("\nVariables in CODE schema but not in DOCS:")
for v in sorted(list(code_vars - docs_vars)):
    print(v)
