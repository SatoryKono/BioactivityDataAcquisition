from bioetl.infrastructure.config import Settings, get_settings

try:
    print("Attempting to instantiate Settings...")
    settings = Settings()
    print("Settings instantiated successfully.")
    print(f"Environment: {settings.env}")
except Exception as e:
    print(f"Error instantiating Settings: {e}")
    import traceback

    traceback.print_exc()
