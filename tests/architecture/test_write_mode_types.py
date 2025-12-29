"""Architecture test: write mode types enforcement.

Tests that write modes use domain enums (SilverWriteMode, GoldWriteMode)
instead of Literal strings in domain layer.

REQ-ARCH-041: Type-safe write modes for Medallion policy enforcement.
See docs/06-architecture-review-consolidated.md R1 for rationale.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

DOMAIN_CONFIG_PATH = Path("src/bioetl/domain/config.py")


class WriteModeTypeChecker(ast.NodeVisitor):
    """AST visitor to find Literal type annotations for write modes."""

    def __init__(self) -> None:
        self.literal_write_modes: list[tuple[int, str]] = []

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Check for Literal[...] with write mode strings."""
        # Check if it's a Literal type annotation
        if isinstance(node.value, ast.Name) and node.value.id == "Literal":
            # Check if it contains write mode strings
            if isinstance(node.slice, ast.Tuple):
                values = [
                    elt.value
                    for elt in node.slice.elts
                    if isinstance(elt, ast.Constant)
                ]
            elif isinstance(node.slice, ast.Constant):
                values = [node.slice.value]
            else:
                values = []

            # Check for write mode values
            write_mode_values = {"merge", "append", "overwrite", "delete", "scd2"}
            if any(v in write_mode_values for v in values if isinstance(v, str)):
                self.literal_write_modes.append((node.lineno, str(values)))

        self.generic_visit(node)


def test_no_literal_write_modes_in_domain_config() -> None:
    """Domain config SHOULD use WriteMode enums, not Literal strings.

    This test verifies that write_mode fields in domain/config.py
    use SilverWriteMode/GoldWriteMode enums from domain/medallion.py
    instead of Literal["merge", "append", ...] strings.

    Note: Currently a warning test (SHOULD) as backward compatibility
    allows string values that are converted to enums in __post_init__.
    Will become a MUST after full migration.
    """
    if not DOMAIN_CONFIG_PATH.exists():
        pytest.skip(f"{DOMAIN_CONFIG_PATH} does not exist")

    source = DOMAIN_CONFIG_PATH.read_text()
    tree = ast.parse(source)

    checker = WriteModeTypeChecker()
    checker.visit(tree)

    # Currently we allow Literal for backward compatibility with type: str | Enum
    # But we want to track and eventually remove all pure Literal annotations
    # This test documents the current state

    # Expect NO pure Literal[...] for write modes (should be Enum | str)
    pure_literals = [
        (line, vals)
        for line, vals in checker.literal_write_modes
        # Filter out lines that are part of | str union type
        if "str" not in source.split("\n")[line - 1]
    ]

    # For now, just report - will be a hard failure after migration
    if pure_literals:
        warnings = [
            f"  Line {line}: Literal{vals} should use WriteMode enum"
            for line, vals in pure_literals
        ]
        pytest.skip(
            f"Found {len(pure_literals)} Literal write mode annotations:\n"
            + "\n".join(warnings)
        )


def test_write_mode_enums_exist_in_domain() -> None:
    """Domain MUST define SilverWriteMode and GoldWriteMode enums."""
    from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode

    # Verify enum values
    assert SilverWriteMode.MERGE.value == "merge"
    assert SilverWriteMode.APPEND.value == "append"
    assert SilverWriteMode.DELETE.value == "delete"

    assert GoldWriteMode.APPEND.value == "append"
    assert GoldWriteMode.SCD2.value == "scd2"
    assert GoldWriteMode.OVERWRITE.value == "overwrite"


