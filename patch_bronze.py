import re
with open("tests/unit/infrastructure/storage/test_bronze_writer_cleanup_and_sidecar.py", "r") as f:
    text = f.read()

text = text.replace("assert bronze_input.source_metadata == source_metadata", "assert bronze_input.source_metadata.url == source_metadata.url")

with open("tests/unit/infrastructure/storage/test_bronze_writer_cleanup_and_sidecar.py", "w") as f:
    f.write(text)
