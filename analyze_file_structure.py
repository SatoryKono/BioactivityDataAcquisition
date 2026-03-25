#!/usr/bin/env python3

import re
from pathlib import Path

def analyze_file(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find all function and class definitions
    pattern = r'^(def |class |@dataclass\s+)'
    matches = []
    
    for i, line in enumerate(content.split('\n'), 1):
        if re.match(pattern, line.strip()):
            matches.append((i, line.strip()))
    
    return matches

if __name__ == "__main__":
    files = [
        'src/bioetl/domain/observability_contract.py',
        'src/bioetl/domain/services/composite_validation_layer.py',
        'src/bioetl/domain/services/cross_validation_validator.py'
    ]
    
    for file in files:
        if Path(file).exists():
            print(f"\n=== {file} ===")
            matches = analyze_file(file)
            for line_num, line in matches:
                print(f"{line_num:3d}: {line}")
            print(f"Total: {len(matches)} definitions")
        else:
            print(f"{file}: NOT FOUND")