#!/usr/bin/env python3
"""Unified entry point for scripts/data_quality/ commands.

Usage:
    python -m scripts.data_quality <command> [args...]
    python -m scripts.data_quality --help

Commands:
    check-dq-dsl-parity              Check DQ DSL parity with documentation
    check-entity-config-parity       Check entity config parity with pipeline specs
    export-chembl-observed-vocab     Export ChEMBL observed vocabulary from fixtures
    inventory-silver-filters-migration  Inventory silver filters for migration
    run-silver-gold-filter-parity    Run silver/gold filter parity checks
"""

from __future__ import annotations

from scripts.engineering.common.cli_dispatch import dispatch_cli, module_command

COMMANDS = {
    "check-dq-dsl-parity": "scripts.data_quality.check_dq_dsl_parity",
    "check-entity-config-parity": "scripts.data_quality.check_entity_config_parity",
    "export-chembl-observed-vocab": "scripts.data_quality.export_chembl_observed_vocab",
    "inventory-silver-filters-migration": "scripts.data_quality.inventory_silver_filters_migration",
    "run-silver-gold-filter-parity": "scripts.data_quality.run_silver_gold_filter_parity",
}
COMMAND_SPECS = {name: module_command(module) for name, module in COMMANDS.items()}


def main(argv: list[str] | None = None) -> int:
    return dispatch_cli(
        argv,
        help_text=__doc__ or "Data quality commands",
        commands=COMMAND_SPECS,
    )


if __name__ == "__main__":
    raise SystemExit(main())
