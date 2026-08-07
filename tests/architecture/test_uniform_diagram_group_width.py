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
"""Architecture tests for grouped width strategy in uniform diagram sizer."""

from __future__ import annotations

import pytest

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


pytestmark = pytest.mark.architecture


def _load_uniform_module() -> ModuleType:
    """Load scripts/diagrams/fix/uniform_diagram_sizes.py as a module."""
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "scripts" / "diagrams" / "uniform_diagram_sizes.py"
    spec = importlib.util.spec_from_file_location(
        "uniform_diagram_sizes_module",
        module_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sample_grouped_class_diagram(*, group_width: bool) -> list[str]:
    """Return minimal grouped class diagram with uneven line widths."""
    lines = [
        "%% @uniform-group g1 nodes=Alpha",
        "%% @uniform-group g2 nodes=Beta",
    ]
    if group_width:
        lines.append("%% @uniform-width group")
    lines.extend(
        [
            "classDiagram",
            "    class Alpha {",
            "        +very_long_member_name_that_drives_width",
            "    }",
            "    class Beta {",
            "        +x",
            "    }",
        ]
    )
    return lines


def _find_line_with_token(lines: list[str], token: str) -> str:
    for line in lines:
        if token in line:
            return line
    raise AssertionError(f"Expected token not found: {token}")


def test_grouped_default_uses_global_width() -> None:
    """Without @uniform-width override, grouped mode keeps global width."""
    uniform = _load_uniform_module()
    normalized = uniform._normalize_class_diagram(
        _sample_grouped_class_diagram(group_width=False)
    )

    beta_line = _find_line_with_token(normalized, "+x")
    rendered = "\n".join(normalized)

    assert "&nbsp;" in beta_line
    assert "width_strategy=global" in rendered


def test_grouped_width_strategy_reduces_padding() -> None:
    """@uniform-width group must reduce artificial padding in short groups."""
    uniform = _load_uniform_module()

    global_width = uniform._normalize_class_diagram(
        _sample_grouped_class_diagram(group_width=False)
    )
    group_width = uniform._normalize_class_diagram(
        _sample_grouped_class_diagram(group_width=True)
    )

    global_text = "\n".join(global_width)
    group_text = "\n".join(group_width)
    global_beta = _find_line_with_token(global_width, "+x")
    group_beta = _find_line_with_token(group_width, "+x")

    assert group_text.count("&nbsp;") < global_text.count("&nbsp;")
    assert group_beta.count("&nbsp;") < global_beta.count("&nbsp;")
    assert "width_strategy=group" in group_text
    assert "width=" in group_text


def test_group_width_directive_is_preserved_and_idempotent() -> None:
    """Grouped width mode should keep @uniform-width and stay idempotent."""
    uniform = _load_uniform_module()
    first = uniform._normalize_class_diagram(
        _sample_grouped_class_diagram(group_width=True)
    )
    second = uniform._normalize_class_diagram(first)

    assert first == second
    assert any(line.strip() == "%% @uniform-width group" for line in second)
    assert "width_strategy=group" in "\n".join(second)
