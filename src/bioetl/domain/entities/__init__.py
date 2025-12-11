"""Domain entities for bioactivity data.

This module provides strongly-typed domain entities following DDD principles.
Entities encapsulate business rules and invariants for core domain concepts.

Available Entities:
    - Activity: Bioactivity measurement (molecule-target interaction)
    - Assay: Biological assay (experimental procedure)
    - Target: Biological target (protein, cell, organism)
    - Molecule: Chemical compound
    - Cell: Cell line
    - Publication: Scientific publication/document
    - Tissue: Biological tissue

Usage:
    >>> from bioetl.domain.entities import Activity, Target
    >>> activity = Activity.from_record(raw_data)
    >>> target = Target.from_record(target_data)

Each entity provides:
    - Immutable data structure (frozen dataclass)
    - Type-safe attributes
    - Business key computation for deduplication
    - Validation of invariants
    - Factory method from_record() for creation from raw data
"""

from bioetl.domain.entities.activity import Activity
from bioetl.domain.entities.assay import Assay
from bioetl.domain.entities.base import EntityBase, extract_field
from bioetl.domain.entities.cell import Cell
from bioetl.domain.entities.molecule import Molecule
from bioetl.domain.entities.publication import Publication
from bioetl.domain.entities.target import Target
from bioetl.domain.entities.tissue import Tissue

__all__ = [
    # Base
    "EntityBase",
    "extract_field",
    # Entities
    "Activity",
    "Assay",
    "Cell",
    "Molecule",
    "Publication",
    "Target",
    "Tissue",
]
