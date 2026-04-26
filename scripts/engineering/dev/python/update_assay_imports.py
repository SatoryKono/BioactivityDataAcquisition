#!/usr/bin/env python3
"""Update assay profile imports."""

import sys

# Read the file
with open("src/bioetl/domain/normalization/profiles/chembl_assay.py", "r") as f:
    content = f.read()

# Find the import section and add new imports
import_section = """from bioetl.domain.config.enum_loader import get_chembl_enum_set
from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.schemas.chembl.assay import AssaySchema"""

new_import_section = """from bioetl.domain.config.enum_loader import get_chembl_enum_set
from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.rules import normalize_cross_pipeline_case
from bioetl.domain.normalization.identifiers import normalize_ontology_id
from bioetl.domain.schemas.chembl.assay import AssaySchema"""

# Replace the import section
updated_content = content.replace(import_section, new_import_section)

# Write the updated content
with open("src/bioetl/domain/normalization/profiles/chembl_assay.py", "w") as f:
    f.write(updated_content)

print("✅ Assay profile imports updated successfully")
