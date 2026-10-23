import sys

sys.path.insert(0, "src")
from bioetl.infrastructure.config._base import Settings

def print_env_vars(schema, prefix="BIOETL_"):
    for key, prop in schema.get("properties", {}).items():
        if "$ref" in prop:
            ref_name = prop["$ref"].split("/")[-1]
            ref_schema = Settings.model_json_schema().get("$defs", {}).get(ref_name, {})
            print_env_vars(ref_schema, prefix + key.upper() + "__")
        elif "allOf" in prop:
            ref_name = prop["allOf"][0]["$ref"].split("/")[-1]
            ref_schema = Settings.model_json_schema().get("$defs", {}).get(ref_name, {})
            print_env_vars(ref_schema, prefix + key.upper() + "__")
        else:
            if "validation_alias" in prop:
                print(prop["validation_alias"])
            elif "validationAlias" in prop:
                 print(prop["validationAlias"])
            else:
                 alias = prop.get("alias", key)
                 if alias.startswith("BIOETL_"):
                     print(alias)
                 else:
                     print(prefix + key.upper())

schema = Settings.model_json_schema()
print_env_vars(schema)
