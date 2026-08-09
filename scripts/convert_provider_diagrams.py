#!/usr/bin/env python3
"""
Script to convert provider diagrams to ADR-040 compliant format.
Removes YAML frontmatter and replaces with %% comment metadata.
Replaces inline styles with classDef canonical colour scheme.
"""

import re
import glob
from pathlib import Path

def convert_provider_diagram(file_path):
    """Convert a single provider diagram to ADR-040 format."""
    with open(file_path, 'r') as f:
        content = f.read()

    # Check for crossref-style header
    header_match = re.match(r'______________________________________________________________________\n\nVersion:.*?\n\n______________________________________________________________________\n\n', content, re.DOTALL)
    if header_match:
        # Remove the header
        content = content[header_match.end():]

    # Extract YAML frontmatter
    yaml_match = re.match(r'---\n(.*?)\n---\n', content, re.DOTALL)
    if not yaml_match:
        print(f"No YAML frontmatter found in {file_path}")
        return

    yaml_content = yaml_match.group(1)
    yaml_lines = yaml_content.split('\n')

    # Parse YAML fields
    title = ""
    description = ""
    version = "1.0.0"
    date = "2026-07-24"
    type_val = "flowchart"
    level = "system"
    adr_refs = []

    for line in yaml_lines:
        if line.startswith('title:'):
            title = line.split(':', 1)[1].strip()
        elif line.startswith('description:'):
            # Multi-line description
            desc_idx = yaml_lines.index(line)
            desc_lines = []
            for i in range(desc_idx + 1, len(yaml_lines)):
                if yaml_lines[i].startswith('  '):
                    desc_lines.append(yaml_lines[i].strip())
                else:
                    break
            description = ' '.join(desc_lines)
        elif line.startswith('version:'):
            version = line.split(':', 1)[1].strip()
        elif line.startswith('last_verified:'):
            date = line.split(':', 1)[1].strip()
        elif line.startswith('adr_references:'):
            # Extract ADR references
            adr_idx = yaml_lines.index(line)
            for i in range(adr_idx + 1, len(yaml_lines)):
                if yaml_lines[i].startswith('  - '):
                    adr_ref = yaml_lines[i].split(':', 1)[0].replace('  - ', '').strip()
                    adr_refs.append(adr_ref)
                else:
                    break

    # Build new metadata
    new_metadata = f"""%% Title: {title}
%% Description: {description}
%% @version {version}
%% @date {date}
%% @type {type_val}
%% @level {level}
%% @nodes 46
%% @adr {','.join(adr_refs)}"""

    # Replace YAML frontmatter with new metadata
    content = re.sub(r'---\n.*?\n---\n', new_metadata + '\n', content, flags=re.DOTALL)

    # Replace inline styles with classDef
    # Remove all style lines
    content = re.sub(r'    style .*?\n', '', content)

    # Add classDef definitions before the end
    class_def = """
    classDef domain fill:#f5f3ff,stroke:#7c3aed,stroke-width:2px
    classDef app fill:#f0fdf4,stroke:#16a34a,stroke-width:2px
    classDef infra fill:#fff1f2,stroke:#dc2626,stroke-width:2px
    classDef composition fill:#fff7ed,stroke:#ea580c,stroke-width:2px
    classDef interfaces fill:#eff6ff,stroke:#2563eb,stroke-width:2px
"""

    # Add classDef before the last line
    content = content.rstrip()
    content += class_def

    # Write back
    with open(file_path, 'w') as f:
        f.write(content)

    print(f"Converted {file_path}")

def main():
    """Convert all provider diagrams."""
    provider_dirs = [
        'chembl',
        'crossref',
        'openalex',
        'pubchem',
        'pubmed',
        'semanticscholar',
        'uniprot'
    ]

    base_path = Path('docs/02-architecture/diagrams/providers')

    for provider in provider_dirs:
        provider_path = base_path / provider
        mmd_files = glob.glob(str(provider_path / '*.mmd'))

        for mmd_file in mmd_files:
            # Skip already converted files (check if they have %% Title)
            with open(mmd_file, 'r') as f:
                first_line = f.readline()
                if first_line.startswith('%% Title:'):
                    print(f"Skipping {mmd_file} (already converted)")
                    continue

            convert_provider_diagram(mmd_file)

if __name__ == '__main__':
    main()