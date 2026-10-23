import re

def extract_env_vars():
    vars_code = {}

    def process_file(filepath, prefix="BIOETL_"):
        with open(filepath) as f:
            content = f.read()
            fields = re.findall(r'([a-z0-9_]+)\s*:\s*[A-Za-z0-9_\|\[\] ]+\s*=\s*Field\([^)]*\)', content, re.DOTALL)
            for var_name in fields:
                env_name = f"{prefix}{var_name.upper()}"
                vars_code[env_name] = {"source": filepath}

            # aliases
            aliases = re.findall(r'([a-z0-9_]+)\s*:\s*[A-Za-z0-9_\|\[\] ]+\s*=\s*Field\([^)]*validation_alias="([^"]+)"[^)]*\)', content, re.DOTALL)
            for var_name, alias in aliases:
                env_name = f"{prefix}{var_name.upper()}"
                if env_name in vars_code:
                    del vars_code[env_name]
                vars_code[alias] = {"source": filepath}

    process_file("src/bioetl/infrastructure/config/_base.py")
    process_file("src/bioetl/infrastructure/config/_observability_settings.py", "BIOETL_OBSERVABILITY__")
    process_file("src/bioetl/infrastructure/config/_pipeline_settings.py", "BIOETL_PIPELINE__")

    with open("src/bioetl/infrastructure/config/_pipeline_settings.py") as f:
        content = f.read()
        control_plane_fields = re.findall(r'([a-z0-9_]+)\s*:\s*[A-Za-z0-9_\|\[\] ]+\s*=\s*Field\([^)]*\)', content.split('class PipelineSettings')[0], re.DOTALL)
        for var_name in control_plane_fields:
            if var_name not in ["required_persistence_profile", "run_manifest_enabled", "run_ledger_enabled", "checkpoint_compatibility_policy"]:
                continue
            vars_code[f"BIOETL_PIPELINE__CONTROL_PLANE__{var_name.upper()}"] = {"source": "ControlPlaneSettings"}

    with open("docs/04-reference/environment-variables.md") as f:
        docs_content = f.read()

    docs_vars = set(re.findall(r'`(BIOETL_[A-Za-z0-9_]+)`', docs_content))

    print("Variables in docs but not found in code files:")
    for v in sorted(list(docs_vars - set(vars_code.keys()))):
        print(v)

    print("\nVariables in code but not in docs:")
    # Ignore nested object placeholders
    ignored_vars = ["BIOETL_OBSERVABILITY", "BIOETL_PIPELINE", "BIOETL_PIPELINE__CONTROL_PLANE", "BIOETL_PIPELINE__SILVER_METADATA_ATOMIC_RETRY", "BIOETL_PIPELINE__SILVER_MERGE_RETRY", "BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT"]
    for v in sorted(list(set(vars_code.keys()) - docs_vars)):
        if v not in ignored_vars:
            print(v)

extract_env_vars()
