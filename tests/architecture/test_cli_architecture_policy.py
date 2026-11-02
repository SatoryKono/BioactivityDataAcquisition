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
"""Schema and negative contract for the CLI architecture boundary (#12480).

The normative boundary is ADR-005: ``interfaces`` must not import
``infrastructure`` directly, while indirect imports through composition stay
allowed. The machine-readable source is ``.importlinter`` contract
``interfaces-no-direct-infrastructure``. These tests do not accept
``composition_ownership_map.yaml`` or a parallel CLI policy file.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tests.architecture._cli_architecture_policy import (
    CLI_ARCHITECTURE_CONTRACT_SCHEMA,
    IMPORT_LINTER_RELATIVE,
    CliArchitecturePolicyError,
    load_repo_cli_architecture_contract,
    parse_cli_architecture_contract,
)

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]

_VALID_CONTRACT = """\
[importlinter]
root_package = bioetl

[importlinter:contract:interfaces-no-direct-infrastructure]
name = Interfaces layer must not import infrastructure directly
type = forbidden
source_modules =
    bioetl.interfaces
forbidden_modules =
    bioetl.infrastructure
allow_indirect_imports = True
"""

_DIRECT_INFRASTRUCTURE_ALLOWED = """\
[importlinter:contract:interfaces-no-direct-infrastructure]
name = Interfaces layer must not import infrastructure directly
type = forbidden
source_modules =
    bioetl.interfaces
forbidden_modules =
    bioetl.domain
allow_indirect_imports = True
"""

_MISSING_REQUIRED_FIELDS = """\
[importlinter:contract:interfaces-no-direct-infrastructure]
name = Interfaces layer must not import infrastructure directly
"""

_CLI_IGNORE = """\
[importlinter:contract:interfaces-no-direct-infrastructure]
name = Interfaces layer must not import infrastructure directly
type = forbidden
source_modules =
    bioetl.interfaces
forbidden_modules =
    bioetl.infrastructure
allow_indirect_imports = True
ignore_imports =
    bioetl.interfaces.cli -> bioetl.infrastructure
"""


def test_cli_contract_schema_is_draft_2020_12() -> None:
    assert Draft202012Validator.check_schema(CLI_ARCHITECTURE_CONTRACT_SCHEMA) is None


def test_repo_import_linter_contract_matches_cli_schema() -> None:
    contract = load_repo_cli_architecture_contract()

    assert contract["contract_id"] == "interfaces-no-direct-infrastructure"
    assert contract["type"] == "forbidden"
    assert contract["source_modules"] == ["bioetl.interfaces"]
    assert contract["forbidden_modules"] == ["bioetl.infrastructure"]
    assert contract["allow_indirect_imports"] is True
    assert contract["ignore_imports"] == []


def test_valid_cli_contract_fixture_is_accepted() -> None:
    contract = parse_cli_architecture_contract(_VALID_CONTRACT)

    assert contract["forbidden_modules"] == ["bioetl.infrastructure"]
    assert contract["allow_indirect_imports"] is True


def test_direct_infrastructure_allowance_is_rejected() -> None:
    with pytest.raises(CliArchitecturePolicyError, match=r"bioetl\.infrastructure"):
        parse_cli_architecture_contract(_DIRECT_INFRASTRUCTURE_ALLOWED)


def test_missing_contract_section_is_rejected() -> None:
    with pytest.raises(CliArchitecturePolicyError, match="missing required contract"):
        parse_cli_architecture_contract("")


def test_missing_required_contract_fields_are_rejected() -> None:
    with pytest.raises(CliArchitecturePolicyError):
        parse_cli_architecture_contract(_MISSING_REQUIRED_FIELDS)


def test_cli_ignore_of_infrastructure_is_rejected() -> None:
    with pytest.raises(CliArchitecturePolicyError):
        parse_cli_architecture_contract(_CLI_IGNORE)


def test_composition_ownership_map_does_not_satisfy_cli_policy() -> None:
    ownership_map = ROOT / "configs/quality/architecture/composition_ownership_map.yaml"
    text = ownership_map.read_text(encoding="utf-8")

    with pytest.raises(CliArchitecturePolicyError, match="missing required contract"):
        parse_cli_architecture_contract(text)


def test_loader_does_not_use_a_second_cli_policy_file() -> None:
    assert IMPORT_LINTER_RELATIVE == ".importlinter"
    assert (ROOT / IMPORT_LINTER_RELATIVE).is_file()
    assert not (
        ROOT / "configs/quality/architecture/cli_architecture_policy.yaml"
    ).exists()