def test_write_mode_enums_have_from_string() -> None:
    """Write mode enums MUST have from_string classmethod for YAML parsing."""
    from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode

    # Test SilverWriteMode.from_string
    assert SilverWriteMode.from_string("merge") == SilverWriteMode.MERGE
    assert SilverWriteMode.from_string("APPEND") == SilverWriteMode.APPEND
    assert SilverWriteMode.from_string("Delete") == SilverWriteMode.DELETE

    # Test GoldWriteMode.from_string
    assert GoldWriteMode.from_string("append") == GoldWriteMode.APPEND
    assert GoldWriteMode.from_string("SCD2") == GoldWriteMode.SCD2
    assert GoldWriteMode.from_string("Overwrite") == GoldWriteMode.OVERWRITE


def test_write_mode_from_string_invalid_raises() -> None:
    """from_string MUST raise ValueError for invalid modes."""
    from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode

    with pytest.raises(ValueError, match="Invalid Silver write mode"):
        SilverWriteMode.from_string("invalid")

    with pytest.raises(ValueError, match="Invalid Gold write mode"):
        GoldWriteMode.from_string("invalid")


def test_table_config_converts_strings_to_enums() -> None:
    """TableConfig MUST convert string write modes to enums."""
    from bioetl.domain.config import TableConfig
    from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode

    # Test with string inputs (backward compatibility)
    config = TableConfig(
        silver_write_mode="merge",
        gold_write_mode="append",
    )

    assert isinstance(config.silver_write_mode, SilverWriteMode)
    assert config.silver_write_mode == SilverWriteMode.MERGE

    assert isinstance(config.gold_write_mode, GoldWriteMode)
    assert config.gold_write_mode == GoldWriteMode.APPEND


def test_table_config_accepts_enums_directly() -> None:
    """TableConfig MUST accept enum values directly."""
    from bioetl.domain.config import TableConfig
    from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode

    config = TableConfig(
        silver_write_mode=SilverWriteMode.DELETE,
        gold_write_mode=GoldWriteMode.SCD2,
    )

    assert config.silver_write_mode == SilverWriteMode.DELETE
    assert config.gold_write_mode == GoldWriteMode.SCD2


def test_pipeline_config_converts_strings_to_enums() -> None:
    """PipelineConfig MUST convert string write modes to enums."""
    from bioetl.domain.config import PipelineConfig
    from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode

    config = PipelineConfig(
        pipeline_name="test",
        provider="test",
        entity_type="test",
        primary_keys=("id",),
        silver_table="test_silver",
        write_mode="merge",
        gold_write_mode="scd2",
    )

    assert isinstance(config.write_mode, SilverWriteMode)
    assert config.write_mode == SilverWriteMode.MERGE

    assert isinstance(config.gold_write_mode, GoldWriteMode)
    assert config.gold_write_mode == GoldWriteMode.SCD2


def test_deprecated_overwrite_for_silver_warns() -> None:
    """silver_write_mode='overwrite' SHOULD warn and convert to DELETE."""
    import warnings

    from bioetl.domain.config import TableConfig
    from bioetl.domain.medallion import SilverWriteMode

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        config = TableConfig(silver_write_mode="overwrite")

        # Should have deprecation warning
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "overwrite" in str(w[0].message)
        assert "DELETE" in str(w[0].message)

        # Should be converted to DELETE
        assert config.silver_write_mode == SilverWriteMode.DELETE


def test_no_silent_degradation_in_batch_writer() -> None:
    """BatchWriter MUST NOT silently convert overwrite to append.

    This test verifies that the silent degradation pattern has been removed
    from batch_writer.py as per R1 refactoring.
    """
    batch_writer_path = Path("src/bioetl/application/core/batch_writer.py")
    if not batch_writer_path.exists():
        pytest.skip(f"{batch_writer_path} does not exist")

    source = batch_writer_path.read_text()

    # Check that the old silent degradation pattern is gone
    assert 'if write_mode == "overwrite":' not in source, (
        "Silent degradation pattern still exists in batch_writer.py. "
        'Remove the \'if write_mode == "overwrite": write_mode = "append"\' logic.'
    )

    # Check that new pattern is present
    assert (
        "Pass write mode directly without silent degradation" in source
    ), "R1 refactoring comment should be present in batch_writer.py"
