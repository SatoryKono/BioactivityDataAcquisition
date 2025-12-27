import ast
import os
import traceback

root_dir = r"E:/google_drive/05_AI/github/BioactivityDataAcquisition2/tests"

print(f"Checking syntax for all .py files in {root_dir}...")

for dirpath, dirnames, filenames in os.walk(root_dir):
    for filename in filenames:
        if filename.endswith(".py"):
            filepath = os.path.join(dirpath, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                ast.parse(content)
            except SyntaxError as e:
                print(f"SyntaxError in {filepath}: {e}")
            except Exception as e:
                print(f"Error parsing {filepath}: {e}")
                traceback.print_exc()

print("Done.")
