# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture test: write mode types enforcement.

Tests that write modes use domain enums (SilverWriteMode, GoldWriteMode)
instead of Literal strings in domain layer.

REQ-ARCH-001: Type-safe write modes for Medallion policy enforcement.
See docs/06-architecture-review-consolidated.md R1 for rationale.
REQ-DATA-008 REQ-GOV-009: write-mode enums and governance of silver write policy.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

DOMAIN_CONFIG_PATHS = [
    Path("src/bioetl/domain/config/table.py"),
    Path("src/bioetl/domain/config/pipeline.py"),
]


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

    This test verifies that write_mode fields in the domain/config/ package
    use SilverWriteMode/GoldWriteMode enums from domain/medallion.py
    instead of Literal["merge", "append", ...] strings.

    Note: Currently a warning test (SHOULD) as backward compatibility
    allows string values that are converted to enums in __post_init__.
    Will become a MUST after full migration.
    """
    existing_paths = [p for p in DOMAIN_CONFIG_PATHS if p.exists()]
    assert existing_paths, "No domain config files found"

    all_pure_literals: list[tuple[str, int, str]] = []
    for config_path in existing_paths:
        source = config_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        checker = WriteModeTypeChecker()
        checker.visit(tree)

        # Expect NO pure Literal[...] for write modes (should be Enum | str)
        pure_literals = [
            (str(config_path), line, vals)
            for line, vals in checker.literal_write_modes
            # Filter out lines that are part of | str union type
            if "str" not in source.split("\n")[line - 1]
        ]
        all_pure_literals.extend(pure_literals)

    assert not all_pure_literals, (
        f"Found {len(all_pure_literals)} Literal write mode annotations:\n"
        + "\n".join(
            f"  {path} Line {line}: Literal{vals} should use WriteMode enum"
            for path, line, vals in all_pure_literals
        )
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
    from bioetl.domain.config import PipelineConfig, TableConfig
    from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode

    config = PipelineConfig(
        pipeline_name="test",
        provider="test",
        entity_type="test",
        table=TableConfig(
            primary_keys=("id",),
            silver_table="test_silver",
            silver_write_mode="merge",
            gold_write_mode="scd2",
        ),
    )

    assert isinstance(config.table.silver_write_mode, SilverWriteMode)
    assert config.table.silver_write_mode == SilverWriteMode.MERGE

    assert isinstance(config.table.gold_write_mode, GoldWriteMode)
    assert config.table.gold_write_mode == GoldWriteMode.SCD2


def test_overwrite_for_silver_raises_error() -> None:
    """silver_write_mode='overwrite' MUST raise ValueError.

    The deprecated 'overwrite' alias for Silver layer has been removed.
    Use SilverWriteMode.DELETE explicitly for rebuild operations.
    """
    from bioetl.domain.config import TableConfig

    with pytest.raises(ValueError, match=r"Invalid Silver write mode.*overwrite"):
        TableConfig(silver_write_mode="overwrite")


def test_no_silent_degradation_in_batch_writer() -> None:
    """BatchWriter MUST NOT silently convert overwrite to append.

    This test verifies that the silent degradation pattern has been removed
    from batch_writer.py as per R1 refactoring.
    """
    batch_writer_path = Path("src/bioetl/application/core/batch_writer.py")
    assert batch_writer_path.exists(), f"{batch_writer_path} does not exist"

    source = batch_writer_path.read_text(encoding="utf-8")

    # Check that the old silent degradation pattern is gone
    assert 'if write_mode == "overwrite":' not in source, (
        "Silent degradation pattern still exists in batch_writer.py. "
        'Remove the \'if write_mode == "overwrite": write_mode = "append"\' logic.'
    )

    # Check behavior invariant instead of implementation comment marker:
    # Silver mode must not include "overwrite" alias in runtime cast.
    assert 'Literal["merge", "append", "delete"]' in source, (
        "BatchWriter silver mode must use explicit delete/append/merge set "
        "without overwrite alias."
    )
