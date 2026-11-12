"""Invalid-record policy accepts only the documented DQ actions."""

from __future__ import annotations

import pytest
from bioetl.domain.composite.config_composite_section_decoders import build_dq_config
from bioetl.domain.composite.config_dq import CompositeDQConfig

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("policy", ["discard", "", "QUARANTINE"])
def test_invalid_policy_is_rejected_at_both_configuration_boundaries(policy):
    with pytest.raises(ValueError, match="invalid_record_policy must be one of"):
        CompositeDQConfig(invalid_record_policy=policy)
    message = "must be a non-empty string" if not policy else "must be one of"
    with pytest.raises(ValueError, match="dq.invalid_record_policy " + message):
        build_dq_config({"invalid_record_policy": policy})


@pytest.mark.parametrize("policy", ["quarantine", "skip", "fail"])
def test_supported_policy_survives_decoding(policy):
    assert (
        build_dq_config({"invalid_record_policy": policy}).invalid_record_policy
        == policy
    )
