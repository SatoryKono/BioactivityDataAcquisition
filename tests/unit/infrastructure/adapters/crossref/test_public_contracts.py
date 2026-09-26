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
"""Compatibility tests for CrossRef adapter module decomposition."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.adapters import crossref as crossref_pkg
from bioetl.infrastructure.adapters.crossref.client import (
    CROSSREF_API_BASE as CLIENT_CROSSREF_API_BASE,
)
from bioetl.infrastructure.adapters.crossref.client import (
    CROSSREF_HEALTH_ERRORS as CLIENT_CROSSREF_HEALTH_ERRORS,
)
from bioetl.infrastructure.adapters.crossref.client import (
    CrossRefAdapter as ClientCrossRefAdapter,
)
from bioetl.infrastructure.adapters.crossref.client import (
    CrossRefFetchFlow as ClientCrossRefFetchFlow,
)
from bioetl.infrastructure.adapters.crossref.client import (
    CrossRefQueryPlanner as ClientCrossRefQueryPlanner,
)
from bioetl.infrastructure.adapters.crossref.client import (
    CrossRefResponseMapper as ClientCrossRefResponseMapper,
)
from bioetl.infrastructure.adapters.crossref.models import (
    CrossRefMessage as FacadeCrossRefMessage,
)
from bioetl.infrastructure.adapters.crossref.models import (
    CrossRefPublicationResponse as FacadeCrossRefPublicationResponse,
)
from bioetl.infrastructure.adapters.crossref.models import (
    CrossRefPublicationsResponse as FacadeCrossRefPublicationsResponse,
)
from bioetl.infrastructure.adapters.crossref._response_models import (
    CrossRefMessage as HelperCrossRefMessage,
)
from bioetl.infrastructure.adapters.crossref._response_models import (
    CrossRefPublicationResponse as HelperCrossRefPublicationResponse,
)
from bioetl.infrastructure.adapters.crossref._response_models import (
    CrossRefPublicationsResponse as HelperCrossRefPublicationsResponse,
)


@pytest.mark.unit
def test_package_reexports_client_symbols_for_backward_compatibility() -> None:
    """Existing imports from crossref package and client must resolve identically."""
    assert crossref_pkg.CrossRefAdapter is ClientCrossRefAdapter
    assert crossref_pkg.CROSSREF_API_BASE == CLIENT_CROSSREF_API_BASE
    assert crossref_pkg.CROSSREF_HEALTH_ERRORS == CLIENT_CROSSREF_HEALTH_ERRORS


@pytest.mark.unit
def test_client_reexports_new_decomposed_components() -> None:
    """Client facade should re-export decomposed flow/query/mapper components."""
    assert ClientCrossRefFetchFlow.__name__ == "CrossRefFetchFlow"
    assert ClientCrossRefQueryPlanner.__name__ == "CrossRefQueryPlanner"
    assert ClientCrossRefResponseMapper.__name__ == "CrossRefResponseMapper"


@pytest.mark.unit
def test_models_facade_reexports_response_wrappers() -> None:
    """CrossRef models facade should preserve response-wrapper imports."""
    assert FacadeCrossRefMessage is HelperCrossRefMessage
    assert FacadeCrossRefPublicationsResponse is HelperCrossRefPublicationsResponse
    assert FacadeCrossRefPublicationResponse is HelperCrossRefPublicationResponse
