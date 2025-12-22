
try:
    from bioetl.application.core.runner import PipelineRunner
    print("Import successful")
except ImportError as e:
    print(f"Import failed: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
