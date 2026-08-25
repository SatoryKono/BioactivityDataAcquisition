"""S3 / #9599 composition Protocol placement inventory."""

from __future__ import annotations

from scripts.engineering.qa.report_composition_protocol_inventory import (
    collect_scoped_protocols,
    evaluate,
    main,
)
import yaml
from pathlib import Path


def test_composition_protocol_inventory_is_complete_and_shrinking() -> None:
    config_path = Path("configs/quality/composition_protocol_inventory.yaml")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    live = collect_scoped_protocols()
    errors = evaluate(config, live)
    assert not errors, "\n".join(errors)
    outside = [
        row
        for row in live
        if str(row["path"]).startswith("src/bioetl/composition/")
        and "/contracts/" not in str(row["path"])
    ]
    assert len(outside) == 0
    assert len(live) == int(config["expected_total"])


def test_report_composition_protocol_inventory_check_cli() -> None:
    assert main(["--check"]) == 0
