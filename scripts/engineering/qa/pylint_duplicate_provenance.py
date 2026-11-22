"""Record the compared-file identity directly from the Pylint scan."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

from pylint.lint import Run
from pylint.reporters.text import TextReporter

from scripts.engineering.qa.report_duplication_baseline import (
    _PYLINT_PACKAGE_ENTRIES_PREFIX,
)

if TYPE_CHECKING:
    from pylint.reporters.ureports.nodes import Section


def _confirmed_package_entries(files_by_name: Mapping[str, set[str]]) -> list[str]:
    return sorted(
        name
        for name, paths in files_by_name.items()
        if len(paths) == 1 and Path(next(iter(paths))).name == "__init__.py"
    )


class DuplicateProvenanceReporter(TextReporter):
    """Emit the default text plus an unambiguous initializer-name inventory."""

    def __init__(self) -> None:
        super().__init__()
        self._files_by_name: dict[str, set[str]] = {}

    def on_set_current_module(self, module: str, filepath: str | None) -> None:
        super().on_set_current_module(module, filepath)
        if module and filepath:
            physical_name = os.path.normcase(os.path.abspath(filepath))
            self._files_by_name.setdefault(module, set()).add(physical_name)

    def display_messages(self, layout: Section | None) -> None:
        super().display_messages(layout)
        names = _confirmed_package_entries(self._files_by_name)
        self.writeln(_PYLINT_PACKAGE_ENTRIES_PREFIX + json.dumps(names))


def main() -> None:
    """Run Pylint with the scoped provenance reporter."""
    Run(sys.argv[1:], reporter=DuplicateProvenanceReporter())


if __name__ == "__main__":
    main()
