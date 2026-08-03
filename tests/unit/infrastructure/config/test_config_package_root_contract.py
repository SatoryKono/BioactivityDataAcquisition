# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit contracts for the infrastructure config package-root facade."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unit


def test_config_package_root_lazy_exports_canonical_loader_functions() -> None:
    """Lazy package-root exports must resolve to canonical loader modules."""
    import bioetl.infrastructure.config as config
    from bioetl.infrastructure.config.composite_config_api import load_composite_config
    from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config
    from bioetl.infrastructure.config.source_config_loader import load_source_config
    from bioetl.infrastructure.config.workflow_config_api import load_workflow_config

    assert config.__getattr__("load_pipeline_config") is load_pipeline_config
    assert config.__getattr__("load_composite_config") is load_composite_config
    assert config.__getattr__("load_source_config") is load_source_config
    assert config.__getattr__("load_workflow_config") is load_workflow_config


def test_config_package_root_rejects_unknown_lazy_export() -> None:
    """Unknown config package-root symbols must fail fast."""
    import bioetl.infrastructure.config as config

    with pytest.raises(AttributeError, match="not_a_config_export"):
        config.__getattr__("not_a_config_export")
