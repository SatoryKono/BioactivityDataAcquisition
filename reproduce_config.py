from bioetl.infrastructure.config import load_pipeline_config

try:
    config = load_pipeline_config("chembl_activity")
    print(f"Pipeline: {config.pipeline_name}")
    print(f"Primary Keys: {config.primary_keys}")

    # Check if 'id' is in primary_keys
    if "id" in config.primary_keys:
        print("ISSUE REPRODUCED: 'id' found in primary_keys")
    else:
        print("Config looks correct.")

except Exception as e:
    print(f"Error loading config: {e}")
