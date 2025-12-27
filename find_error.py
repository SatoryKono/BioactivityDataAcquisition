import os

root_dir = r"E:/google_drive/05_AI/github/BioactivityDataAcquisition2"

for dirpath, dirnames, filenames in os.walk(root_dir):
    if ".venv" in dirpath:
        continue
    for filename in filenames:
        if filename.endswith(".py"):
            filepath = os.path.join(dirpath, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    if len(lines) >= 5:
                        line5 = lines[4] # 0-indexed
                        # Check if line 5 starts with triple quotes at column 5 (4 spaces indent)
                        if line5.startswith("    \"\"\"") or line5.startswith("    '''"):
                            print(f"File: {filepath}")
                            print(f"Line 5: {line5.rstrip()}")

                            # Check if it is closed
                            content = "".join(lines)
                            import ast
                            try:
                                ast.parse(content)
                            except SyntaxError as e:
                                print(f"SyntaxError in {filepath}: {e}")
                            except Exception as e:
                                print(f"Error parsing {filepath}: {e}")

            except Exception as e:
                pass
